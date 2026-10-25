import json

import pytest

from app.ingestion.parsers import UnsupportedFormatError, parse_file


def test_txt(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world", encoding="utf-8")
    docs = parse_file(f)
    assert docs[0].text == "hello world" and docs[0].format == "txt"


def test_md_title(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("# My Title\n\nBody", encoding="utf-8")
    assert parse_file(f)[0].title == "My Title"


def test_html_strips_scripts(tmp_path):
    f = tmp_path / "a.html"
    f.write_text("<html><title>T</title><script>x=1</script><p>Hi</p></html>", encoding="utf-8")
    doc = parse_file(f)[0]
    assert doc.title == "T" and "x=1" not in doc.text and "Hi" in doc.text


def test_json_array(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json.dumps([{"title": "A", "text": "one"}, {"text": "two"}]), encoding="utf-8")
    docs = parse_file(f)
    assert len(docs) == 2 and docs[0].title == "A"


def test_unsupported(tmp_path):
    f = tmp_path / "a.xyz"
    f.write_text("x")
    with pytest.raises(UnsupportedFormatError):
        parse_file(f)