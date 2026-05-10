#!/usr/bin/env python
"""Build a single comprehensive HTML report from all latest enterprise request markdown docs."""

import markdown
import os, re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent

# Ordered document list — (filename, display title, emoji)
DOCS = [
    ("00_SUMMARY_README.md",                                      "Executive Summary",                         "📋"),
    ("corrected_master_mapping.md",                               "✅ Corrected Master Mapping (v2)",          "🗺️"),
    ("corrected_priority_matrix.md",                              "✅ Priority Matrix (v2 Corrected)",         "🚦"),
    ("corrected_batch1_details.md",                               "ENT-3291→3737 Full Details",                "📄"),
    ("corrected_batch2_details.md",                               "ENT-3738→3863 Full Details",                "📄"),
    ("corrected_legacy_details.md",                               "Legacy ENT Tickets Full Details",           "📄"),
    ("01_security_compliance_identity_requests.md",               "Security, Compliance & Identity",           "🔐"),
    ("02_scale_integration_rovo_ai_requests.md",                  "Scale, Integration & Rovo/AI",              "📈"),
    ("02_critical_analysis.md",                                   "Critical Analysis",                         "🔍"),
    ("03_governance_admin_data_requests.md",                      "Governance, Admin & Data",                  "🏛️"),
    ("04_confluence_voc_enterprise_context.md",                   "Confluence VOC & Enterprise Context",       "📚"),
    ("07_NEW_PROJECT_CANDIDATES.md",                              "New Project Candidates",                    "🆕"),
    ("LEGACY_TICKETS_SUMMARY.md",                                 "Legacy Tickets Summary",                    "🗂️"),
    ("RESEARCH_COMPLETE.md",                                      "Research Methodology",                      "🔬"),
]

