import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import verified
from verified import normalize, missing_numbers, verify


def test_changed_number_is_flagged():
    claim =  "Temu has quietly dismantled a nearly USD$1bn "    # the claim text, as a string
    source = "Temu has quietly dismantled a nearly USD$2bn " 
    assert missing_numbers(claim, source) == ["1"]  # what you expect back


def test_matching_numbers_are_not_flagged():
    claim = "Temu has quietly dismantled a nearly USD$1bn network"
    source = "Temu has quietly dismantled a nearly USD$1bn network"
    assert missing_numbers(claim, source) == []


def test_thousands_separator_is_ignored():
    claim = "The fine was 1,000 euros"
    source = "The fine was 1000 euros"
    assert missing_numbers(claim, source) == []


def test_missing_numbers_are_returned_sorted():
    claim = "Shares rose 3 percent, 1 firm lost 2 jobs"
    source = "Shares rose and a firm lost jobs"
    assert missing_numbers(claim, source) == ["1", "2", "3"]


def test_claim_without_numbers_is_not_flagged():
    claim = "Temu has quietly dismantled its influencer network"
    source = "Temu has quietly dismantled a nearly USD$1bn network"
    assert missing_numbers(claim, source) == []


# --- verify() ---------------------------------------------------------------
# Hand-made lookup: normalized URL -> summary text (same shape build_lookup returns).
LOOKUP = {
    "example.com/temu-fine": "Regulators fined Temu 5 million euros over listings.",
    "example.org/pdd-results": "PDD reported revenue growth and named no figures.",
}


def test_unknown_source_url_is_not_supported():
    claim = {"claim": "Temu was fined 5 million euros", "source_url": "https://nowhere.net/story"}
    assert verify(claim, LOOKUP) == {"supported": False, "reason": "source not found"}


def test_url_variants_still_find_the_source(monkeypatch):
    # www., trailing slash and a query string must all normalize to the same key
    monkeypatch.setattr(verified, "llm_judge", lambda claim_text, source_text: {"supported": True, "reason": "ok"})
    claim = {"claim": "Temu was fined 5 million euros", "source_url": "https://www.Example.com/temu-fine/?utm=x"}
    assert verify(claim, LOOKUP)["supported"] is True


def test_changed_number_is_rejected_without_calling_the_judge(monkeypatch):
    def judge_must_not_run(claim_text, source_text):
        raise AssertionError("llm_judge should not be called when numbers are missing")

    monkeypatch.setattr(verified, "llm_judge", judge_must_not_run)
    claim = {"claim": "Temu was fined 9 million euros", "source_url": "https://example.com/temu-fine"}
    assert verify(claim, LOOKUP) == {"supported": False, "reason": "missing numbers: ['9']"}


def test_clean_claim_is_passed_to_the_judge(monkeypatch):
    calls = []

    def fake_judge(claim_text, source_text):
        calls.append((claim_text, source_text))
        return {"supported": True, "reason": "fake judge"}

    monkeypatch.setattr(verified, "llm_judge", fake_judge)
    claim = {"claim": "PDD reported revenue growth", "source_url": "https://example.org/pdd-results"}

    assert verify(claim, LOOKUP) == {"supported": True, "reason": "fake judge"}
    assert calls == [("PDD reported revenue growth", LOOKUP["example.org/pdd-results"])]
