# AINewsFeed — Build Plan

Updated Oct 30, 2026 · Adapted from the FX News Agent plan, applied to AINewsFeed instead of EUR/PLN.

## What it is

An agent that answers "What happened with PDD / Temu this week?" from collected news. Every factual claim in the answer is checked against its source before you see it. It's served over MCP and REST, with measured retrieval and answer quality.

**Demo question:** "What happened with Temu this week?" The agent searches stored articles with hybrid search, writes a short answer with cited sources, and runs every claim through the verifier. When the news doesn't cover something, it says so instead of guessing.

**Scope:** PDD Holdings / Pinduoduo / Temu, English-language business news, daily granularity.

**Done means:**

- [ ] Ingesting daily for 30+ days without manual fixes
- [ ] Hybrid retrieval measured against BM25-only and vector-only on your own labelled set, with the numbers in the README
- [ ] Answer quality measured on ~150 labelled questions, with judge agreement reported as a confidence interval
- [ ] `docker compose up` starts everything locally; CI is green
- [ ] A README and one write-up post on how you calibrated the judge

## Current status (Oct 30, 2026)

| Piece | Status |
| --- | --- |
| `api_scrapper.py`: fetch, filter, dedupe, extract text → `articles.json` | Done |
| `summarize_all.py`: 3-bullet summaries → `summaries.json` | Done |
| `writer.py`: claims with `source_url` → `claims.json` | Done (a74e512) |
| `verified.py`: `normalize`, `missing_numbers`, `build_lookup`, `verify` with stub judge, dry-run tally, 9 tests passing | Done (a74e512, c671150) |
| `judge.py`: `build_prompt`, `parse_judge_reply`, `call_claude` with one retry | In progress (707b64b, WIP): 4 of 5 tests in `tests/test_llm_judge.py` fail |
| Real `llm_judge` wired into `verify` (replaces the stub in `verified.py`) | Next |
| ruff, mypy, CI, Postgres, scheduling | Not started |

## Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Language and tooling | Python 3.12, uv, ruff, mypy (strict), pytest | Already using uv and pytest; add ruff and mypy in M0 |
| Database | ParadeDB Docker image | Postgres with pg_search (BM25) and pgvector in one image, so hybrid search is one SQL query |
| News | NewsAPI (current), plus trafilatura for article text | Already working. See open decision on production use |
| Model | Claude Haiku via the Anthropic SDK | Already used in summarize and writer stages |
| Agent | Hand-rolled loop first, then LangGraph | Shows you understand what LangGraph abstracts |
| Serving | FastAPI, plus an MCP server built with the official Python SDK | REST and MCP are both named in AI Engineer postings |
| Observability | Langfuse for traces; Prometheus and Grafana for latency, errors, tokens and cost | Standard, and named in postings |
| Deploy | Docker Compose on a small VPS; GitHub Actions for CI | A live URL beats a local demo |

## Hand-write vs delegate

Hand-write anything an interviewer could ask you to explain or rewrite live. Delegate config and glue.

| Hand-write | Delegate to Claude |
| --- | --- |
| Filters, dedupe, claim extraction logic | pyproject, ruff and mypy config |
| Verifier logic and judge prompt | Loaders, small plumbing helpers |
| SQL schema and the hybrid query (RRF fusion) | Dockerfiles and docker-compose.yml |
| Agent loop and its tools | GitHub Actions workflows |
| LangGraph graph definition | FastAPI and MCP boilerplate around your functions |
| Eval harness, metrics and confidence intervals | Grafana dashboard JSON, Prometheus config |
| Prompt-injection defenses | README badges, Makefile |

**Rule for delegated code:** read every line before you commit it, and be able to say what it does.
**Rule for hand-written code:** ask for hints and skeletons with blanks, not full solutions.

## Milestones

About 8 hours a week. Each line below is one session (60–90 min) with its done-criterion.

### V · Finish the verifier (Oct 19 – Oct 25)

Covers: LLM-as-judge (early M5 work), testing.

- [x] **S1:** Commit `writer.py`, verifier and tests. *Done:* `git status` clean.
- [x] **S1:** Dry run of `verify` on real claims with the stub judge. *Done:* counts for "source not found", "missing numbers", "stub"; 2–3 missing-numbers rejections read and judged as real errors or formatting misses.
- [ ] **S2:** `parse_judge_reply(text)` plus tests: clean JSON, fenced JSON, garbage, missing `supported`. *Done:* tests pass. *Status:* function and tests exist; 4 tests still fail. Left to do: strip code fences before `json.loads`; the parser keeps raising `ValueError`, so change the 3 fallback tests to `pytest.raises(ValueError)`; return `FALLBACK` only after the retry fails, in `call_claude` or `verify`.
- [ ] **S3:** Real `llm_judge` with a strict prompt (supported only if the source states it outright). *Done:* one hand-picked claim gets a sensible verdict.
- [ ] **S3:** Full run on all claims; save `verified.json`. *Done:* counts per outcome, plus one rejection you agree with.

