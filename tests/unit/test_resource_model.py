"""Tests for the Resource model with files/signature fields."""

from ignition_cli.models.resource import Resource


class TestResourceModel:
    def test_basic_resource(self):
        r = Resource(name="my-db", type="ignition/database-connection")
        assert r.name == "my-db"
        assert r.type == "ignition/database-connection"
        assert r.files is None
        assert r.signature is None

    def test_resource_with_files(self):
        r = Resource(name="my-theme", files=["style.css", "logo.png", "font.woff2"])
        assert r.files == ["style.css", "logo.png", "font.woff2"]

    def test_resource_with_empty_files(self):
        r = Resource(name="empty-res", files=[])
        assert r.files == []

    def test_resource_with_signature(self):
        r = Resource(name="my-res", signature="abc123def")
        assert r.signature == "abc123def"

    def test_resource_with_all_fields(self):
        r = Resource(
            name="full-res",
            type="ignition/theme",
            config={"key": "value"},
            state="RUNNING",
            files=["a.css", "b.js"],
            signature="sig456",
        )
        assert r.name == "full-res"
        assert r.type == "ignition/theme"
        assert r.config == {"key": "value"}
        assert r.state == "RUNNING"
        assert r.files == ["a.css", "b.js"]
        assert r.signature == "sig456"
