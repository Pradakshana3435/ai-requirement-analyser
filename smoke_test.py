from groq import Groq
import config

client = Groq(api_key=config.require_key())
resp = client.chat.completions.create(
    model=config.GROQ_MODEL,
    messages=[{"role": "user", "content": "Reply with exactly: API OK"}],
    temperature=0,
)
print(resp.choices[0].message.content)