### M0 · Skeleton and CI (Oct 26 – Nov 8)

Covers: tests, linters, type-checkers, Docker.

- [ ] **S1:** Add ruff (config delegated), fix all lint errors yourself. *Done:* `ruff check .` clean.
- [ ] **S2:** Add mypy strict (config delegated), add type hints to `verifier.py`. *Done:* mypy passes on `verifier.py`.
- [ ] **S3:** Type hints for the scraper, summarizer and writer. *Done:* mypy strict passes on the whole repo.
- [ ] **S4:** GitHub Actions running ruff, mypy and pytest (workflow delegated). *Done:* green check on a push.
- [ ] **S5:** Docker Desktop installed; `docker compose up` starts ParadeDB. *Done:* `SELECT extname FROM pg_extension` lists `pg_search` and `vector`.
- [ ] Decide: repo public now? (Recommended: yes, the commit history is part of the signal.)

### M1 · Ingestion into Postgres, daily (Nov 9 – Nov 29)

Covers: PostgreSQL, production habits.

- [ ] **S1:** Design the schema yourself: `articles` (url unique, title, source, published_at, text), `summaries`, `claims`, `verdicts`. *Done:* `schema.sql` creates all tables.
- [ ] **S2:** One-off loader: `articles.json` and `summaries.json` into the database. *Done:* row counts match the JSON files.
- [ ] **S3:** Scraper writes to Postgres instead of JSON; dedupe by unique URL (`ON CONFLICT DO NOTHING`). *Done:* running twice adds no duplicates.
- [ ] **S4:** Summarizer and writer read from and write to the database. *Done:* one full pipeline run, end to end, from DB to DB.
- [ ] **S5:** Roundup filter from TODO.md (cheap LLM check, result cached on the article row). *Done:* a known digest article gets rejected.
- [ ] **S6:** Daily schedule with a log line per run. *Done:* 3 consecutive automatic runs logged.
- [ ] Resolve the NewsAPI production question (see open decisions) before deploying anywhere public.

### M2 · Hybrid retrieval (Nov 30 – Dec 20)

Covers: pgvector, BM25, hybrid search, evaluation-driven development.

- [ ] **S1:** Embeddings column, filled by the ingest job. *Done:* every article has an embedding.
- [ ] **S2:** BM25 index on title and text; `search_bm25(query)`. *Done:* returns 10 rows for "Temu tariffs".
- [ ] **S3:** `search_vector(query)`. *Done:* returns 10 rows.
- [ ] **S4:** `search_news(query)` fuses both with RRF (you write the SQL). *Done:* fused results differ sensibly from both inputs.
- [ ] **S5–S6:** Retrieval set of ~40 queries with relevant article IDs, labelled by you. *Done:* file committed.
- [ ] **S7:** recall@10 and MRR for all three methods. *Done:* table in the README.

### Buffer (Dec 21 – Jan 3)

Holidays. Ingestion keeps running; nothing else is planned.

### M3 · Agent, then LangGraph (Jan 4 – Jan 31)

Covers: tool calling, agent loops, context engineering, LangGraph.

- [ ] **S1:** Tool definitions: `search_news(query, days)` and `get_article(url)`. *Done:* both callable from a script.
- [ ] **S2–S3:** Hand-rolled tool-use loop against the live API. *Done:* answers the demo question with cited links.
- [ ] **S4:** Pipe the agent's answer through claim extraction and `verify`. *Done:* unsupported claims are flagged or removed before output.
- [ ] **S5:** "Not covered by the news" behavior. *Done:* a question with no matching articles gets an honest non-answer.
- [ ] **S6–S7:** Same agent rebuilt in LangGraph. *Done:* same answers; short README note on what LangGraph handled for you.

### M4 · FastAPI and MCP (Feb 1 – Feb 14)

Covers: REST APIs, MCP servers.

- [ ] **S1–S2:** `POST /ask` with request validation and error handling. *Done:* curl returns an answer; bad input returns 422.
- [ ] **S3:** MCP server exposing `search_news` and `get_article`. *Done:* Claude Desktop or Claude Code calls it successfully.
- [ ] **S4:** Short demo recording of an MCP client using your server.

