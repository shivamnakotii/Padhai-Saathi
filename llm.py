import json
import os
import re

from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv("MODEL", "claude-sonnet-5-5")

_client = None


def client():
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY set nahi hai. .env file mein apni key daalo.")
        import anthropic
        _client = anthropic.Anthropic(api_key=key)
    return _client


def ask(system: str, messages: list, max_tokens: int = 1500) -> str:
    r = client().messages.create(model=MODEL, max_tokens=max_tokens, system=system, messages=messages)
    return "".join(b.text for b in r.content if b.type == "text")


def ask_json(system: str, prompt: str, max_tokens: int = 3000):
    text = ask(system + "\nSirf valid JSON return karo, aur kuch nahi (no markdown fences).",
               [{"role": "user", "content": prompt}], max_tokens)
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start = min([i for i in (text.find("["), text.find("{")) if i != -1], default=0)
    end = max(text.rfind("]"), text.rfind("}")) + 1
    return json.loads(text[start:end])
