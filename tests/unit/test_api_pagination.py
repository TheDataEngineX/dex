"""Tests for cursor-based pagination utilities."""

from __future__ import annotations

import pytest

from dataenginex.api.pagination import (
    PaginatedResponse,
    PaginationMeta,
    decode_cursor,
    encode_cursor,
    paginate,
)


class TestCursorEncoding:
    def test_encode_then_decode_roundtrip(self) -> None:
        assert decode_cursor(encode_cursor(0)) == 0
        assert decode_cursor(encode_cursor(42)) == 42
        assert decode_cursor(encode_cursor(999)) == 999

    def test_decode_invalid_cursor_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid pagination cursor"):
            decode_cursor("not-valid-base64!!")

    def test_decode_missing_offset_key_raises(self) -> None:
        import base64
        import json

        bad = base64.urlsafe_b64encode(json.dumps({"x": 1}).encode()).decode()
        with pytest.raises(ValueError, match="Invalid pagination cursor"):
            decode_cursor(bad)


class TestPaginate:
    def test_first_page_no_cursor(self) -> None:
        items = list(range(50))
        result = paginate(items, limit=10)
        assert isinstance(result, PaginatedResponse)
        assert result.data == list(range(10))
        assert result.pagination.total == 50
        assert result.pagination.has_next is True
        assert result.pagination.has_previous is False
        assert result.pagination.next_cursor is not None

    def test_last_page_no_next_cursor(self) -> None:
        items = list(range(5))
        result = paginate(items, limit=10)
        assert result.data == list(range(5))
        assert result.pagination.has_next is False
        assert result.pagination.next_cursor is None

    def test_cursor_advances_page(self) -> None:
        items = list(range(30))
        first = paginate(items, limit=10)
        second = paginate(items, cursor=first.pagination.next_cursor, limit=10)
        assert second.data == list(range(10, 20))
        assert second.pagination.has_previous is True

    def test_invalid_cursor_resets_to_first_page(self) -> None:
        items = list(range(10))
        result = paginate(items, cursor="bad-cursor", limit=5)
        assert result.data == list(range(5))

    def test_limit_clamped_to_max(self) -> None:
        items = list(range(200))
        result = paginate(items, limit=500)
        assert len(result.data) == 100  # max_limit default

    def test_limit_minimum_is_one(self) -> None:
        items = list(range(10))
        result = paginate(items, limit=0)
        assert len(result.data) == 1

    def test_empty_list(self) -> None:
        result = paginate([])
        assert result.data == []
        assert result.pagination.total == 0
        assert result.pagination.has_next is False

    def test_pagination_meta_model(self) -> None:
        meta = PaginationMeta(total=100, limit=20, has_next=True, next_cursor="abc")
        assert meta.has_previous is False
