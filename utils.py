import re
import json


def extract_json(raw_text: str) -> dict:
    # This method is not required if using the anthropic-sdk (it would cover it)
    # Note: it will still fail on some cases.
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
