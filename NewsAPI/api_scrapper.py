# we call a NewsAPI and return first results

import os
from turtle import title
from newsapi import NewsApiClient

key = os.environ["NEWSAPI_KEY"]
newsapi = NewsApiClient(api_key=key)
#init 

aliases = {
    "pinduoduo": ["pinduoduo", "pdd holdings"]
}

def get_newsapi_results(query):
    return newsapi.get_everything(q=query, language='en')

result = get_newsapi_results("pinduoduo")
# print(result)

def parse_articles(result: dict) -> list[dict]:
    parsed = []
    for article in result['articles']:
        item = {
            "title": article['title'],
            "url": article['url'],
            "published": article['publishedAt'],
            "source": article['source']['name'],
        }
        parsed.append(item)
    return parsed

def filter_by_query(articles: list[dict], query: str) -> list[dict]:
    terms = aliases.get(query.lower(), [query.lower()])
    return [
        a for a in articles
        if any(term in a['title'].lower() for term in terms)
    ]

parsed = parse_articles(result)
filtered = filter_by_query(parsed, "pinduoduo")
print(filtered)










