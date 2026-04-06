from __future__ import annotations

import json
import re
import urllib.request

from common import SKILL_ROOT, ssl_context


SNAPSHOT_SOURCES = {
    2023: "https://ccf.atom.im/v6/",
    2024: "https://ccf.atom.im/v6.1/",
    2025: "https://ccf.atom.im/v6.1/",
    2026: "https://ccf.atom.im/v6.1/",
}

ROW_RE = re.compile(
    r"<tr class=\"item\"[^>]*>\s*<th scope=\"row\">(?P<index>.*?)</th>\s*<td>(?P<abbr>.*?)</td>\s*<td><a href=\"(?P<dblp>.*?)\"[^>]*>(?P<full>.*?)</a></td>\s*<td>(?P<classification>.*?)</td>\s*<td>(?P<kind>.*?)</td>\s*<td>(?P<field>.*?)</td>",
    re.S,
)


def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("&amp;", "&").replace("&quot;", "\"").replace("&#39;", "'").replace("&nbsp;", " ").strip()


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ccf-paper-search/0.1"})
    with urllib.request.urlopen(req, context=ssl_context()) as resp:
        return resp.read().decode("utf-8")


def alias_list(abbr: str, full_name: str) -> list[str]:
    aliases = [abbr, full_name]
    replacements = {
        "USENIX Annual Technical Conference": ["USENIX ATC", "ACM SIGOPS ATC"],
        "ACM SIGOPS Annual Technical Conference": ["USENIX ATC", "ACM SIGOPS ATC"],
    }
    aliases.extend(replacements.get(full_name, []))
    return sorted({alias for alias in aliases if alias})


def main() -> None:
    target_root = SKILL_ROOT / "data" / "ccf_snapshots"
    target_root.mkdir(parents=True, exist_ok=True)
    for year, url in SNAPSHOT_SOURCES.items():
        html = fetch_html(url)
        items = []
        for match in ROW_RE.finditer(html):
            classification = strip_tags(match.group("classification"))
            kind = strip_tags(match.group("kind"))
            if classification != "A" or kind != "会议":
                continue
            abbr = strip_tags(match.group("abbr"))
            full_name = strip_tags(match.group("full"))
            field = strip_tags(match.group("field"))
            items.append(
                {
                    "abbr": abbr,
                    "full_name": full_name,
                    "dblp_url": strip_tags(match.group("dblp")),
                    "field": field,
                    "aliases": alias_list(abbr, full_name),
                }
            )
        with (target_root / f"{year}-a.json").open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"{year}: {len(items)} A conferences")


if __name__ == "__main__":
    main()