MD_EXTENSIONS = ["tables", "toc", "fenced_code", "attr_list", "nl2br"]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Latest Enterprise Requests — CoreEng Mapping | FY26</title>
  <style>
    :root {{
      --bg: #0d1117;
      --surface: #161b22;
      --surface2: #1e2430;
      --border: #2a3040;
      --accent: #58a6ff;
      --accent2: #bc8cff;
      --green: #3fb950;
      --yellow: #d29922;
      --red: #f85149;
      --orange: #e3b341;
      --teal: #39c5cf;
      --text: #c9d1d9;
      --text-bright: #f0f6fc;
      --muted: #6e7681;
      --code-bg: #0d1117;
      --sidebar-w: 300px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      min-height: 100vh;
      font-size: 14px;
      line-height: 1.65;
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
      scrollbar-width: thin;
      scrollbar-color: var(--border) transparent;
    }}
    #sidebar-header {{
      padding: 20px 16px 16px;
      border-bottom: 1px solid var(--border);
      background: var(--surface2);
      position: sticky; top: 0; z-index: 10;
    }}
    #sidebar-header .logo {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .1em;
      color: var(--accent);
      margin-bottom: 6px;
    }}
    #sidebar-header h2 {{
      font-size: 13px;
      font-weight: 700;
      color: var(--text-bright);
      line-height: 1.4;
    }}
    #sidebar-header .meta {{
      font-size: 11px;
      color: var(--muted);
      margin-top: 6px;
    }}
    #sidebar nav {{ padding: 8px 0 40px; }}
    .nav-section-label {{
      padding: 14px 16px 4px;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .12em;
      color: var(--muted);
    }}
    #sidebar nav a.section-link {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      font-size: 12.5px;
      font-weight: 500;
      color: var(--text);
      text-decoration: none;
      border-left: 2px solid transparent;
      transition: all .12s;
    }}
    #sidebar nav a.section-link .emoji {{ font-size: 14px; flex-shrink: 0; }}
    #sidebar nav a.section-link:hover {{ background: var(--surface2); color: var(--text-bright); }}
    #sidebar nav a.section-link.active {{ background: rgba(88,166,255,.08); border-left-color: var(--accent); color: var(--accent); font-weight: 600; }}
    #sidebar nav a.toc-link {{
      display: block;
      padding: 3px 16px 3px 36px;
      font-size: 11.5px;
      color: var(--muted);
      text-decoration: none;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    #sidebar nav a.toc-link:hover {{ color: var(--text); }}

    /* ── STATS BAR ── */
    #stats-bar {{
      display: flex; gap: 12px; flex-wrap: wrap;
      margin-bottom: 28px;
    }}
    .stat-card {{
      flex: 1; min-width: 140px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px 18px;
    }}
    .stat-card .num {{ font-size: 28px; font-weight: 800; color: var(--text-bright); line-height: 1; }}
    .stat-card .label {{ font-size: 11px; color: var(--muted); margin-top: 4px; text-transform: uppercase; letter-spacing: .06em; }}
    .stat-card.green .num {{ color: var(--green); }}
    .stat-card.yellow .num {{ color: var(--yellow); }}
    .stat-card.red .num {{ color: var(--red); }}
    .stat-card.blue .num {{ color: var(--accent); }}
    .stat-card.purple .num {{ color: var(--accent2); }}

    /* ── MAIN CONTENT ── */
    #main {{
      margin-left: var(--sidebar-w);
      flex: 1;
      padding: 40px 52px 80px;
      max-width: 1280px;
      min-width: 0;
    }}

    /* ── TOP BANNER ── */
    #banner {{
      background: linear-gradient(135deg, #161b22 0%, #1e2430 50%, #1a1f2e 100%);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 28px 32px;
      margin-bottom: 28px;
      position: relative;
      overflow: hidden;
    }}
    #banner::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: linear-gradient(90deg, var(--accent), var(--accent2), var(--teal));
    }}
    #banner h1 {{ font-size: 22px; font-weight: 800; color: var(--text-bright); margin-bottom: 8px; }}
    #banner .meta {{ font-size: 12px; color: var(--muted); display: flex; gap: 20px; flex-wrap: wrap; }}
    #banner .meta span {{ display: flex; align-items: center; gap: 5px; }}

    /* ── SECTIONS ── */
    .doc-section {{ margin-bottom: 48px; scroll-margin-top: 20px; }}
    .section-header {{
      display: flex; align-items: center; gap: 10px;
      margin-bottom: 16px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
    }}
    .section-emoji {{ font-size: 20px; }}
    .section-title {{ font-size: 17px; font-weight: 700; color: var(--text-bright); }}
    .section-filename {{ font-size: 11px; color: var(--muted); margin-left: auto; font-family: monospace; }}
    .section-divider {{ border: none; border-top: 1px solid var(--border); margin: 40px 0; }}

    /* ── MARKDOWN BODY ── */
    .md-body h1 {{ font-size: 20px; font-weight: 800; color: var(--text-bright); margin: 28px 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}
    .md-body h2 {{ font-size: 16px; font-weight: 700; color: var(--accent); margin: 24px 0 10px; }}
    .md-body h3 {{ font-size: 14px; font-weight: 700; color: #a8b5c8; margin: 18px 0 8px; }}
    .md-body h4 {{ font-size: 12px; font-weight: 700; color: var(--muted); margin: 14px 0 6px; text-transform: uppercase; letter-spacing: .06em; }}
    .md-body p {{ margin: 8px 0; }}
    .md-body ul, .md-body ol {{ margin: 8px 0 8px 20px; }}
    .md-body li {{ margin: 3px 0; }}
    .md-body strong {{ color: var(--text-bright); font-weight: 700; }}
    .md-body em {{ color: var(--orange); font-style: italic; }}
    .md-body a {{ color: var(--accent); text-decoration: none; }}
    .md-body a:hover {{ text-decoration: underline; }}
    .md-body code {{
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 3px;
      padding: 1px 5px;
      font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
      font-size: 12px;
      color: #79c0ff;
    }}
    .md-body pre {{
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px 18px;
      overflow-x: auto;
      margin: 12px 0;
    }}
    .md-body pre code {{ border: none; background: none; padding: 0; font-size: 12px; color: #a5f3fc; }}
    .md-body blockquote {{
      border-left: 3px solid var(--accent2);
      padding: 8px 16px;
      background: rgba(188,140,255,.06);
      border-radius: 0 6px 6px 0;
      margin: 12px 0;
      color: var(--muted);
    }}
    .md-body hr {{ border: none; border-top: 1px solid var(--border); margin: 24px 0; }}

    /* ── TABLES ── */
    .md-body table {{
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0;
      font-size: 12.5px;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--border);
    }}
    .md-body thead tr {{ background: var(--surface2); }}
    .md-body th {{
      padding: 9px 12px;
      text-align: left;
      font-weight: 700;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .05em;
      color: var(--accent);
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }}
    .md-body td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }}
    .md-body tr:last-child td {{ border-bottom: none; }}
    .md-body tbody tr:hover {{ background: rgba(255,255,255,.02); }}

    /* ── STATUS PILL AUTO-DETECTION ── */
    /* We use JS to colorize cells containing status words */

    /* ── SEARCH BAR ── */
    #search-wrap {{
      margin-bottom: 20px;
    }}
    #search-input {{
      width: 100%;
      padding: 10px 16px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text-bright);
      font-size: 13px;
      outline: none;
    }}
    #search-input:focus {{ border-color: var(--accent); }}
    #search-input::placeholder {{ color: var(--muted); }}

    /* ── BACK TO TOP ── */
    #top-btn {{
      position: fixed;
      bottom: 24px; right: 24px;
      background: var(--accent);
      color: var(--bg);
      border: none;
      border-radius: 50%;
      width: 38px; height: 38px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 4px 14px rgba(88,166,255,.35);
      transition: opacity .2s, transform .2s;
      z-index: 200;
    }}
    #top-btn:hover {{ opacity: .85; transform: translateY(-2px); }}

    @media (max-width: 860px) {{
      #sidebar {{ display: none; }}
      #main {{ margin-left: 0; padding: 20px 16px; }}
    }}
  </style>
