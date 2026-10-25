import json
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from app.ingestion.models import ParsedDocument


class UnsupportedFormatError(Exception):
    """უცნობი ფაილის ფორმატი."""


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_txt(path: Path) -> list[ParsedDocument]:
    return [ParsedDocument(
        title=path.stem, source=str(path), format="txt", text=_read_text(path),
    )]


def parse_md(path: Path) -> list[ParsedDocument]:
    text = _read_text(path)
    title = path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()   # პირველი # სათაური
            break
    return [ParsedDocument(title=title, source=str(path), format="md", text=text)]


def parse_html(path: Path) -> list[ParsedDocument]:
    soup = BeautifulSoup(_read_text(path), "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()                # ტექსტს არ ვუშვებთ
    title = soup.title.get_text(strip=True) if soup.title else path.stem
    text = soup.get_text(separator="\n", strip=True)
    return [ParsedDocument(title=title, source=str(path), format="html", text=text)]


def parse_pdf(path: Path) -> list[ParsedDocument]:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    text = "\n\n".join(pages)
    return [ParsedDocument(
        title=path.stem, source=str(path), format="pdf", text=text,
        metadata={"pages": len(pages)},
    )]


def parse_json(path: Path) -> list[ParsedDocument]:
    """JSON: ობიექტი ან ობიექტების მასივი. თითო ობიექტი = ერთი დოკუმენტი."""
    data = json.loads(_read_text(path))
    items = data if isinstance(data, list) else [data]
    docs = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        text = item.get("text") or item.get("content") or ""
        if not text:
            continue
        docs.append(ParsedDocument(
            title=str(item.get("title", f"{path.stem}-{i}")),
            source=f"{path}#{i}",
            format="json",
            text=text,
            metadata={k: v for k, v in item.items() if k not in ("text", "content")},
        ))
    return docs


PARSERS = {
    ".txt": parse_txt,
    ".md": parse_md,
    ".html": parse_html,
    ".htm": parse_html,
    ".pdf": parse_pdf,
    ".json": parse_json,
}


def parse_file(path: str | Path) -> list[ParsedDocument]:
    path = Path(path)
    parser = PARSERS.get(path.suffix.lower())
    if parser is None:
        raise UnsupportedFormatError(f"Unsupported format: {path.suffix}")
    return parser(path)