"""F3: citations map to exact source spans; unverifiable quotes are rejected; retrieval works on the fake matter."""
from types import SimpleNamespace

from backend.app.db import connect
from backend.app.documents.processor import process_matter_documents
from backend.app.rag.chunker import chunk_text, sentence_units
from backend.app.rag.cite import ResultRegistry, record_citation, verify_quote
from backend.app.rag.index import build_index
from backend.app.rag.search import hybrid_search
from backend.app.sync.engine import sync_matter
from backend.tests.fake_clio import MATTER_ID


def test_units_are_exact_spans():
    text = "First sentence here. Second one follows!\nThird line without period"
    units = sentence_units(text)
    assert [text[s:e] for s, e in units] == ["First sentence here.", "Second one follows!", "Third line without period"]
    ch = chunk_text(text)[0]
    assert ch.text == text[ch.char_start:ch.char_end]


def test_pipeline_index_search_and_cite(tmp_db, fake_clio):
    sync_matter(MATTER_ID, client=fake_clio)
    with connect() as db:
        st = process_matter_documents(db, fake_clio, MATTER_ID)
        assert st["processed"] == 1 and st["pending_ocr"] == 1  # page 2 is an image-only "scan"
        s1 = build_index(db, MATTER_ID)
        assert s1["chunks"] > 10
        s2 = build_index(db, MATTER_ID)
        assert s2["reindexed"] == 0 and s2["chunks"] == 0  # hash-gated: nothing re-embedded

        hits = hybrid_search(db, MATTER_ID, "independent medical examination requested by the adjuster", k=5)
        assert hits and hits[0].record_id == "communication:20"
        hits_docs = hybrid_search(db, MATTER_ID, "cervical strain assessment", types=["document"], k=3)
        assert hits_docs and hits_docs[0].page == 1

        # search_result round trip: cite block 1 of the first hit → exact span in the source text
        reg = ResultRegistry()
        blocks = reg.blocks(hits[:2])
        assert blocks[0]["citations"] == {"enabled": True} and len(blocks[0]["content"]) == len(hits[0].units)
        loc = SimpleNamespace(search_result_index=0, start_block_index=1, end_block_index=2,
                              cited_text=blocks[0]["content"][1]["text"])
        c = reg.to_citation(loc)
        body = db.execute("SELECT body_text FROM records WHERE id=?", (c.record_id,)).fetchone()[0]
        assert body[c.char_start:c.char_end] == blocks[0]["content"][1]["text"]

        # model quotes: verified when present (even with whitespace drift), rejected when fabricated
        ok = verify_quote(db, "note:1", None, "taken to the  ER")
        assert ok and "taken to the ER" in ok.excerpt
        assert verify_quote(db, "note:1", None, "client sustained a fractured femur in a boating accident") is None

        # deterministic structured citation
        bc = record_citation(db, "medical_bill:81")
        assert bc.excerpt.startswith("Medical bill · Lakeside Orthopedics · $22,140.00")
