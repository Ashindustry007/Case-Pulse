"""F3 contract guarantees: a surfaced fact cannot exist without a citation + excerpt."""
import pytest
from pydantic import ValidationError

from backend.app import contracts as C

CIT = dict(record_id="note:1", source_type="note", title="t", char_start=0, char_end=4, excerpt="text")


def test_cited_requires_a_citation():
    with pytest.raises(ValidationError):
        C.Cited[float](value=1.0, citations=[])


def test_citation_requires_excerpt():
    with pytest.raises(ValidationError):
        C.Citation(**{**CIT, "excerpt": ""})


def test_assumption_must_cite_unless_not_found():
    with pytest.raises(ValidationError):
        C.Assumption(label="Policy limits", text="$100k")
    C.Assumption(label="Policy limits", text="not found in file", not_found=True)


def test_list_facts_require_citations():
    with pytest.raises(ValidationError):
        C.KeyMoment(rank=1, title="x", importance=9, rank_reason="r", citations=[])
    with pytest.raises(ValidationError):
        C.Injury(name="x", citations=[])


def test_provider_case_omits_unshared_sections():
    case = C.ProviderCase(grant_id=1, policy_version=1, patient_display="J. R.", firm_name="F")
    dumped = case.model_dump(exclude_none=True)
    assert "coverage" not in dumped and "case_value" not in dumped and "bills" not in dumped