</head>
<body>

<!-- SIDEBAR -->
<div id="sidebar">
  <div id="sidebar-header">
    <div class="logo">Atlassian CoreEng</div>
    <h2>Latest Enterprise Requests</h2>
    <div class="meta">📅 {date} &nbsp;|&nbsp; 152 tickets analyzed</div>
  </div>
  <nav id="sidebar-nav">
    <div class="nav-section-label">Documents</div>
{sidebar_links}
  </nav>
</div>

<!-- MAIN -->
<div id="main">

  <!-- BANNER -->
  <div id="banner">
    <h1>🏢 Latest Enterprise Requests → CoreEng Mapping</h1>
    <div class="meta">
      <span>📅 {date}</span>
      <span>🗂️ 152 ENT tickets · Last 90 days</span>
      <span>🔍 4 deep research agents · 6 search strategies</span>
      <span>🎯 Maps to 10 CoreEng pillars</span>
    </div>
  </div>

  <!-- STATS -->
  <div id="stats-bar">
    <div class="stat-card blue"><div class="num">152</div><div class="label">Total ENT Tickets (90d)</div></div>
    <div class="stat-card red"><div class="num">84%</div><div class="label">Pending Review (unaddressed)</div></div>
    <div class="stat-card purple"><div class="num">59%</div><div class="label">Need New Projects</div></div>
    <div class="stat-card yellow"><div class="num">5</div><div class="label">New Project Candidates</div></div>
    <div class="stat-card green"><div class="num">41%</div><div class="label">Map to Existing Projects</div></div>
  </div>

  <!-- SEARCH -->
  <div id="search-wrap">
    <input id="search-input" type="text" placeholder="🔍 Search tickets, summaries, pillars..." />
  </div>

{sections}

</div>

<button id="top-btn" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

<script>
// Sidebar active link on scroll
const sectionLinks = document.querySelectorAll('#sidebar-nav a.section-link');
const docSections = document.querySelectorAll('.doc-section');
const observer = new IntersectionObserver(entries => {{
  entries.forEach(e => {{
    if (e.isIntersecting) {{
      sectionLinks.forEach(l => l.classList.remove('active'));
      const active = document.querySelector('#sidebar-nav a[href="#' + e.target.id + '"]');
      if (active) active.classList.add('active');
    }}
  }});
}}, {{threshold: 0.1, rootMargin: '-10% 0px -80% 0px'}});
docSections.forEach(s => observer.observe(s));

