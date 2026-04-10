import llm
import json


from utils import extract_json
from tools import REGISTRY

SYSTEM_PROMPT = f"""
You are an AI assistant with access to tools.

TOOLS:
{json.dumps(REGISTRY.get_all(), indent=2)}

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

if __name__ == "__main__":
    model = llm.get_model("claude-haiku-4.5")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    while True:
        prompt = input("> ")
        if prompt == "exit":
            break

        messages.append({"role": "user", "content": prompt})

        while True:
            # print(f"input: {messages}")

            # If we fail to get a JSON, let's retry (small models skip system prompts)
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

                result = REGISTRY.execute(response["name"], **response["arguments"])

                messages.append(
                    {
                        "role": "tool",
                        "name": response["name"],
                        "content": json.dumps(
                            {"result": result},
                        ),
                    }
                )
