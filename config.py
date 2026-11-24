import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
MAX_PARALLEL = int(os.getenv("MAX_PARALLEL", "3"))
CACHE_DIR = ".cache"
SUGGEST_SCOPE = os.getenv("SUGGEST_SCOPE", "flagged")  # "flagged" or "all"

_KEYS = {"groq": GROQ_API_KEY, "gemini": GEMINI_API_KEY, "anthropic": ANTHROPIC_API_KEY}


def require_key() -> str:
    key = _KEYS.get(LLM_PROVIDER, "")
    if not key:
        raise RuntimeError(f"No API key set for provider '{LLM_PROVIDER}'. Add it to .env.")
    return key