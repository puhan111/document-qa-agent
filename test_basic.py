import pytest
from parse import _clean, parse_file
from ingest import chunk_text


def test_chunk_text_basic():
    """块长5、重叠2，正确分块且不重叠。"""
    result = chunk_text("0123456789", chunk_size=5, chunk_overlap=2)
    assert result == ["01234", "34567", "6789"]


def test_chunk_text_short_text():
    """文本比块长短时，只切一块。"""
    assert chunk_text("abc", chunk_size=10, chunk_overlap=2) == ["abc"]


def test_chunk_text_no_redundant_tail():
    """刚好切满时，不产生多余的重复小片段（之前修过的边界 bug）。"""
    assert chunk_text("0123456789", chunk_size=4, chunk_overlap=1) == ["0123", "3456", "6789"]


def test_clean_removes_trailing_spaces_and_blank_lines():
    """去掉行尾空格和空行。"""
    assert _clean("hello  \n\n  \nworld\n") == "hello\nworld"


def test_parse_file_unsupported_type():
    """不支持的扩展名要抛 ValueError。"""
    with pytest.raises(ValueError):
        parse_file("data.txt")