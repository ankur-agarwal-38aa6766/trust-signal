import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def heading_anchors(body: str) -> set[str]:
    anchors = set(re.findall(r'<a\s+(?:id|name)=["\x27]([^"\x27]+)', body))
    seen: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*$", body, flags=re.MULTILINE):
        heading = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", heading)
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        occurrence = seen.get(slug, 0)
        seen[slug] = occurrence + 1
        anchors.add(slug if not occurrence else f"{slug}-{occurrence}")
    return anchors


def test_repository_markdown_relative_links():
    # Git's inventory excludes ignored evidence, builds and private local files.
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    errors = []
    count = 0
    for path in paths:
        file = ROOT / path
        # Deleted tracked files remain in `git ls-files --cached` until commit.
        if not file.is_file():
            continue
        body = re.sub(r"```.*?```", "", file.read_text(), flags=re.DOTALL)
        links = re.findall(
            r'(?<!!)\[[^\]\n]+\]\(([^\s)]+)(?:\s+"[^"]*")?\)', body
        )
        for raw in links:
            raw = raw.strip("<>")
            url = urlsplit(raw)
            if url.scheme or url.netloc:
                continue
            count += 1
            target = (file.parent / unquote(url.path)).resolve() if url.path else file
            if not target.exists():
                errors.append(f"{path} -> {raw}: missing path")
            elif (
                url.fragment
                and target.suffix == ".md"
                and unquote(url.fragment) not in heading_anchors(target.read_text())
            ):
                errors.append(f"{path} -> {raw}: missing anchor")
    assert count > 0
    assert not errors, "\n".join(errors)
