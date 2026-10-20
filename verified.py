# verifier.py
import re
from collections import Counter
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

if __name__ == "__main__":
    summaries = load_summaries("summaries.json")
    lookup = build_lookup(summaries)
    claims = load_summaries("claims.json")
    counts = Counter()
    number_rejections = []
    for claim in claims:
        result = verify(claim, lookup)
        print(f"{claim['claim'][:50]}... -> {result}")
        bucket = result["reason"].split(":")[0]
        counts[bucket] += 1
        if bucket == "missing numbers":
            number_rejections.append((claim, result))

    print("\n--- counts ---")
    for bucket, n in counts.most_common():
        print(f"{bucket}: {n}")

    print("\n--- missing-number rejections (read these) ---")
    for claim, result in number_rejections:
        print(f"CLAIM:  {claim['claim']}")
        print(f"SOURCE: {lookup[normalize(claim['source_url'])]}")
        print(f"REASON: {result['reason']}\n")
