# toy agent loop

Small toy program for setting up an agentic loop that can use predefined tools. 

Supported tools - list, read, edit files, run bash commands.

Inspired by https://ghuntley.com/agent/

## setup
```sh
uv sync
uv run chat.py
```

## how it works
1. User types a question
2. chat.py sends it to Claude with tool definitions in the system prompt
3. Claude responds with JSON:
   - If type='message': display answer to user
   - If type='tool_call': execute the tool via REGISTRY
4. Add tool result back to message history
5. Claude sees result and either calls another tool or sends final message
6. Repeat until Claude outputs a message response or user exits

## example
```sh
$ uv run chat.py
> top 3 tools to add to this
< Top 3 tools to add:

1. **write_file** - Create new files without needing to check existence first. Would simplify file creation workflow.

2. **search_files** - Search file contents or filenames using grep/find patterns. Essential for navigating larger codebases.

3. **execute_python** - Run Python code directly for calculations, data processing, or testing. More flexible than bash for certain tasks.
```
