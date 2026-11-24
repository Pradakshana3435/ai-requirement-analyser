import time
from pydantic import BaseModel
from llm.client import call_json


class Hello(BaseModel):
    message: str


for i in range(2):
    start = time.time()
    r = call_json("hello", "You are a helpful assistant.",
                  'Return a JSON object with one key "message" containing a short greeting.', Hello)
    print(f"run {i + 1}: {r.message!r} in {time.time() - start:.2f}s")