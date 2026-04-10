import llm
import subprocess
import re
import json

from pydantic import BaseModel
from typing import Callable
from pathlib import Path


def extract_json(raw_text: str) -> dict:
    text = raw_text.strip()

    # Try fenced blocks first (last one wins)
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    for candidate in reversed(fenced):
        try:
            return json.loads(candidate.strip())
        except json.JSONDecodeError:
            continue

    # Try every {...} block from last to first
    matches = list(re.finditer(r"\{.*?\}", text, re.DOTALL))
    for match in reversed(matches):
        try:
            return json.loads(match.group().strip())
        except json.JSONDecodeError:
            continue

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    raise ValueError(f"No valid JSON found in model output:\n{raw_text}")


class ToolParam(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True


class Tool(BaseModel):
    name: str
    description: str
    params: list[ToolParam]
    func: Callable


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_all(self) -> list[dict]:
        return [tool.model_dump(exclude={"func"}) for tool in self._tools.values()]

    def execute(self, tool_name: str, **kwargs):
        tool = self.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        return tool.func(**kwargs)


def read_file(path: str) -> str:
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return f"File not found {path}"
    except Exception as e:
        return f"Exception reading file: {e}"


def list_files() -> str:
    result = subprocess.run(["ls", "-la"], capture_output=True, text=True)
    return result.stdout


def run_bash(command: str) -> str:
    blocked = ["rm -rf", "sudo", "curl", "wget", "mkfs"]
    if any(bad in command for bad in blocked):
        return f"Blocked: {command=} contains a disallowed pattern"

    if input(f"\n\n\n >>> Allow to run `{command=}`?").lower() != "y":
        return f"Did not allow execution of {command=}"

    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=30, cwd=Path.cwd()
    )
    return result.stdout


def edit_file(path: str, content: str, append: bool = False) -> str:
    file_path = Path(path)

    if not file_path.exists():
        return f"File not found: {path}"

    if append:
        content = file_path.read_text() + "\n" + content

    file_path.write_text(content)
    return f"Updated file: {path}"


registry = ToolRegistry()

registry.register(
    Tool(
        name="read_file",
        description="Read the entire contents of a file",
        params=[
            ToolParam(
                name="path",
                type="string",
                description="File path to read",
                required=True,
            )
        ],
        func=read_file,
    )
)

registry.register(
    Tool(
        name="list_files",
        description="List files in current directory",
        params=[],
        func=list_files,
    )
)

registry.register(
    Tool(
        name="run_bash",
        description="Run a bash command and return its output. Use for file operations, searching, running scripts, etc.",
        params=[
            ToolParam(
                name="command",
                type="string",
                description="The bash command to execute",
                required=True,
            )
        ],
        func=run_bash,
    )
)

registry.register(
    Tool(
        name="edit_file",
        description="Edit a file by (re)writing or appending content",
        params=[
            ToolParam(
                name="path",
                type="string",
                description="File path to edit",
                required=True,
            ),
            ToolParam(
                name="content",
                type="string",
                description="Content to use for editing",
                required=True,
            ),
            ToolParam(
                name="append",
                type="boolean",
                description="Should we append to the file.",
                required=True,
            ),
        ],
        func=edit_file,
    )
)

system_prompt = f"""
You are an AI assistant with access to tools.

TOOLS:
{json.dumps(registry.get_all(), indent=2)}

STRICT OUTPUT RULES:
- Output EXACTLY ONE JSON object per response. Nothing else.
- No markdown. No backticks. No explanations. No XML.
- Do not narrate what you are about to do.
- Do not call multiple tools at once — one tool call per response.
- If you need to read a file before answering, call the tool. Do not also output a message.
- After a tool returns a result, either call another tool OR output a message — never repeat the same tool call.
- If a tool call succeeded (e.g. "Successfully edited"), respond with a message confirming the result to the user.
- Be concise, short in answers, unless asked otherwise.

Response format:
If responding to user: {{"type": "message", "content": "text"}}
If calling a tool:     {{"type": "tool_call", "name": "tool_name", "arguments": {{...}}}}
"""


messages = [{"role": "system", "content": system_prompt}]
model = llm.get_model("claude-haiku-4.5")

while True:
    prompt = input("> ")
    if prompt == "exit":
        break

    messages.append({"role": "user", "content": prompt})

    while True:
        # print(f"input: {messages}")

        # Trying to force it to give json by retrying...
        response = None
        for _ in range(3):
            output = model.prompt(json.dumps(messages)).text()
            # print('raw < ', output)
            try:
                response = extract_json(output)
                break
            except:
                continue

        if response is None:
            raise ValueError("Model failed to produce valid JSON")

        if response["type"] == "message":
            messages.append({"role": "assistant", "content": response["content"]})
            print("<", response["content"])
            break

        elif response["type"] == "tool_call":
            messages.append({"role": "assistant", "content": json.dumps(response)})

            result = registry.execute(response["name"], **response["arguments"])

            messages.append(
                {
                    "role": "tool",
                    "name": response["name"],
                    "content": json.dumps(
                        {"result": result},
                    ),
                }
            )
