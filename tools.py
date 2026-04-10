import subprocess
from pydantic import BaseModel
from typing import Callable
from pathlib import Path


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

    if input(f">>> Allow to run `{command=}`?").lower() != "y":
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


def code_search(pattern: str, file_type: str = "", directory: str = ".") -> str:
    try:
        cmd = ["rg", "--color=never", pattern]

        if file_type:
            cmd.extend(["--type", file_type])

        cmd.append(directory)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, cwd=Path.cwd()
        )

        if result.returncode == 0:
            return result.stdout
        elif result.returncode == 1:
            return f"No matches found for pattern: {pattern}"
        else:
            return f"Search error: {result.stderr}"
    except FileNotFoundError:
        return "Error: ripgrep (rg) not installed. Please install it first."
    except Exception as e:
        return f"Search error: {e}"


REGISTRY = ToolRegistry()

REGISTRY.register(
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

REGISTRY.register(
    Tool(
        name="list_files",
        description="List files in current directory",
        params=[],
        func=list_files,
    )
)

REGISTRY.register(
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

REGISTRY.register(
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

REGISTRY.register(
    Tool(
        name="code_search",
        description="Search for code patterns using ripgrep (rg). Use this to find code patterns, function definitions, variable usage, or any text in the codebase. You can search by pattern, file type, or directory.",
        params=[
            ToolParam(
                name="pattern",
                type="string",
                description="The search pattern (regex supported)",
                required=True,
            ),
            ToolParam(
                name="file_type",
                type="string",
                description="File type filter (e.g., 'py', 'js', 'go') - optional",
                required=False,
            ),
            ToolParam(
                name="directory",
                type="string",
                description="Directory to search in (default: current directory)",
                required=False,
            ),
        ],
        func=code_search,
    )
)
