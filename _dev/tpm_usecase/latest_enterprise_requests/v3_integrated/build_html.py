#!/usr/bin/env python3
"""Build a single-file index.html for v3_integrated/ from the markdown files.

Renders each numbered .md as its own section, with a sticky TOC, polished CSS, and
cross-links rewritten so file references like `01_organization.md` jump to the
in-page anchor `#sec-01-organization`. Outputs to v3_integrated/index.html.

No external dependencies (uses only the Python stdlib + a tiny markdown subset).
"""

from __future__ import annotations
import html
import os
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "index.html"

# Order matters
DOC_ORDER = [
    ("README.md", "Overview"),
    ("01_organization.md", "1 · Organization"),
    ("02_demand_overview.md", "2 · Demand Overview"),
    ("03_master_mapping.md", "3 · Master Mapping"),
    ("04_open_blockers.md", "4 · Open Blockers"),
    ("05_recent_inbox.md", "5 · Recent Inbox"),
    ("06_voc_sources.md", "6 · VoC Sources"),
    ("07_new_project_candidates.md", "7 · New Project Candidates"),
    ("08_mustwin_template.md", "8 · MUSTWIN Template"),
    ("09_audit_log.md", "9 · Audit Log"),
    ("10_blueprint.md", "10 · Blueprint"),
    ("11_validation_stack.md", "11 · Validation Stack (Tier 1/2/3)"),
    ("12_eval_actor_stack.md", "12 · Eval Actor Stack (L0–L4)"),
    ("13_maturity_model.md", "13 · Maturity Model (Stage 0–4)"),
    ("14_metrics.md", "14 · Metrics & Time-to-Intent"),
    ("15_deep_org.md", "15 · Deep Org (per-pillar)"),
    ("16_operations.md", "16 · Operations / Policies / Guardrails"),
]


# --------------------------- Tiny markdown renderer ---------------------------

INLINE_CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^\*]+)\*\*")
ITALIC_RE = re.compile(r"(?<!\*)\*([^\*\n]+)\*(?!\*)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
STRIKE_RE = re.compile(r"~~([^~]+)~~")


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^a-zA-Z0-9\- ]+", "", text)
    return re.sub(r"\s+", "-", text.strip().lower())


def inline_md(s: str) -> str:
    """Apply inline markdown transforms; HTML-escape first."""
    s = html.escape(s, quote=False)
    # links must come before bold/italic (so the link text is still escaped raw)
    def repl_link(m):
        text, url = m.group(1), m.group(2)
        # Rewrite cross-doc links to in-page anchors
        for fname, _label in DOC_ORDER:
            if url == fname or url.endswith("/" + fname):
                return f'<a href="#sec-{slugify(fname.replace(".md",""))}">{text}</a>'
        ext = " target=\"_blank\" rel=\"noopener\"" if url.startswith("http") else ""
        return f'<a href="{html.escape(url, quote=True)}"{ext}>{text}</a>'
    s = LINK_RE.sub(repl_link, s)
    s = INLINE_CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", s)
    s = STRIKE_RE.sub(lambda m: f"<del>{m.group(1)}</del>", s)
    s = BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", s)
    s = ITALIC_RE.sub(lambda m: f"<em>{m.group(1)}</em>", s)
    return s


