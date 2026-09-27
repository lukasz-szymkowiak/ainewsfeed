"""Fetch and filter news articles from NewsAPI for a given company query."""

import os
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from newsapi import NewsApiClient
from trafilatura import fetch_url, extract
from trafilatura.settings import use_config
import json

# Read NEWSAPI_KEY from the .env file (searched upward from this file's folder).
load_dotenv()

# Some sites (e.g. Cloudflare-protected ones) return 403 for trafilatura's
# default User-Agent but accept a plain browser-like one.
TRAFILATURA_CONFIG = use_config()
TRAFILATURA_CONFIG.set("DEFAULT", "USER_AGENTS", "Mozilla/5.0")

# Map a search query to acceptable name variants that should also count
# as a match (e.g. a company's ticker-holding parent, a rebrand, etc.).
ALIASES = {
    "pinduoduo": ["pinduoduo", "pdd", "temu"],
}

# Aggregators/deal sites whose pages give us no usable article text.
EXCLUDED_DOMAINS = "biztoc.com,dealnews.com"


def normalize_text(value: str | None) -> str:
    """Normalize Unicode, punctuation and whitespace for comparison."""
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return " ".join(re.findall(r"\w+", value))


def mentions(text: str, term: str) -> bool:
    return f" {normalize_text(term)} " in f" {text} "


def canonical_url(value: str | None) -> str:
    """Ignore fragments and known tracking parameters, preserving article IDs."""
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        if not parts.netloc:
            return value
        query = sorted(
            (key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_")
            and key.casefold() not in {"fbclid", "gclid", "mc_cid", "mc_eid"}
        )
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                           parts.path, urlencode(query), ""))
    except ValueError:
        return value


def get_newsapi_results(query: str) -> dict:
    """Call NewsAPI's /everything endpoint and return the raw response."""
    key = os.environ.get("NEWSAPI_KEY")
    if not key:
        raise RuntimeError("NEWSAPI_KEY is not set. Add it to the .env file.")
    newsapi = NewsApiClient(api_key=key)
    return newsapi.get_everything(
        q=query,
        language="en",
        sort_by="publishedAt",
        page_size=100,
        exclude_domains=EXCLUDED_DOMAINS,
    )


def parse_articles(result: dict) -> list[dict]:
    """Flatten NewsAPI's raw response into a list of simple article dicts."""
    parsed = []
    for article in result["articles"]:
        item = {
            "title": article["title"],
            "description": article["description"] or "",
            "url": article["url"],
            "published": article["publishedAt"],
            "source": article["source"]["name"],
        }
        parsed.append(item)
    return parsed


def filter_by_query(articles: list[dict], query: str) -> list[dict]:
    """Match whole names, excluding known figurative uses of the Temu brand."""
    query = normalize_text(query)
    if not query:
        return []
    terms = ALIASES.get(query, [query])
    relevant = []
    for article in articles:
        text = normalize_text(
            f"{article.get('title') or ''} {article.get('description') or ''}"
        )
        if query == "pinduoduo":
            # These nicknames refer to unrelated products. A separate actual
            # company mention still qualifies the story.
            text = re.sub(r"\btemu (?:range rover|beef)\b", "", text)
        if any(mentions(text, term) for term in terms):
            relevant.append(article)
    return relevant


def dedupe_by_title(articles: list[dict]) -> list[dict]:
    """Keep the first occurrence by URL, normalized title or syndicated preview.

    Input order is preserved (NewsAPI supplies newest first). Shared previews
    require a substantial exact match, overlapping titles and the same day;
    merely covering the same topic does not make two articles duplicates.
    """
    seen_titles = set()
    seen_urls = set()
    previews = {}
    unique = []
    for article in articles:
        title = normalize_text(article.get("title"))
        url = canonical_url(article.get("url"))
        description = normalize_text(article.get("description"))
        day = (article.get("published") or "")[:10]
        tokens = set(title.split())
        preview_key = (day, description)
        same_preview = False
        if day and len(description.split()) >= 15 and tokens:
            same_preview = any(
                len(tokens & prior) / len(tokens | prior) >= 0.5
                for prior in previews.get(preview_key, [])
            )
            previews.setdefault(preview_key, []).append(tokens)
        duplicate = ((title and title in seen_titles)
                     or (url and url in seen_urls) or same_preview)
        if title:
            seen_titles.add(title)
        if url:
            seen_urls.add(url)
        if not duplicate:
            unique.append(article)
    return unique


def get_links(articles: list[dict]) -> list[str]:
    """Extract the URLs from a list of article dicts."""
    return [article["url"] for article in articles]

def add_article_text(articles: list[dict], limit: int | None = None) -> list[dict]:
    """Download each article and add its main text under "text" (None if it couldn't be fetched)."""
    for article in articles[:limit]:
        article["text"] = None
        if article["url"] is None:
            continue
        downloaded = fetch_url(article["url"], config=TRAFILATURA_CONFIG)
        if downloaded is None:
            print(f"Could not download: {article['url']}")
            continue
        article["text"] = extract(downloaded, include_comments=False)
    return articles[:limit]

if __name__ == "__main__":
    company = "pinduoduo"  # key into ALIASES, used for the title filter
    # sent to NewsAPI: the company, or Temu only when the story is business news
    search_query = (
        '"PDD Holdings" OR Pinduoduo OR '
        "(Temu AND (earnings OR regulation OR tariffs OR sales OR shares OR revenue))"
    )
    raw_result = get_newsapi_results(search_query)
    parsed_articles = parse_articles(raw_result)
    filtered_articles = dedupe_by_title(filter_by_query(parsed_articles, company))
    filtered_articles_with_text = add_article_text(filtered_articles)
    with open("articles.json", "w", encoding="utf-8") as file:
        json.dump(filtered_articles_with_text, file, ensure_ascii=False, indent=2)
