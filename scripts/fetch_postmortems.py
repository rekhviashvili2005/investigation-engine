import argparse
import hashlib
import re
import time
from pathlib import Path

import httpx

README_URL = "https://raw.githubusercontent.com/danluu/post-mortems/master/README.md"
OUT = Path("data/postmortems")
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def extract_links(readme: str) -> list[tuple[str, str]]:
    seen, out = set(), []
    for title, url in LINK_RE.findall(readme):
        if "github.com/danluu" in url or url in seen:
            continue
        seen.add(url)
        out.append((title.strip(), url))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=120)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 (research project)"}
    with httpx.Client(timeout=15, follow_redirects=True, headers=headers) as client:
        readme = client.get(README_URL).text
        links = extract_links(readme)
        print(f"Links found: {len(links)}")

        saved = 0
        for title, url in links:
            if saved >= args.limit:
                break
            name = hashlib.sha1(url.encode()).hexdigest()[:12]
            path = OUT / f"{name}.html"
            if path.exists():
                saved += 1
                continue
            try:
                r = client.get(url)
                ctype = r.headers.get("content-type", "")
                if r.status_code != 200 or "html" not in ctype:
                    continue
                path.write_text(
                    f"<!-- source: {url} -->\n<!-- label: {title} -->\n{r.text}",
                    encoding="utf-8",
                )
                saved += 1
                print(f"  saved {saved}: {title[:50]}")
            except Exception as e:      # მკვდარი ბმული, timeout, SSL და ა.შ.
                print(f"  skip {url[:60]} ({type(e).__name__})")
            time.sleep(0.5)             # თავაზიანი tempo
    print(f"Done. {saved} files in {OUT}")


if __name__ == "__main__":
    main()