def render_table(rows: list[str]) -> str:
    """rows = list of '| a | b |' lines INCLUDING the separator '|---|---|'."""
    if len(rows) < 2:
        return ""
    header = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    body = []
    for r in rows[2:]:  # skip header + separator
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        body.append("<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in cells) + "</tr>")
    return (
        "<div class='table-wrap'><table><thead><tr>"
        + "".join(f"<th>{inline_md(h)}</th>" for h in header)
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def render_md(text: str, section_anchor: str) -> str:
    out = []
    lines = text.splitlines()
    i = 0
    in_code = False
    code_buf = []
    code_lang = ""
    while i < len(lines):
        line = lines[i]

        # fenced code blocks
        if line.startswith("```"):
            if in_code:
                out.append(
                    f"<pre><code class='lang-{code_lang}'>"
                    + html.escape("\n".join(code_buf), quote=False)
                    + "</code></pre>"
                )
                in_code = False
                code_buf = []
                code_lang = ""
            else:
                in_code = True
                code_lang = line.strip("`").strip()
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # tables (header line then '|---|...|')
        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"\s*\|[ \-:|]+\|\s*$", lines[i + 1]):
            tbl = [line, lines[i + 1]]
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                tbl.append(lines[j])
                j += 1
            out.append(render_table(tbl))
            i = j
            continue

        # ATX headings
        m = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if m:
            level = len(m.group(1))
            text_md = m.group(2)
            slug = slugify(text_md)
            anchor_id = f"{section_anchor}--{slug}" if level > 1 else section_anchor
            out.append(f'<h{level} id="{anchor_id}">{inline_md(text_md)}</h{level}>')
            i += 1
            continue

        # blockquote (consume contiguous '> ' lines)
        if line.lstrip().startswith(">"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            inner = "<br>".join(inline_md(b) for b in buf)
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        # unordered lists
        if re.match(r"^\s*[\*\-]\s+", line):
            buf = []
            while i < len(lines) and re.match(r"^\s*[\*\-]\s+", lines[i]):
                buf.append(re.sub(r"^\s*[\*\-]\s+", "", lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline_md(b)}</li>" for b in buf) + "</ul>")
            continue

        # ordered lists
        if re.match(r"^\s*\d+\.\s+", line):
            buf = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                buf.append(re.sub(r"^\s*\d+\.\s+", "", lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{inline_md(b)}</li>" for b in buf) + "</ol>")
            continue

        # horizontal rule
        if re.match(r"^\s*---+\s*$", line):
            out.append("<hr>")
            i += 1
            continue

        # blank line
        if not line.strip():
            i += 1
            continue

        # paragraph (consume until blank line / structural)
        para = [line]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].lstrip().startswith(("#", ">", "|", "*", "-"))
            and not re.match(r"^\s*\d+\.\s+", lines[i])
            and not re.match(r"^\s*---+\s*$", lines[i])
            and not lines[i].startswith("```")
        ):
            para.append(lines[i])
            i += 1
        out.append("<p>" + inline_md(" ".join(para)) + "</p>")

    return "\n".join(out)


# --------------------------- Build the HTML ---------------------------

def build_doc_section(fname: str, label: str) -> tuple[str, list[tuple[str, str]]]:
    """Returns (html_section, list of (h2_id, h2_text) for the TOC)."""
    path = ROOT / fname
    if not path.exists():
        return f"<section><h2>{label}</h2><p><em>(missing: {fname})</em></p></section>", []
    text = path.read_text(encoding="utf-8")
    section_anchor = "sec-" + slugify(fname.replace(".md", ""))
    body = render_md(text, section_anchor)

    # collect h2 ids from rendered body for sub-TOC
    h2s = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body)

    return (
        f'<section id="{section_anchor}" class="doc">{body}</section>',
        h2s,
    )


def main() -> None:
    sections_html = []
    nav = []
    for fname, label in DOC_ORDER:
        sec_html, h2s = build_doc_section(fname, label)
        sections_html.append(sec_html)
        section_anchor = "sec-" + slugify(fname.replace(".md", ""))
        sub = "".join(
            f'<li><a href="#{hid}">{re.sub("<[^>]+>", "", htext)}</a></li>'
            for hid, htext in h2s[:8]  # cap
        )
        nav.append(
            f'<li class="nav-doc"><a href="#{section_anchor}">{html.escape(label)}</a>'
            + (f'<ul class="nav-sub">{sub}</ul>' if sub else "")
            + "</li>"
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html_out = TEMPLATE.format(
        timestamp=timestamp,
        nav="".join(nav),
        body="\n".join(sections_html),
    )
    OUT.write_text(html_out, encoding="utf-8")
    print(f"wrote {OUT}  ({len(html_out):,} bytes)")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Enterprise Demand → Core Engineering Mapping (v3 integrated)</title>
<style>
  :root {{
    --bg: #0b1220;
    --panel: #ffffff;
    --ink: #1d2333;
    --ink-muted: #5b6477;
    --rule: #e6e8ee;
    --accent: #0052cc;
    --accent-soft: #deebff;
    --warn: #de350b;
    --good: #006644;
    --code-bg: #f4f5f7;
    --table-stripe: #fafbfc;
    --shadow: 0 1px 3px rgba(9,30,66,.08), 0 0 1px rgba(9,30,66,.18);
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    color: var(--ink);
    background: linear-gradient(180deg, #f4f6fb 0%, #eef1f8 100%);
    line-height: 1.55;
    font-size: 14.5px;
  }}
  .layout {{
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
    gap: 24px;
    max-width: 1480px;
    margin: 0 auto;
    padding: 24px;
  }}
  /* TOC */
  aside.toc {{
    position: sticky;
    top: 24px;
    align-self: start;
    max-height: calc(100vh - 48px);
    overflow-y: auto;
    background: var(--panel);
    border-radius: 10px;
    box-shadow: var(--shadow);
    padding: 18px 16px;
    font-size: 13px;
  }}
  aside.toc h3 {{
    margin: 0 0 6px; font-size: 11px; letter-spacing: .12em; color: var(--ink-muted); text-transform: uppercase;
  }}
  aside.toc .meta {{ color: var(--ink-muted); font-size: 11.5px; margin-bottom: 12px; }}
  aside.toc ul {{ list-style: none; padding-left: 0; margin: 0; }}
  aside.toc li.nav-doc {{ margin: 4px 0; }}
  aside.toc li.nav-doc > a {{ font-weight: 600; color: var(--ink); text-decoration: none; }}
  aside.toc li.nav-doc > a:hover {{ color: var(--accent); }}
  aside.toc .nav-sub {{ padding-left: 14px; margin: 4px 0 8px; border-left: 2px solid var(--rule); }}
  aside.toc .nav-sub li {{ margin: 2px 0; }}
  aside.toc .nav-sub a {{ color: var(--ink-muted); text-decoration: none; font-weight: 400; font-size: 12.5px; }}
  aside.toc .nav-sub a:hover {{ color: var(--accent); }}
  /* Main */
  main.body {{
    min-width: 0;
  }}
  section.doc {{
    background: var(--panel);
    border-radius: 12px;
    box-shadow: var(--shadow);
    padding: 28px 36px;
    margin-bottom: 24px;
  }}
  section.doc + section.doc {{ }}
  h1, h2, h3, h4, h5, h6 {{ color: var(--ink); margin-top: 1.4em; line-height: 1.25; scroll-margin-top: 24px; }}
  h1 {{ font-size: 24px; margin-top: 0; padding-bottom: 12px; border-bottom: 2px solid var(--accent-soft); }}
  h2 {{ font-size: 18px; padding-top: 8px; border-top: 1px solid var(--rule); }}
  h3 {{ font-size: 15.5px; color: var(--accent); }}
  h4 {{ font-size: 14px; }}
  p {{ margin: 10px 0; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  blockquote {{
    margin: 14px 0;
    padding: 12px 16px;
    border-left: 4px solid var(--accent);
    background: var(--accent-soft);
    border-radius: 4px;
    color: #233861;
  }}
  blockquote em {{ color: #233861; }}
  code {{
    font-family: SFMono-Regular, Menlo, Consolas, monospace;
    background: var(--code-bg);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.9em;
  }}
  pre {{
    background: #1d2333;
    color: #e6e8ee;
    padding: 14px 16px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 12.5px;
    line-height: 1.5;
  }}
  pre code {{ background: none; color: inherit; padding: 0; font-size: inherit; }}
  hr {{ border: none; border-top: 1px solid var(--rule); margin: 24px 0; }}
  ul, ol {{ padding-left: 22px; }}
  li {{ margin: 4px 0; }}
  .table-wrap {{ overflow-x: auto; margin: 12px 0; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13.5px;
  }}
  th {{
    text-align: left;
    background: #f4f6fb;
    color: var(--ink);
    border-bottom: 2px solid var(--rule);
    padding: 8px 10px;
    font-weight: 600;
    white-space: nowrap;
  }}
  td {{
    padding: 7px 10px;
    border-bottom: 1px solid var(--rule);
    vertical-align: top;
  }}
  tbody tr:nth-child(even) {{ background: var(--table-stripe); }}
  tbody tr:hover {{ background: #f1f6ff; }}
  /* Banner */
  .banner {{
    background: linear-gradient(135deg, #0052cc 0%, #0747a6 100%);
    color: white;
    padding: 24px 36px;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
  }}
  .banner h1 {{ color: white; margin: 0; border: none; padding: 0; font-size: 22px; }}
  .banner p {{ margin: 8px 0 0; opacity: .9; font-size: 14px; }}
  .pill {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11.5px;
    font-weight: 600;
    background: white;
    color: var(--accent);
    margin-right: 6px;
  }}
  /* responsive */
  @media (max-width: 980px) {{
    .layout {{ grid-template-columns: 1fr; }}
    aside.toc {{ position: static; max-height: none; }}
  }}
  /* "Print"-friendly */
  @media print {{
    aside.toc {{ display: none; }}
    .layout {{ display: block; padding: 0; }}
    section.doc {{ box-shadow: none; page-break-after: always; padding: 12px 0; }}
    .banner {{ background: none; color: black; }}
    .banner h1 {{ color: black; }}
  }}
</style>
</head>
<body>
  <div class="layout">
    <aside class="toc">
      <h3>Contents</h3>
      <p class="meta">Built {timestamp}<br>v3 integrated · verified 2026-05-15</p>
      <ul>{nav}</ul>
    </aside>
    <main class="body">
      <div class="banner">
        <h1>Enterprise Demand → Core Engineering Mapping</h1>
        <p>
          <span class="pill">v3 integrated</span>
          <span class="pill">verified 2026-05-15</span>
          Single-source-of-truth for the enterprise (ENT) → CoreEng pillar mapping, written in the role of the MUSTWIN TPM. All ticket priorities &amp; assignees verified live against <code>hello.atlassian.net</code>.
        </p>
      </div>
      {body}
    </main>
  </div>
</body>
</html>
"""

if __name__ == "__main__":
    main()
