"""Fetch and filter news articles from NewsAPI for a given company query."""

import os

from newsapi import NewsApiClient

# Map a search query to acceptable name variants that should also count
# as a match (e.g. a company's ticker-holding parent, a rebrand, etc.).
ALIASES = {
    "pinduoduo": ["pinduoduo", "pdd holdings"],
}


def get_newsapi_results(query: str) -> dict:
    """Call NewsAPI's /everything endpoint and return the raw response."""
    key = os.environ["NEWSAPI_KEY"]
    newsapi = NewsApiClient(api_key=key)
    return newsapi.get_everything(q=query, language="en")


def parse_articles(result: dict) -> list[dict]:
    """Flatten NewsAPI's raw response into a list of simple article dicts."""
    parsed = []
    for article in result["articles"]:
        item = {
            "title": article["title"],
            "url": article["url"],
            "published": article["publishedAt"],
            "source": article["source"]["name"],
        }
        parsed.append(item)
    return parsed


def filter_by_query(articles: list[dict], query: str) -> list[dict]:
    """Keep only articles whose title mentions the query or a known alias."""
    terms = ALIASES.get(query.lower(), [query.lower()])
    return [
        article
        for article in articles
        if any(term in article["title"].lower() for term in terms)
    ]


if __name__ == "__main__":
    query = "pinduoduo"
    raw_result = get_newsapi_results(query)
    parsed_articles = parse_articles(raw_result)
    filtered_articles = filter_by_query(parsed_articles, query)
    print(filtered_articles)