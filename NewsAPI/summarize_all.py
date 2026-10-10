import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv



PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

with open(PROJECT_ROOT / "articles.json", encoding="utf-8") as file:
    articles = (json.load(file))

titles = [a.get("title") for a in articles if a.get("title")]
# [print(len(titles), f"articles found. First 10 titles: {titles[:10]}")]

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to the project .env file.")
else:
    client = Anthropic(api_key=api_key)

def summarize(client, article):
    prompt = f"""Summarize the following article in 3 bullet points in English.
    Use only information contained in the text.
    Focus on specific developments involving PDD Holdings, Pinduoduo, or Temu.
    Attribute company claims and research findings to their respective sources.
    Preserve caveats, dates, and numbers. Do not add your own conclusions.

    Title: {article['title']}

    Text:
    {article['text']}
    """
    message = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if block.type == "text")
results = []
def main() -> None:
    for article in articles[:]:
        summary = summarize(client, article)
        results.append({
            "title": article["title"],
            "url": article.get("url"),
            "summary": summary,
        })



if __name__ == "__main__":
    main()

output_path = PROJECT_ROOT / "summaries.json"
with open(output_path, "w", encoding="utf-8") as file:
     json.dump(results, file, ensure_ascii=False, indent=2)