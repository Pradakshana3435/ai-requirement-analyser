from typing import List

from pydantic import BaseModel

from llm.client import call_json
from models import Requirement

MAX_REQS = 60

SYSTEM_PROMPT = """You are a business analyst assistant. Write a brief summary (3 to 4 sentences) of
the submitted requirements: what the system or project is about and the main areas covered.
Use ONLY the requirement statements given. Do not add any detail that is not in them.

Return JSON in exactly this shape:
{"summary": "..."}
"""


class SummaryResult(BaseModel):
    summary: str


def summarize(reqs: List[Requirement]) -> str:
    lines = "\n".join(f"{r.req_id}: {r.text}" for r in reqs[:MAX_REQS])
    result = call_json("summary", SYSTEM_PROMPT, f"REQUIREMENTS:\n{lines}", SummaryResult)
    return result.summary.strip()