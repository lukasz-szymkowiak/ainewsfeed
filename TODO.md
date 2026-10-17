# TODO

## Filter multi-topic roundups out of the feed

**Problem:** the filters in `NewsAPI/api_scrapper.py` only check that the company is named in the
title and that a business word appears in the title or description. They never check whether the
article is mainly *about* the company.

**Example:** the ExchangeWire "Digest: McDonald's Bets on $1bn Ad Business; Temu Cuts Fake
Influencer Network on Meta" (first entry in `articles.json`) passes every filter. Its body also
covers TikTok's settlement with Alabama, so `read_json.py` summarizes unrelated stories.

**Idea (do later):**
- Add a cheap LLM call (e.g. a Haiku-class model) that reads the article body and answers whether
  the article contains something specific about PDD Holdings, Pinduoduo or Temu.
- Run it as the last step, after `dedupe_by_title` and `add_article_text`, so only articles that
  already passed the keyword filters and have text are sent.
- Keep the result with the article (e.g. a boolean plus a one-line reason) so it is cached in
  `articles.json` and not re-asked on every run.

**Open questions:**
- Reject the whole article, or only tell the summarizer which part to focus on?
- A quick title-based pre-check may also help (digests use `;` and the word "Digest").
