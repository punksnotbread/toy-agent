import anthropic
import os

from tools import REGISTRY, build_anthropic_tools

SYSTEM_PROMPT = """
You are an AI assistant with access to tools.

INSTRUCTION:
- You must always respond with one of two actions:
  1. Call a tool to help answer the user's question
  2. Send a text response to the user (when you have a complete answer)
- Call tools one at a time, never multiple tools in one response
- If a tool result is returned, evaluate if you need to:
  - Call another tool to gather more information
  - Respond with a message to the user with the gathered information
- Be concise and direct in your responses
"""

if __name__ == "__main__":
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)

    messages = []
    tools = build_anthropic_tools()

    while True:
        prompt = input("> ")
        if prompt == "exit":
            break

        messages.append({"role": "user", "content": prompt})

        while True:
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            content_blocks = []
            for block in response.content:
                if block.type == "text":
                    content_blocks.append(
                        {
                            "type": "text",
                            "text": block.text,
                        }
                    )
                elif block.type == "tool_use":
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )

            messages.append({"role": "assistant", "content": content_blocks})

            tool_results = []
            has_text_response = False

            for block in response.content:
                if block.type == "text":
                    print("<", block.text)
                    has_text_response = True

                elif block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    try:
                        result = REGISTRY.execute(tool_name, **tool_input)
                    except Exception as e:
                        result = f"Error executing tool: {str(e)}"

                    # Print tool output to user if it's from bash
                    if tool_name == "run_bash":
                        print("$ OUTPUT:")
                        print(result)
                        print()

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        }
                    )

            if tool_results:
                messages.append(
                    {
                        "role": "user",
                        "content": tool_results,
                    }
                )
                continue

            if has_text_response:
                break
