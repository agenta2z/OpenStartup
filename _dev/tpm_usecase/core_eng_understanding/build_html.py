#!/usr/bin/env python
"""Build a single comprehensive HTML report from all CoreEng markdown docs."""

import markdown
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent

DOCS = [
    ("00_index.md",                                               "Overview & Index"),
    ("01_org_structure_leadership.md",                            "Org Structure & Leadership"),
    ("02_identity_iam_pillar.md",                                 "Identity & IAM Pillar"),
    ("03_platform_pillars_brie_tsp_tdp_encryption_alp_sandbox.md","Platform Pillars: BRIE · TSP · TDP · Encryption · ALP · Sandbox"),
    ("04_compliance_scale_finops_engexcellence_new_ent.md",       "Compliance · Scale · FinOps · Eng Excellence · New ENT Requests"),
    ("05_enterprise_request_map.md",                              "Enterprise Request Map → CoreEng"),
]

MD_EXTENSIONS = [
    "tables",
    "toc",
    "fenced_code",
    "attr_list",
    "nl2br",
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CoreEng Deep Understanding — FY26</title>
  <style>
    :root {{
      --bg: #0f1117;
      --surface: #1a1d27;
      --surface2: #22263a;
      --border: #2e3347;
      --accent: #4f8ef7;
      --accent2: #7c6af7;
      --green: #34c77b;
      --yellow: #f5c542;
      --red: #f56565;
      --orange: #f5994a;
      --text: #e2e8f0;
      --muted: #8892a4;
      --code-bg: #181b28;
      --sidebar-w: 280px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      min-height: 100vh;
      font-size: 15px;
      line-height: 1.7;
    }}

    /* ── SIDEBAR ── */
    #sidebar {{
      width: var(--sidebar-w);
      min-width: var(--sidebar-w);
      background: var(--surface);
      border-right: 1px solid var(--border);
      position: fixed;
      top: 0; left: 0; bottom: 0;
      overflow-y: auto;
      z-index: 100;
      padding: 0 0 40px;
    }}
    #sidebar-header {{
      padding: 20px 18px 14px;
      border-bottom: 1px solid var(--border);
      background: var(--surface2);
    }}
    #sidebar-header h2 {{
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--accent);
    }}
    #sidebar-header p {{
      font-size: 11px;
      color: var(--muted);
      margin-top: 4px;
    }}
    #sidebar nav {{ padding: 10px 0; }}
    #sidebar nav a.section-link {{
      display: block;
      padding: 9px 18px;
      font-size: 13px;
      font-weight: 600;
      color: var(--text);
      text-decoration: none;
      border-left: 3px solid transparent;
      transition: all .15s;
    }}
    #sidebar nav a.section-link:hover,
    #sidebar nav a.section-link.active {{
      background: var(--surface2);
      border-left-color: var(--accent);
      color: var(--accent);
    }}
    #sidebar nav a.toc-link {{
      display: block;
      padding: 4px 18px 4px 28px;
      font-size: 12px;
      color: var(--muted);
      text-decoration: none;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    #sidebar nav a.toc-link:hover {{ color: var(--text); }}

    /* ── MAIN CONTENT ── */
    #main {{
      margin-left: var(--sidebar-w);
      flex: 1;
      padding: 48px 56px 80px;
      max-width: 1200px;
    }}

    /* ── TOP BANNER ── */
    #banner {{
      background: linear-gradient(135deg, #1e2240 0%, #232850 100%);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 32px 36px;
      margin-bottom: 40px;
    }}
    #banner h1 {{
      font-size: 26px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 6px;
    }}
    #banner .meta {{
      font-size: 13px;
      color: var(--muted);
      display: flex; gap: 24px; flex-wrap: wrap;
    }}
    #banner .meta span {{ display: flex; align-items: center; gap: 6px; }}
    .pill {{
      display: inline-block;
      padding: 2px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .pill-green  {{ background: rgba(52,199,123,.15); color: var(--green);  border: 1px solid rgba(52,199,123,.3);  }}
    .pill-yellow {{ background: rgba(245,197,66,.15);  color: var(--yellow); border: 1px solid rgba(245,197,66,.3);  }}
    .pill-red    {{ background: rgba(245,101,101,.15); color: var(--red);    border: 1px solid rgba(245,101,101,.3); }}
    .pill-blue   {{ background: rgba(79,142,247,.15);  color: var(--accent); border: 1px solid rgba(79,142,247,.3);  }}
    .pill-grey   {{ background: rgba(136,146,164,.1);  color: var(--muted);  border: 1px solid rgba(136,146,164,.2); }}

    /* ── SECTIONS ── */
    .doc-section {{
      margin-bottom: 56px;
      scroll-margin-top: 24px;
    }}
    .section-label {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .1em;
      color: var(--accent2);
      margin-bottom: 8px;
    }}
    .section-divider {{
      border: none;
      border-top: 1px solid var(--border);
      margin: 40px 0;
    }}

    /* ── MARKDOWN CONTENT ── */
    .md-body h1 {{
      font-size: 24px; font-weight: 800; color: #fff;
      margin: 36px 0 16px; padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
    }}
    .md-body h2 {{
      font-size: 19px; font-weight: 700; color: var(--accent);
      margin: 32px 0 14px;
    }}
    .md-body h3 {{
      font-size: 15px; font-weight: 700; color: #c9d2e8;
      margin: 24px 0 10px;
    }}
    .md-body h4 {{
      font-size: 13px; font-weight: 700; color: var(--muted);
      margin: 18px 0 8px; text-transform: uppercase; letter-spacing: .06em;
    }}
    .md-body p {{ margin: 10px 0; color: var(--text); }}
    .md-body ul, .md-body ol {{
      margin: 10px 0 10px 22px; color: var(--text);
    }}
    .md-body li {{ margin: 4px 0; }}
    .md-body strong {{ color: #fff; font-weight: 700; }}
    .md-body em {{ color: var(--yellow); font-style: italic; }}
    .md-body a {{ color: var(--accent); text-decoration: none; }}
    .md-body a:hover {{ text-decoration: underline; }}
    .md-body code {{
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 1px 6px;
      font-family: "JetBrains Mono", "Fira Code", monospace;
      font-size: 13px;
      color: #7dd3fc;
    }}
    .md-body pre {{
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 18px 20px;
      overflow-x: auto;
      margin: 14px 0;
    }}
    .md-body pre code {{
      border: none; background: none; padding: 0;
      font-size: 13px; color: #a5f3fc;
    }}
    .md-body blockquote {{
      border-left: 3px solid var(--accent2);
      padding: 10px 18px;
      background: var(--surface2);
      border-radius: 0 8px 8px 0;
      margin: 14px 0;
      color: var(--muted);
    }}
    .md-body hr {{
      border: none; border-top: 1px solid var(--border); margin: 28px 0;
    }}

    /* ── TABLES ── */
    .md-body table {{
      width: 100%;
      border-collapse: collapse;
      margin: 18px 0;
      font-size: 13px;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--border);
    }}
    .md-body thead tr {{
      background: var(--surface2);
    }}
    .md-body th {{
      padding: 10px 14px;
      text-align: left;
      font-weight: 700;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .05em;
      color: var(--accent);
      border-bottom: 1px solid var(--border);
    }}
    .md-body td {{
      padding: 9px 14px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    .md-body tr:last-child td {{ border-bottom: none; }}
    .md-body tbody tr:hover {{ background: var(--surface2); }}

    /* ── EMOJI STATUS INDICATORS ── */
    /* Auto-colorise certain emojis in table cells */

    /* ── SCROLL TO TOP ── */
    #top-btn {{
      position: fixed;
      bottom: 28px; right: 28px;
      background: var(--accent);
      color: #fff;
      border: none;
      border-radius: 50%;
      width: 40px; height: 40px;
      font-size: 18px;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 4px 12px rgba(79,142,247,.4);
      transition: opacity .2s;
    }}
    #top-btn:hover {{ opacity: .85; }}

    /* ── RESPONSIVE ── */
    @media (max-width: 900px) {{
      #sidebar {{ display: none; }}
      #main {{ margin-left: 0; padding: 24px 18px; }}
    }}
  </style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-header">
    <h2>CoreEng Deep Understanding</h2>
    <p>Generated {date}</p>
  </div>
  <nav id="sidebar-nav">
{sidebar_links}
  </nav>
</div>

<div id="main">
  <div id="banner">
    <h1>🏢 Core Engineering — Deep Understanding</h1>
    <div class="meta">
      <span>📅 Generated: {date}</span>
      <span>👤 DRI: Ke Wang (kwang4@atlassian.com)</span>
      <span>🎯 Purpose: Map Enterprise Requests → CoreEng Org &amp; Projects</span>
      <span>📊 Coverage: 34 known ENT tickets + 50 new (last 90d)</span>
    </div>
  </div>

{sections}

</div>

<button id="top-btn" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

<script>
// Highlight active sidebar link on scroll
const links = document.querySelectorAll('#sidebar-nav a.section-link');
const sections = document.querySelectorAll('.doc-section');
const observer = new IntersectionObserver(entries => {{
  entries.forEach(e => {{
    if (e.isIntersecting) {{
      links.forEach(l => l.classList.remove('active'));
      const active = document.querySelector('#sidebar-nav a[href="#' + e.target.id + '"]');
      if (active) active.classList.add('active');
    }}
  }});
}}, {{threshold: 0.15}});
sections.forEach(s => observer.observe(s));
</script>
</body>
</html>
"""


def slugify(text):
    import re
    return re.sub(r'[^a-z0-9-]', '-', text.lower().strip()).strip('-')


def extract_h2_headings(html_body):
    """Extract h2 headings for sidebar ToC sub-links."""
    import re
    headings = re.findall(r'<h2[^>]*>(.*?)</h2>', html_body, re.DOTALL)
    clean = []
    for h in headings:
        # strip inner tags
        text = re.sub(r'<[^>]+>', '', h).strip()
        if text:
            clean.append(text)
    return clean


def build():
    sections_html = ""
    sidebar_links = ""

    for filename, section_title in DOCS:
        fpath = BASE_DIR / filename
        if not fpath.exists():
            print(f"  MISSING: {filename}")
            continue

        md_text = fpath.read_text(encoding="utf-8")
        md_instance = markdown.Markdown(extensions=MD_EXTENSIONS)
        body_html = md_instance.convert(md_text)

        section_id = slugify(section_title)

        # Extract h2 headings for sidebar sub-links
        sub_headings = extract_h2_headings(body_html)
        sub_links = ""
        for sh in sub_headings[:12]:  # max 12 sub-links per section
            sh_id = slugify(sh)
            sub_links += f'    <a class="toc-link" href="#{sh_id}">{sh[:55]}</a>\n'

        sidebar_links += f'    <a class="section-link" href="#{section_id}">{section_title}</a>\n'
        sidebar_links += sub_links

        sections_html += f"""
<div class="doc-section" id="{section_id}">
  <div class="section-label">📄 {filename}</div>
  <div class="md-body">
{body_html}
  </div>
</div>
<hr class="section-divider" />
"""
        print(f"  ✅ {filename} ({len(md_text):,} chars)")

    out_html = HTML_TEMPLATE.format(
        date=datetime.now().strftime("%B %d, %Y"),
        sidebar_links=sidebar_links,
        sections=sections_html,
    )

    out_path = BASE_DIR / "coreng_understanding.html"
    out_path.write_text(out_html, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"\n✅ HTML written → {out_path}  ({size_kb} KB)")
    return str(out_path)


if __name__ == "__main__":
    print("Building CoreEng HTML report...\n")
    build()