// Search filter
const searchInput = document.getElementById('search-input');
searchInput.addEventListener('input', function() {{
  const q = this.value.toLowerCase().trim();
  if (!q) {{
    document.querySelectorAll('.doc-section').forEach(s => s.style.display = '');
    document.querySelectorAll('.md-body tr').forEach(r => r.style.display = '');
    return;
  }}
  document.querySelectorAll('.doc-section').forEach(section => {{
    const text = section.textContent.toLowerCase();
    section.style.display = text.includes(q) ? '' : 'none';
  }});
  document.querySelectorAll('.md-body tbody tr').forEach(row => {{
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}});

// Auto-colorize status cells in tables
document.querySelectorAll('.md-body td').forEach(td => {{
  const t = td.textContent.trim();
  if (t.includes('✅') || t === 'Shipped' || t === 'Done') td.style.color = '#3fb950';
  else if (t.includes('🔴') || t === 'Off Track' || t.includes('Paused')) td.style.color = '#f85149';
  else if (t.includes('🟡') || t === 'At Risk' || t.includes('Pending')) td.style.color = '#d29922';
  else if (t.includes('🟢') || t === 'On Track') td.style.color = '#3fb950';
  else if (t.startsWith('P0')) {{ td.style.color = '#f85149'; td.style.fontWeight = '700'; }}
  else if (t.startsWith('P1')) {{ td.style.color = '#e3b341'; td.style.fontWeight = '600'; }}
  else if (t.startsWith('P2')) td.style.color = '#58a6ff';
  else if (t.startsWith('ENT-')) {{ td.style.fontFamily = 'monospace'; td.style.fontWeight = '600'; td.style.color = '#79c0ff'; }}
  else if (t.includes('⚠️') || t.includes('NEW')) td.style.color = '#e3b341';
  else if (t.includes('NEW PROJECT')) td.style.color = '#bc8cff';
}});
</script>
</body>
</html>
"""


def slugify(text):
    return re.sub(r'[^a-z0-9-]', '-', text.lower().strip()).strip('-')


def extract_h2_headings(html_body):
    headings = re.findall(r'<h2[^>]*>(.*?)</h2>', html_body, re.DOTALL)
    return [re.sub(r'<[^>]+>', '', h).strip() for h in headings if re.sub(r'<[^>]+>', '', h).strip()]


def build():
    sections_html = ""
    sidebar_links = ""
    built = 0

    for filename, section_title, emoji in DOCS:
        fpath = BASE_DIR / filename
        if not fpath.exists():
            print(f"  SKIP (missing): {filename}")
            continue

        md_text = fpath.read_text(encoding="utf-8")
        md_instance = markdown.Markdown(extensions=MD_EXTENSIONS)
        body_html = md_instance.convert(md_text)

        section_id = slugify(section_title)
        sub_headings = extract_h2_headings(body_html)

        sub_links = ""
        for sh in sub_headings[:10]:
            sh_id = slugify(sh)
            sub_links += f'    <a class="toc-link" href="#{sh_id}">{sh[:60]}</a>\n'

        sidebar_links += f'    <a class="section-link" href="#{section_id}"><span class="emoji">{emoji}</span>{section_title}</a>\n'
        sidebar_links += sub_links

        sections_html += f"""
<div class="doc-section" id="{section_id}">
  <div class="section-header">
    <span class="section-emoji">{emoji}</span>
    <span class="section-title">{section_title}</span>
    <span class="section-filename">{filename}</span>
  </div>
  <div class="md-body">
{body_html}
  </div>
</div>
<hr class="section-divider" />
"""
        size_kb = len(md_text) // 1024
        print(f"  ✅ {filename:<55} ({size_kb:>3} KB)")
        built += 1

    out_html = HTML_TEMPLATE.format(
        date=datetime.now().strftime("%B %d, %Y"),
        sidebar_links=sidebar_links,
        sections=sections_html,
    )

    out_path = BASE_DIR / "index.html"
    out_path.write_text(out_html, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"\n✅ HTML built ({built} docs) → {out_path}  ({size_kb} KB)")
    return str(out_path)


if __name__ == "__main__":
    print(f"Building Latest Enterprise Requests HTML...\n")
    build()
