"""Tests for shared command helpers."""

from __future__ import annotations

from ignition_cli.commands._common import extract_items, extract_metadata


class TestExtractItems:
    def test_list_passthrough(self):
        data = [{"name": "a"}, {"name": "b"}]
        assert extract_items(data) == data

    def test_dict_with_items(self):
        data = {"items": [1, 2, 3], "metadata": {"total": 3}}
        assert extract_items(data) == [1, 2, 3]

    def test_dict_with_fallback_key(self):
        data = {"resources": [{"name": "r1"}]}
        assert extract_items(data, "resources") == [{"name": "r1"}]

    def test_dict_items_takes_precedence(self):
        data = {"items": [1], "resources": [2]}
        assert extract_items(data, "resources") == [1]

    def test_dict_no_matching_key(self):
        data = {"other": "value"}
        assert extract_items(data) == []

    def test_dict_multiple_fallbacks(self):
        data = {"logs": [{"msg": "hello"}]}
        assert extract_items(data, "entries", "logs") == [{"msg": "hello"}]

    def test_none_returns_empty(self):
        assert extract_items(None) == []

    def test_string_returns_empty(self):
        assert extract_items("not a list") == []

    def test_empty_items(self):
        assert extract_items({"items": []}) == []


class TestExtractMetadata:
    def test_with_metadata(self):
        data = {
            "items": [],
            "metadata": {"total": 100, "matching": 50, "limit": 25, "offset": 0},
        }
        meta = extract_metadata(data)
        assert meta["total"] == 100
        assert meta["matching"] == 50

    def test_without_metadata(self):
        assert extract_metadata({"items": []}) == {}

    def test_non_dict(self):
        assert extract_metadata([1, 2, 3]) == {}

    def test_none(self):
        assert extract_metadata(None) == {}
