import json
from pathlib import Path

if __package__:
    from .api_scrapper import filter_business_news
else:
    from api_scrapper import filter_business_news

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def select_article(articles: list[dict], company: str = "pinduoduo") -> dict:
    """Select the first business story with usable text, preserving feed order."""
    for article in filter_business_news(articles, company):
        text = article.get("text")
        if isinstance(text, str) and text.strip():
            return article
    raise ValueError("No company business news with usable text found. Run api_scrapper.py to refresh articles.json.")


def main() -> None:
    with open(PROJECT_ROOT / "articles.json", encoding="utf-8") as file:
        article = select_article(json.load(file))

    print(f"Article: {article['title']}")
    print(f"Source: {article.get('source') or 'Unknown'} | {article.get('published') or ''}")
    print(f"URL: {article.get('url') or ''}\n", flush=True)

    print(article["text"])


if __name__ == "__main__":
    main()
