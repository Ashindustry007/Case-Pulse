"""F9: an unchanged case is never re-digested — the second digest run makes zero LLM calls; an edit re-digests
exactly the changed record."""
import time
from types import SimpleNamespace

from backend.app.ai import digest as D
from backend.app.db import connect
from backend.app.sync.engine import sync_matter
from backend.tests.fake_clio import MATTER_ID


def test_digest_is_hash_cached(tmp_db, fake_clio, monkeypatch):
    calls = []

    def fake_parsed(purpose, model, output_format, **kw):
        text = kw["messages"][0]["content"]
        ids = [seg.split('"')[0] for seg in text.split('<item record_id="')[1:]]
        calls.append(ids)
        items = [D.ItemDigest(record_id=i, one_liner="x", category="other", importance=5, importance_reason="r",
                              why_it_matters="w", client_contact=False, waiting_on=None, confidential=False,
                              provider_safe_summary="s") for i in ids]
        usage = SimpleNamespace(input_tokens=1000, output_tokens=100, cache_read_input_tokens=0,
                                cache_creation_input_tokens=0)
        return D.DigestBatch(items=items), SimpleNamespace(model=model, usage=usage)

    monkeypatch.setattr(D, "call_claude_parsed", fake_parsed)
    sync_matter(MATTER_ID, client=fake_clio)
    with connect() as db:
        first = D.digest_matter(db, MATTER_ID)
        assert first["digested"] > 0 and first["skipped"] == 0
        n_calls = len(calls)
        second = D.digest_matter(db, MATTER_ID)
        assert second["digested"] == 0 and second["skipped"] == first["digested"]
        assert len(calls) == n_calls  # ZERO new LLM calls
        saved = db.execute("SELECT saved_usd FROM ai_runs WHERE cache_hit=1 ORDER BY id DESC LIMIT 1").fetchone()[0]
        assert saved > 0  # F10 "saved by cache"
    time.sleep(1.1)
    fake_clio.edit_note(1, "Updated intake note.")
    sync_matter(MATTER_ID, client=fake_clio)
    with connect() as db:
        third = D.digest_matter(db, MATTER_ID)
    assert third["digested"] == 1 and calls[-1] == ["note:1"]
