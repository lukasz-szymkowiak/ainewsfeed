import anthropic
from dotenv import load_dotenv

load_dotenv()


def call_claude(prompt: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=15000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text