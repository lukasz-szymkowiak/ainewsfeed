# verifier.py
import re
from urllib.parse import urlsplit
import json
from pathlib import Path

def normalize(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    return f"{host}{path}"

def missing_numbers(claim_text: str, summary_text: str) -> list[str]:
    claims_numbers = {n.replace(",", "") for n in re.findall(r"\d+(?:[.,]\d+)*", claim_text)}
    summaries_numbers = {n.replace(",", "") for n in re.findall(r"\d+(?:[.,]\d+)*", summary_text)}
    matching_numbers = set(claims_numbers).difference(set(summaries_numbers))
    return sorted(matching_numbers)

def llm_judge(claim_text, source_text):
    return {"supported": False, "reason": "stub"}

def load_summaries(path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)

def build_lookup(summaries):
    lookup = {}
    for item in summaries:
        key = normalize(item["url"])
        if key in lookup:
            print(f"warning: duplicate URL after normalize, keeping first: {key}")
            continue
        lookup[key] = item["summary"]
    return lookup

def verify(claim, lookup):
    claim_text = claim["claim"]          # check the real key name in claims.json
    key = normalize(claim["source_url"])

    if key not in lookup:
        return {"supported": False, "reason": "source not found"}

    source_text = lookup[key]

    missing = missing_numbers(claim_text, source_text)
    if missing:
        return {"supported": False, "reason": f"missing numbers: {missing}"}

    return llm_judge(claim_text, source_text)