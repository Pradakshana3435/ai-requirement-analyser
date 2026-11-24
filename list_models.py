from groq import Groq
import config

client = Groq(api_key=config.require_key())
for m in sorted(client.models.list().data, key=lambda m: m.id):
    print(m.id)