### M5 · Evals and tracing (Feb 15 – Mar 14)

Covers: automated evals, LLM-as-judge, Langfuse.

- [ ] **S1–S3:** Answer set of ~150 questions with your reference answers and sources.
- [ ] **S4:** Judge rubric: correct, grounded in cited articles, admits gaps.
- [ ] **S5–S6:** Calibrate the judge on ~50 questions you labelled pass/fail. *Done:* agreement and Cohen's kappa with bootstrap 95% CIs.
- [ ] **S7:** Calibrate the claim verifier the same way on ~50 labelled claims.
- [ ] **S8:** Langfuse trace for every run. *Done:* one full agent run visible as a trace.
- [ ] **S9:** 20-question smoke eval in CI.

### M6 · Ops and red team (Mar 15 – Mar 28)

Covers: Prometheus, Grafana, red teaming, prompt caching.

- [ ] **S1:** Prometheus metrics for latency, errors, tokens and cost; one Grafana dashboard.
- [ ] **S2:** Prompt caching on, latency and cost measured before and after.
- [ ] **S3–S4:** Injection set: ~30 fake articles carrying instructions. Attack success rate before and after mitigations in the README. (Scraped pages are untrusted input, so this matters for your pipeline specifically.)

### M7 · Write-up and demo (Mar 29 – Apr 11)

- [ ] README with architecture diagram, results tables and one-command start
- [ ] One write-up post on judge calibration
- [ ] Two-minute demo video

## Eval plan

Every number in the README comes from a hand-built test set, versioned in the repo.

| Set | Size | Question it answers | Method |
| --- | --- | --- | --- |
| Claims | ~50 claims labelled supported / unsupported | Can the verifier be trusted? | Agreement and Cohen's kappa, bootstrap 95% CI |
| Retrieval | ~40 queries with relevant article IDs | Does hybrid beat BM25-only and vector-only? | recall@10 and MRR per method |
| Answers | ~150 questions with reference answers and sources | Is the answer correct and grounded? | LLM-as-judge rubric |
| Judge calibration | ~50 of the 150, labelled pass/fail by you | Can the answer judge be trusted? | Agreement and Cohen's kappa, bootstrap 95% CI |
| Injection | ~30 fake articles carrying instructions | Does untrusted text steer the agent? | Attack success rate before and after mitigations |

**Where questions come from:** pick weeks with real PDD/Temu news (earnings, regulation, tariffs, lawsuits), read that week's articles yourself, and write the reference answer. Include quiet weeks where the right answer is "no significant news."

**In CI:** the 20-question smoke subset on every push to main; the full set before each release.

## Session rules

- One session = 60–90 minutes, with one done-criterion written before you start.
- Two fixed weekday slots plus one weekend slot. A missed slot is skipped, not made up.
- Run code within the first 15 minutes. Reading docs alone doesn't count as a session.
- Commit at the end of every session, on a branch if it's broken.
- Stuck over 30 minutes on config or tooling: delegate it. Stuck on core logic: ask for hints.
- Each piece follows Identify → Set Up → Execute → Evaluate.

## Risks

- **ISYE 6740 starts January 2027.** If 8 hours a week stops being realistic, stretch M3–M7 by about 50% instead of cutting evals. The evals are the differentiator.
- **Scope creep from the verifier.** It's tempting to keep polishing it. Once V is done, it's good enough until M5.

## Open decisions

- [ ] **NewsAPI in production.** The free Developer plan is for development and testing only, not staging or production; articles are delayed 24 hours and search goes back one month. Paid plans start at $449/month. Options: keep ingestion running locally as a dev job, switch to RSS feeds (company press-release feeds, business news), or evaluate another free source. Decide in M1.
- [ ] **Storing full article text.** Fine locally for summarizing. For a public deploy, serve only titles, your summaries and links, not scraped full text.
- [ ] **Embeddings:** hosted API or a local model? Decide on the M2 retrieval set, quality vs cost. English-only content makes this simpler than the FX plan.
- [ ] **VPS:** which provider, and the monthly budget.
- [ ] **Repo public from day one?** Recommended: yes.
- [x] **Reuse existing code or start fresh?** Reuse. Filters, `normalize`, `missing_numbers` and the verifier carry over.

## Sources

- [NewsAPI pricing and plan terms](https://newsapi.org/pricing)
- [NBP Web API](https://api.nbp.pl/en.html) (not used; kept for reference from the FX plan)
- [ParadeDB on Railway: bundled extensions](https://railway.com/deploy/paradedb-railway)
