from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    title: str
    source: str          # ფაილის გზა ან dataset-ის იდენტიფიკატორი
    format: str          # txt, md, html, pdf, json
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Chunk:
    index: int
    text: str
    start_char: int
    end_char: int