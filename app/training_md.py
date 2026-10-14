"""Tiny markdown-to-HTML for the training guide page.
Supports the subset used in AMANDA_TRAINING_GUIDE.md:
# / ## headings, **bold**, *italic*, --- rules, * and 1. lists, paragraphs.
No external dependencies (keeps the Vercel function light)."""
import html
import re


def _inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def render(md: str) -> str:
    out = []
    in_list = None  # None, "ul", "ol"
    for raw in md.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            if in_list:
                out.append(f"</{in_list}>")
                in_list = None
            continue
        if stripped == "---":
            if in_list:
                out.append(f"</{in_list}>")
                in_list = None
            out.append("<hr>")
            continue
        if stripped.startswith("## "):
            if in_list:
                out.append(f"</{in_list}>")
                in_list = None
            out.append(f"<h2>{_inline(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            if in_list:
                out.append(f"</{in_list}>")
                in_list = None
            out.append(f"<h1>{_inline(stripped[2:])}</h1>")
            continue
        m = re.match(r"^(\*|\d+\.)\s+(.*)$", stripped)
        if m:
            kind = "ul" if m.group(1) == "*" else "ol"
            if in_list != kind:
                if in_list:
                    out.append(f"</{in_list}>")
                out.append(f"<{kind}>")
                in_list = kind
            out.append(f"<li>{_inline(m.group(2))}</li>")
            continue
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None
        out.append(f"<p>{_inline(stripped)}</p>")
    if in_list:
        out.append(f"</{in_list}>")
    return "\n".join(out)
