"""Hackathon rule: Clio is read-only input. Every non-GET call to the Clio API must be refused before any I/O."""
import pytest

from backend.app.clio.client import ClioClient, ReadOnlyViolation, _drop_field


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "post", "delete"])
def test_non_get_is_refused(method):
    c = ClioClient(access_token="dummy")
    with pytest.raises(ReadOnlyViolation):
        c.request(method, "/matters/1.json")


def test_no_write_helpers_exist():
    c = ClioClient(access_token="dummy")
    for name in ("post", "put", "patch", "delete", "create", "update"):
        assert not hasattr(c, name)


def test_drop_field_top_level_and_nested():
    f = "id,name,custom_field_values{id,value},avatar"
    assert _drop_field(f, "avatar") == "id,name,custom_field_values{id,value}"
    assert _drop_field(f, "custom_field_values") == "id,name,avatar"
    assert _drop_field("id,client{id,name,avatar}", "avatar") == "id,client{id,name}"
