"""Fetch and filter news articles from NewsAPI for a given company query."""

import os
import re
import unicodedata
from http.client import HTTPException
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from trafilatura import fetch_url, extract
from trafilatura.settings import use_config
import json

# Read NEWSAPI_KEY from the .env file (searched upward from this file's folder).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

COMPANY_QUERY = '"PDD Holdings" OR Pinduoduo OR Temu'

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

# Seller tutorials and vendor integration announcements are not company news.
# Check the headline so a passing mention in an otherwise relevant story does
# not discard the article.
SELLER_PROMOTION_PHRASES = (
    "seller education",
    "seller training",
    "seller academy",
    "seller resources",
    "integration for retailers",
    "dropshipping platform",
)

# A conservative topic filter for company news. Keyword matching can miss
# relevant stories, but avoids selecting lifestyle pieces from passing mentions.
BUSINESS_NEWS_PHRASES = (
    "earnings", "revenue", "profit", "profits", "quarterly results",
    "stock", "share price", "shares rise", "shares fall",
    "tariff", "tariffs", "regulation", "regulations", "regulatory",
    "antitrust", "lawsuit", "lawsuits", "fine", "fines", "fee", "fees",
    "law", "laws", "advertising", "ad spending", "ad business", "ads",
    "fulfillment", "logistics", "supply chain", "acquisition", "merger",
    "layoffs", "invests", "investment", "investments", "expansion",
    "competition", "compete",
    "partner", "partners", "partnership", "launches", "introduces",
    "expands", "recall", "recalls", "ban", "banned", "privacy", "customs",
)


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
    # The installed newsapi-python client doesn't expose searchIn. Use the
    # endpoint directly, with Python's system certificate trust and a key header.
    params = urlencode({
        "q": query,
        "searchIn": "title,description",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 100,
        "excludeDomains": EXCLUDED_DOMAINS,
    })
    request = Request(
        f"https://newsapi.org/v2/everything?{params}",
        headers={"X-Api-Key": key},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


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
    """Match whole names, excluding figurative uses and seller promotions."""
    query = normalize_text(query)
    if not query:
        return []
    terms = ALIASES.get(query, [query])
    relevant = []
    for article in articles:
        title = normalize_text(article.get("title"))
        if query == "pinduoduo" and any(
            mentions(title, phrase) for phrase in SELLER_PROMOTION_PHRASES
        ):
            continue
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


def filter_business_news(articles: list[dict], query: str) -> list[dict]:
    """Require a company headline and business context in title or description."""
    query = normalize_text(query)
    terms = ALIASES.get(query, [query])
    relevant = []
    for article in filter_by_query(articles, query):
        title = normalize_text(article.get("title"))
        context = normalize_text(f"{article.get('title') or ''} {article.get('description') or ''}")
        if (any(mentions(title, term) for term in terms)
                and any(mentions(context, topic) for topic in BUSINESS_NEWS_PHRASES)):
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


def merge_with_saved(fresh: list[dict], saved: list[dict]) -> list[dict]:
    """Combine a fresh fetch with previously saved articles, newest first.

    NewsAPI's free plan only reaches back ~30 days, so saved articles that
    have aged out of the window are kept. Matching is by canonical URL; a
    fresh article reuses the saved body text instead of downloading it again.
    """
    saved_by_url = {canonical_url(a["url"]): a for a in saved if a.get("url")}
    merged = []
    fresh_urls = set()
    for article in fresh:
        key = canonical_url(article.get("url"))
        fresh_urls.add(key)
        if key in saved_by_url:
            article["text"] = saved_by_url[key].get("text")
        merged.append(article)
    merged.extend(a for key, a in saved_by_url.items() if key not in fresh_urls)
    return sorted(merged, key=lambda a: a.get("published") or "", reverse=True)


def get_links(articles: list[dict]) -> list[str]:
    """Extract the URLs from a list of article dicts."""
    return [article["url"] for article in articles]

def fetch_html_system_certs(url: str) -> str | None:
    """Download a page with the system certificate store (trafilatura uses certifi's)."""
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (OSError, ValueError, HTTPException):
        return None


def add_article_text(articles: list[dict], limit: int | None = None) -> list[dict]:
    """Download each article and add its main text under "text" (None if it couldn't be fetched)."""
    for article in articles[:limit]:
        if isinstance(article.get("text"), str) and article["text"].strip():
            continue
        article["text"] = None
        if article["url"] is None:
            continue
        downloaded = (fetch_url(article["url"], config=TRAFILATURA_CONFIG)
                      or fetch_html_system_certs(article["url"]))
        if downloaded is None:
            print(f"Could not download: {article['url']}")
            continue
        article["text"] = extract(downloaded, include_comments=False)
    return articles[:limit]

if __name__ == "__main__":
    company = "pinduoduo"  # key into ALIASES, used for the title filter
    raw_result = get_newsapi_results(COMPANY_QUERY)
    parsed_articles = parse_articles(raw_result)
    filtered_articles = dedupe_by_title(filter_business_news(parsed_articles, company))
    print(f"NewsAPI: {len(parsed_articles)} returned, {raw_result.get('totalResults')} total matches.", flush=True)
    print(f"After business filtering and deduplication: {len(filtered_articles)} articles.", flush=True)
    if raw_result.get("totalResults", 0) > 100:
        print("Only the newest API page was fetched (maximum 100 results).", flush=True)
    if filtered_articles:
        print(f"Newest retained article: {filtered_articles[0]['published']} — {filtered_articles[0]['title']}", flush=True)
    output_path = PROJECT_ROOT / "articles.json"
    # Keep articles saved by earlier runs (they age out of NewsAPI's 30-day
    # window) and reuse their extracted bodies. Re-filter the merged list so a
    # tightened filter also purges old entries.
    saved_articles = []
    if output_path.exists():
        with open(output_path, encoding="utf-8") as file:
            saved_articles = json.load(file)
    merged_articles = dedupe_by_title(
        filter_business_news(merge_with_saved(filtered_articles, saved_articles), company)
    )
    print(f"After merging with {len(saved_articles)} saved articles: {len(merged_articles)} articles.", flush=True)
    filtered_articles_with_text = add_article_text(merged_articles)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(filtered_articles_with_text, file, ensure_ascii=False, indent=2)
    print(f"Saved {len(filtered_articles_with_text)} articles to {output_path}")
    print(f"Articles with extracted text: {sum(bool(item.get('text')) for item in filtered_articles_with_text)}")
