# toy agent loop

Small toy program for setting up an agentic loop with tools. 

Supported tools - list, read, edit files, run bash commands.

Inspired by https://ghuntley.com/agent/

## setup
```sh
uv sync
uv run chat.py
```

## example
```sh
$ uv run chat.py
> top 3 tools to add to this
< Top 3 tools to add:

1. **write_file** - Create new files without needing to check existence first. Would simplify file creation workflow.

2. **search_files** - Search file contents or filenames using grep/find patterns. Essential for navigating larger codebases.

3. **execute_python** - Run Python code directly for calculations, data processing, or testing. More flexible than bash for certain tasks.
```
