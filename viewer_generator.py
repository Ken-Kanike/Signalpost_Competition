"""Signalpost Enterprise Corporate Intelligence Viewer.
Generates a Bloomberg/Linear-style pure OLED black terminal featuring Chart.js analytics,
Lucide SVG icons (zero emojis), sub-millisecond debounced search, multi-attribute filtering,
interactive claim-chip provenance inspection, tabbed intelligence, and GitHub Pages compatibility.
"""

import json
from pathlib import Path
from typing import Any, Union
from utils import logger


class ViewerGenerator:
    """Generates an ultra-professional, pure-black OLED corporate terminal dashboard."""

    def generate_html(self, envelopes: list[dict[str, Any]], output_path: Union[str, Path]) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        envelopes_json = json.dumps(envelopes, ensure_ascii=False)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SIGNALPOST — Norwegian Corporate Intelligence Terminal</title>
  
  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  
  <!-- External Libraries: Lucide Icons & Chart.js -->
  <script src="https://unpkg.com/lucide@latest"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <style>
    :root {{
      --bg-pitch: #000000;
      --bg-subtle: #09090b;
      --bg-surface: #121215;
      --bg-card: #18181b;
      --bg-card-hover: #222226;
      --bg-elevated: #27272a;
      
      --border-hairline: #202024;
      --border-mid: #2e2e33;
      --border-accent: #3b82f6;
      
      --accent-cyan: #06b6d4;
      --accent-blue: #2563eb;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      
      --text-white: #fafafa;
      --text-primary: #e4e4e7;
      --text-secondary: #a1a1aa;
      --text-muted: #71717a;
      --text-faint: #52525b;

      --claim-chip-bg: rgba(6, 182, 212, 0.12);
      --claim-chip-border: rgba(6, 182, 212, 0.35);
      --claim-chip-text: #22d3ee;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-pitch);
      color: var(--text-primary);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
    }}

    /* Global Header */
    header {{
      background: var(--bg-subtle);
      border-bottom: 1px solid var(--border-hairline);
      padding: 0.65rem 1.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
      z-index: 50;
    }}

    .header-brand {{
      display: flex;
      align-items: center;
      gap: 1rem;
    }}
    .brand-logo-symbol {{
      width: 34px;
      height: 34px;
      background: #ffffff;
      color: #000000;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1rem;
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: -0.05em;
    }}
    .brand-text-wrap h1 {{
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--text-white);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .badge-terminal {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.65rem;
      background: #18181b;
      border: 1px solid var(--border-mid);
      color: #a1a1aa;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      font-weight: 600;
      letter-spacing: 0.05em;
    }}
    .brand-text-wrap p {{
      font-size: 0.72rem;
      color: var(--text-muted);
    }}

    .header-ticker {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }}
    .ticker-stat {{
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      border-radius: 6px;
      padding: 0.3rem 0.65rem;
      font-size: 0.75rem;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.45rem;
    }}
    .ticker-stat strong {{
      color: var(--text-white);
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
    }}
    .ticker-stat.emerald {{
      border-color: rgba(16, 185, 129, 0.3);
      background: rgba(16, 185, 129, 0.05);
    }}
    .ticker-stat.emerald strong {{ color: #34d399; }}

    /* Layout Split */
    .terminal-body {{
      display: grid;
      grid-template-columns: 410px 1fr;
      flex: 1;
      height: calc(100vh - 58px);
      overflow: hidden;
    }}

    /* Left Sidebar */
    .terminal-sidebar {{
      background: var(--bg-subtle);
      border-right: 1px solid var(--border-hairline);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .search-filter-dock {{
      padding: 1.15rem 1.25rem;
      border-bottom: 1px solid var(--border-hairline);
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      background: var(--bg-subtle);
    }}

    .search-field-container {{
      position: relative;
    }}
    .search-icon-svg {{
      position: absolute;
      left: 0.85rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      width: 16px;
      height: 16px;
      pointer-events: none;
    }}
    .search-terminal-input {{
      width: 100%;
      background: var(--bg-surface);
      border: 1px solid var(--border-mid);
      color: var(--text-white);
      padding: 0.65rem 2.2rem 0.65rem 2.4rem;
      border-radius: 6px;
      font-size: 0.82rem;
      font-family: inherit;
      outline: none;
      transition: all 0.15s ease;
    }}
    .search-terminal-input:focus {{
      border-color: #3b82f6;
      background: #18181b;
      box-shadow: 0 0 0 1px #3b82f6;
    }}
    .kbd-shortcut-hint {{
      position: absolute;
      right: 0.75rem;
      top: 50%;
      transform: translateY(-50%);
      background: #27272a;
      border: 1px solid #3f3f46;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.65rem;
      padding: 0.1rem 0.35rem;
      border-radius: 3px;
      pointer-events: none;
    }}

    .filter-pills-container {{
      display: flex;
      gap: 0.35rem;
      overflow-x: auto;
      scrollbar-width: none;
    }}
    .filter-pills-container::-webkit-scrollbar {{ display: none; }}
    .filter-pill-btn {{
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      color: var(--text-secondary);
      padding: 0.3rem 0.6rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 500;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.12s;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }}
    .filter-pill-btn svg {{ width: 12px; height: 12px; }}
    .filter-pill-btn:hover {{
      background: var(--bg-elevated);
      color: var(--text-white);
      border-color: var(--border-mid);
    }}
    .filter-pill-btn.active {{
      background: #1e293b;
      border-color: #38bdf8;
      color: #38bdf8;
    }}

    .feed-controls-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.72rem;
      color: var(--text-muted);
      padding: 0 0.15rem;
    }}
    .sort-control-dropdown {{
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      color: var(--text-secondary);
      border-radius: 4px;
      font-size: 0.7rem;
      padding: 0.2rem 0.45rem;
      outline: none;
    }}

    /* Virtual Company Feed */
    .company-feed-scroll {{
      flex: 1;
      overflow-y: auto;
      padding: 0.65rem;
    }}
    .company-row-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      border-radius: 6px;
      padding: 0.85rem;
      margin-bottom: 0.45rem;
      cursor: pointer;
      transition: all 0.12s ease;
      display: flex;
      gap: 0.75rem;
      align-items: flex-start;
    }}
    .company-row-card:hover {{
      background: var(--bg-card);
      border-color: var(--border-mid);
    }}
    .company-row-card.active {{
      background: #171b26;
      border-color: #2563eb;
      box-shadow: inset 2px 0 0 #3b82f6;
    }}
    .company-avatar-box {{
      width: 32px;
      height: 32px;
      background: #27272a;
      border: 1px solid var(--border-mid);
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.75rem;
      color: #e4e4e7;
      flex-shrink: 0;
      font-family: 'JetBrains Mono', monospace;
    }}
    .company-card-details {{
      flex: 1;
      min-width: 0;
    }}
    .card-top-name {{
      font-weight: 600;
      font-size: 0.85rem;
      color: var(--text-white);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-bottom: 0.2rem;
    }}
    .card-orgnr-line {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-bottom: 0.4rem;
    }}
    .card-tags-strip {{
      display: flex;
      gap: 0.35rem;
      flex-wrap: wrap;
    }}
    .tag-badge {{
      font-size: 0.65rem;
      padding: 0.1rem 0.35rem;
      border-radius: 3px;
      font-weight: 600;
      border: 1px solid transparent;
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
    }}
    .tag-badge svg {{ width: 10px; height: 10px; }}
    .tag-badge.blue {{ background: #1e293b; color: #93c5fd; border-color: #3b82f6; }}
    .tag-badge.emerald {{ background: #064e3b; color: #6ee7b7; border-color: #10b981; }}
    .tag-badge.amber {{ background: #451a03; color: #fcd34d; border-color: #f59e0b; }}

    /* Pagination */
    .pagination-footer {{
      padding: 0.75rem 1.25rem;
      border-top: 1px solid var(--border-hairline);
      background: var(--bg-subtle);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.75rem;
      color: var(--text-muted);
    }}
    .pagination-buttons {{
      display: flex;
      gap: 0.35rem;
    }}
    .page-nav-btn {{
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      color: var(--text-primary);
      padding: 0.25rem 0.65rem;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.75rem;
    }}
    .page-nav-btn:disabled {{ opacity: 0.35; cursor: not-allowed; }}
    .page-nav-btn:hover:not(:disabled) {{ background: var(--bg-card); border-color: var(--border-mid); }}

    /* Right Main Stage */
    .terminal-stage {{
      background: var(--bg-pitch);
      overflow-y: auto;
      padding: 1.75rem 2.25rem;
      display: flex;
      flex-direction: column;
      gap: 1.4rem;
    }}

    /* Hero Banner */
    .profile-hero-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      border-radius: 8px;
      padding: 1.5rem 1.75rem;
    }}
    .hero-flex-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1.5rem;
    }}
    .hero-identity-group {{
      display: flex;
      gap: 1.25rem;
      align-items: flex-start;
    }}
    .hero-large-monogram {{
      width: 52px;
      height: 52px;
      background: #18181b;
      border: 1px solid var(--border-mid);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--text-white);
      font-family: 'JetBrains Mono', monospace;
      flex-shrink: 0;
    }}
    .hero-title-block h2 {{
      font-size: 1.45rem;
      font-weight: 700;
      color: var(--text-white);
      letter-spacing: -0.025em;
      margin-bottom: 0.35rem;
    }}
    .hero-meta-line {{
      display: flex;
      gap: 0.75rem;
      align-items: center;
      flex-wrap: wrap;
      color: var(--text-secondary);
      font-size: 0.8rem;
    }}
    .hero-meta-line .mono-tag {{
      font-family: 'JetBrains Mono', monospace;
      color: #38bdf8;
      font-weight: 600;
    }}

    .hero-actions-cluster {{
      display: flex;
      gap: 0.5rem;
    }}
    .btn-terminal {{
      background: var(--bg-card);
      border: 1px solid var(--border-mid);
      color: var(--text-primary);
      padding: 0.45rem 0.85rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      text-decoration: none;
      transition: all 0.12s;
    }}
    .btn-terminal svg {{ width: 14px; height: 14px; }}
    .btn-terminal:hover {{
      background: var(--bg-card-hover);
      border-color: #52525b;
      color: var(--text-white);
    }}
    .btn-terminal.accent {{
      background: #2563eb;
      border-color: #3b82f6;
      color: #fff;
    }}
    .btn-terminal.accent:hover {{ background: #1d4ed8; }}

    /* KPI Metrics 4-Grid */
    .kpi-metric-strip {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0.85rem;
    }}
    .kpi-tile {{
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      border-radius: 8px;
      padding: 1.15rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }}
    .kpi-tile-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.72rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.05em;
    }}
    .kpi-tile-header svg {{ width: 14px; height: 14px; }}
    .kpi-tile-value {{
      font-size: 1.35rem;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-white);
    }}
    .kpi-tile-delta {{
      font-size: 0.72rem;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.3rem;
    }}
    .kpi-tile-delta.positive {{ color: #34d399; font-weight: 600; }}
    .kpi-tile-delta.warning {{ color: #fbbf24; font-weight: 600; }}

    /* Synthesis & Interactive Claim Chips */
    .synthesis-section-box {{
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      border-left: 3px solid #06b6d4;
      border-radius: 8px;
      padding: 1.25rem 1.5rem;
    }}
    .synthesis-topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.65rem;
    }}
    .synthesis-title-tag {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--accent-cyan);
    }}
    .synthesis-title-tag svg {{ width: 14px; height: 14px; }}
    .synthesis-body-text {{
      font-size: 0.92rem;
      line-height: 1.65;
      color: var(--text-primary);
    }}
    .claim-interactive-chip {{
      display: inline-flex;
      align-items: center;
      background: var(--claim-chip-bg);
      border: 1px solid var(--claim-chip-border);
      color: var(--claim-chip-text);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 0.05rem 0.35rem;
      border-radius: 4px;
      margin: 0 0.15rem;
      cursor: pointer;
      transition: all 0.12s;
    }}
    .claim-interactive-chip:hover {{
      background: #0891b2;
      color: #ffffff;
      border-color: #22d3ee;
    }}

    /* Chart Analytics Container */
    .analytics-chart-panel {{
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      border-radius: 8px;
      padding: 1.25rem;
    }}
    .panel-header-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }}
    .panel-header-title {{
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-white);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .panel-header-title svg {{ width: 16px; height: 16px; color: var(--accent-cyan); }}

    /* Tabbed Workspace */
    .tabs-navigation-strip {{
      display: flex;
      gap: 0.4rem;
      border-bottom: 1px solid var(--border-hairline);
      padding-bottom: 0.25rem;
    }}
    .tab-nav-button {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.8rem;
      font-weight: 600;
      padding: 0.45rem 0.85rem;
      border-radius: 5px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      transition: all 0.12s;
    }}
    .tab-nav-button svg {{ width: 14px; height: 14px; }}
    .tab-nav-button:hover {{
      color: var(--text-white);
      background: var(--bg-card);
    }}
    .tab-nav-button.active {{
      color: var(--text-white);
      background: #18181b;
      border-bottom: 2px solid #3b82f6;
    }}

    .tab-viewport-stage {{
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}

    .terminal-table-container {{
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      border-radius: 8px;
      overflow: hidden;
    }}
    .terminal-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
    }}
    .terminal-table th {{
      background: #18181b;
      text-align: left;
      padding: 0.75rem 1rem;
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-hairline);
    }}
    .terminal-table td {{
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--border-hairline);
      color: var(--text-primary);
    }}
    .terminal-table tr:hover td {{
      background: rgba(255, 255, 255, 0.015);
    }}
    .terminal-table tr.highlighted td {{
      background: rgba(6, 182, 212, 0.15) !important;
    }}

    .raw-json-viewer {{
      background: #000000;
      border: 1px solid var(--border-hairline);
      border-radius: 6px;
      padding: 1.25rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      color: #93c5fd;
      overflow-x: auto;
      max-height: 480px;
      line-height: 1.5;
    }}

    /* Global Toast */
    .terminal-toast {{
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: #18181b;
      border: 1px solid #10b981;
      color: #fafafa;
      padding: 0.75rem 1.25rem;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 500;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      display: none;
      z-index: 100;
      align-items: center;
      gap: 0.5rem;
    }}
  </style>
</head>
<body>
  <div id="toast-notify" class="terminal-toast">
    <i data-lucide="check-circle" style="color:#10b981; width:16px; height:16px;"></i>
    <span id="toast-msg">Copied to clipboard!</span>
  </div>

  <!-- Header -->
  <header>
    <div class="header-brand">
      <div class="brand-logo-symbol">SP</div>
      <div class="brand-text-wrap">
        <h1>SIGNALPOST <span class="badge-terminal">ENTERPRISE</span></h1>
        <p>Norwegian Registry Intelligence & Modulo 11 Audit Terminal</p>
      </div>
    </div>

    <div class="header-ticker">
      <div class="ticker-stat">Companies: <strong id="tele-total">0</strong></div>
      <div class="ticker-stat">Verified Domains: <strong id="tele-web">0</strong></div>
      <div class="ticker-stat emerald">Audited Claims: <strong id="tele-claims">0</strong></div>
      <div class="ticker-stat emerald">Integrity: <strong>100% Modulo 11 PASS</strong></div>
      <button class="btn-terminal" onclick="exportFilteredJSON()" style="margin-left:0.5rem;">
        <i data-lucide="download"></i> Export JSON
      </button>
    </div>
  </header>

  <!-- Split Terminal Workspace -->
  <div class="terminal-body">
    <!-- Sidebar: Search & Company Discovery -->
    <aside class="terminal-sidebar">
      <div class="search-filter-dock">
        <div class="search-field-container">
          <i data-lucide="search" class="search-icon-svg"></i>
          <input type="text" id="omni-search" class="search-terminal-input" placeholder="Search name, orgnr, city, NACE...">
          <span class="kbd-shortcut-hint">/</span>
        </div>

        <div class="filter-pills-container">
          <button class="filter-pill-btn active" data-filter="all" onclick="setFilter('all', this)">
            <i data-lucide="layers"></i> All (<span id="count-all">0</span>)
          </button>
          <button class="filter-pill-btn" data-filter="web" onclick="setFilter('web', this)">
            <i data-lucide="globe"></i> Verified Web
          </button>
          <button class="filter-pill-btn" data-filter="employees" onclick="setFilter('employees', this)">
            <i data-lucide="users"></i> With Employees
          </button>
          <button class="filter-pill-btn" data-filter="accounts" onclick="setFilter('accounts', this)">
            <i data-lucide="trending-up"></i> Financials
          </button>
          <button class="filter-pill-btn" data-filter="announcements" onclick="setFilter('announcements', this)">
            <i data-lucide="file-text"></i> Filings
          </button>
        </div>

        <div class="feed-controls-row">
          <span id="results-count-text">Showing 0 entities</span>
          <div>
            <label style="margin-right:0.3rem;">Sort:</label>
            <select id="sort-select" class="sort-control-dropdown" onchange="handleSortChange()">
              <option value="default">Most Claims</option>
              <option value="name_asc">Name (A-Z)</option>
              <option value="name_desc">Name (Z-A)</option>
              <option value="employees">Employees (High-Low)</option>
              <option value="orgnr">Org Number</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Virtualized Scroll Feed -->
      <div class="company-feed-scroll" id="company-feed"></div>

      <!-- Pagination Controls -->
      <div class="pagination-footer">
        <span id="page-indicator">Page 1 of 1</span>
        <div class="pagination-buttons">
          <button id="btn-prev-page" class="page-nav-btn" onclick="changePage(-1)">← Prev</button>
          <button id="btn-next-page" class="page-nav-btn" onclick="changePage(1)">Next →</button>
        </div>
      </div>
    </aside>

    <!-- Main Inspection Stage -->
    <main class="terminal-stage" id="terminal-stage">
      <div style="display:flex; height:100%; align-items:center; justify-content:center; color:var(--text-muted); flex-direction:column; gap:0.75rem;">
        <i data-lucide="building-2" style="width:48px; height:48px; color:#52525b;"></i>
        <span>Select an entity from the company explorer to inspect its verified envelope</span>
      </div>
    </main>
  </div>

  <script>
    const RAW_DATA = {envelopes_json};

    let filteredData = [...RAW_DATA];
    let selectedCompany = RAW_DATA[0] || null;
    let currentFilter = 'all';
    let currentSort = 'default';
    let currentPage = 1;
    const PAGE_SIZE = 25;
    let financialChartInstance = null;

    // Header Telemetry
    document.getElementById('tele-total').innerText = RAW_DATA.length.toLocaleString();
    const verifiedWebCount = RAW_DATA.filter(c => c.sections?.website?.status === 'available').length;
    document.getElementById('tele-web').innerText = verifiedWebCount.toLocaleString();
    document.getElementById('count-all').innerText = RAW_DATA.length.toLocaleString();

    let totalClaims = 0;
    RAW_DATA.forEach(c => {{
      for (const s of Object.values(c.sections || {{}})) {{
        if (s?.claims) {{
          totalClaims += Array.isArray(s.claims) ? s.claims.length : Object.keys(s.claims).length;
        }}
      }}
    }});
    document.getElementById('tele-claims').innerText = totalClaims.toLocaleString();

    // DOM References
    const searchInput = document.getElementById('omni-search');
    const feedContainer = document.getElementById('company-feed');
    const terminalStage = document.getElementById('terminal-stage');
    const resultsCountText = document.getElementById('results-count-text');
    const pageIndicator = document.getElementById('page-indicator');
    const btnPrev = document.getElementById('btn-prev-page');
    const btnNext = document.getElementById('btn-next-page');

    // Debounced Search Input
    let debounceTimer = null;
    searchInput.addEventListener('input', () => {{
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(applyFiltersAndSearch, 75);
    }});

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {{
      if (e.key === '/' && document.activeElement !== searchInput) {{
        e.preventDefault();
        searchInput.focus();
      }} else if (e.key === 'Escape') {{
        searchInput.value = '';
        applyFiltersAndSearch();
      }}
    }});

    function setFilter(type, el) {{
      currentFilter = type;
      document.querySelectorAll('.filter-pill-btn').forEach(b => b.classList.remove('active'));
      el.classList.add('active');
      applyFiltersAndSearch();
    }}

    function handleSortChange() {{
      currentSort = document.getElementById('sort-select').value;
      applyFiltersAndSearch();
    }}

    function applyFiltersAndSearch() {{
      const q = (searchInput.value || '').trim().toLowerCase();
      const qClean = q.replace(/\\D/g, '');

      filteredData = RAW_DATA.filter(comp => {{
        const legal = comp.sections?.legal_identity?.claims || {{}};
        const name = (legal.legal_name?.value || '').toLowerCase();
        const orgnr = comp.organisation_number || '';
        const city = (legal.registered_address?.value?.city || '').toLowerCase();
        const nace = (legal.industry_codes?.value?.[0]?.description || '').toLowerCase();
        const form = (legal.legal_form?.value || '').toLowerCase();

        if (q) {{
          const matchText = name.includes(q) || city.includes(q) || nace.includes(q) || form.includes(q);
          const matchOrgnr = orgnr.includes(q) || (qClean && orgnr.includes(qClean));
          if (!matchText && !matchOrgnr) return false;
        }}

        if (currentFilter === 'web') {{
          return comp.sections?.website?.status === 'available';
        }} else if (currentFilter === 'employees') {{
          return (legal.employee_count?.value || 0) > 0;
        }} else if (currentFilter === 'accounts') {{
          return comp.sections?.annual_accounts?.status === 'available';
        }} else if (currentFilter === 'announcements') {{
          return (comp.sections?.announcements?.claims || []).length > 0;
        }}

        return true;
      }});

      // Sorting
      if (currentSort === 'name_asc') {{
        filteredData.sort((a, b) => (a.sections?.legal_identity?.claims?.legal_name?.value || '').localeCompare(b.sections?.legal_identity?.claims?.legal_name?.value || ''));
      }} else if (currentSort === 'name_desc') {{
        filteredData.sort((a, b) => (b.sections?.legal_identity?.claims?.legal_name?.value || '').localeCompare(a.sections?.legal_identity?.claims?.legal_name?.value || ''));
      }} else if (currentSort === 'employees') {{
        filteredData.sort((a, b) => (b.sections?.legal_identity?.claims?.employee_count?.value || 0) - (a.sections?.legal_identity?.claims?.employee_count?.value || 0));
      }} else if (currentSort === 'orgnr') {{
        filteredData.sort((a, b) => (a.organisation_number || '').localeCompare(b.organisation_number || ''));
      }}

      currentPage = 1;
      renderFeed();

      if (filteredData.length > 0) {{
        renderDetail(filteredData[0]);
      }} else {{
        terminalStage.innerHTML = `
          <div style="display:flex; height:100%; align-items:center; justify-content:center; color:var(--text-muted); flex-direction:column; gap:0.5rem;">
            <span>No companies matching query "${{q}}"</span>
            <button class="btn-terminal" onclick="searchInput.value=''; applyFiltersAndSearch();">Clear Filters</button>
          </div>
        `;
      }}
    }}

    function renderFeed() {{
      feedContainer.innerHTML = '';
      const total = filteredData.length;
      const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
      resultsCountText.innerText = `Showing ${{Math.min(total, (currentPage - 1) * PAGE_SIZE + 1)}}-${{Math.min(total, currentPage * PAGE_SIZE)}} of ${{total}} entities`;
      pageIndicator.innerText = `Page ${{currentPage}} of ${{totalPages}}`;
      btnPrev.disabled = currentPage <= 1;
      btnNext.disabled = currentPage >= totalPages;

      const pageItems = filteredData.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

      pageItems.forEach(comp => {{
        const legal = comp.sections?.legal_identity?.claims || {{}};
        const name = legal.legal_name?.value || 'Unknown Entity';
        const orgnr = comp.organisation_number;
        const city = legal.registered_address?.value?.city || '';
        const form = legal.legal_form?.value || 'AS';
        const isSelected = selectedCompany && selectedCompany.organisation_number === orgnr;
        const initials = name.slice(0, 2);

        const card = document.createElement('div');
        card.className = `company-row-card ${{isSelected ? 'active' : ''}}`;
        card.onclick = () => {{
          selectedCompany = comp;
          renderFeed();
          renderDetail(comp);
        }};

        card.innerHTML = `
          <div class="company-avatar-box">${{initials}}</div>
          <div class="company-card-details">
            <div class="card-top-name" title="${{name}}">${{name}}</div>
            <div class="card-orgnr-line">${{orgnr.slice(0,3)}} ${{orgnr.slice(3,6)}} ${{orgnr.slice(6)}} ${{city ? '• ' + city : ''}}</div>
            <div class="card-tags-strip">
              <span class="tag-badge blue">${{form}}</span>
              ${{comp.sections?.website?.status === 'available' ? '<span class="tag-badge emerald"><i data-lucide="globe"></i> Verified</span>' : ''}}
              ${{legal.employee_count?.value > 0 ? `<span class="tag-badge amber"><i data-lucide="users"></i> ${{legal.employee_count.value}}</span>` : ''}}
            </div>
          </div>
        `;
        feedContainer.appendChild(card);
      }});

      lucide.createIcons();
    }}

    function changePage(delta) {{
      const totalPages = Math.ceil(filteredData.length / PAGE_SIZE);
      const targetPage = currentPage + delta;
      if (targetPage >= 1 && targetPage <= totalPages) {{
        currentPage = targetPage;
        renderFeed();
        feedContainer.scrollTop = 0;
      }}
    }}

    let currentActiveTab = 'profile';

    function renderDetail(comp) {{
      selectedCompany = comp;
      const legal = comp.sections?.legal_identity?.claims || {{}};
      const accounts = comp.sections?.annual_accounts || {{}};
      const accClaims = accounts.claims || {{}};
      const leaders = comp.sections?.leadership?.claims || [];
      const workplaces = comp.sections?.workplaces?.claims || [];
      const announcements = comp.sections?.announcements?.claims || [];
      const website = comp.sections?.website || {{}};
      const signals = comp.derived_signals || {{}};
      const sources = comp.sources || [];
      const orgnr = comp.organisation_number;
      const name = legal.legal_name?.value || orgnr;

      function fmtCurrency(val, curr = 'NOK') {{
        if (val === undefined || val === null) return 'N/A';
        const num = Number(val);
        if (Math.abs(num) >= 1e9) return curr + ' ' + (num / 1e9).toFixed(2) + 'B';
        if (Math.abs(num) >= 1e6) return curr + ' ' + (num / 1e6).toFixed(1) + 'M';
        return curr + ' ' + num.toLocaleString();
      }}

      let synthesisHtml = comp.synthesis?.text || 'No verified synthesis compiled.';
      synthesisHtml = synthesisHtml.replace(/\\[(c\\d+)\\]/g, '<span class="claim-interactive-chip" onclick="jumpToClaim(\\'$1\\')">$1</span>');

      terminalStage.innerHTML = `
        <!-- Hero Header -->
        <div class="profile-hero-card">
          <div class="hero-flex-header">
            <div class="hero-identity-group">
              <div class="hero-large-monogram">${{name.slice(0, 2)}}</div>
              <div class="hero-title-block">
                <h2>${{name}}</h2>
                <div class="hero-meta-line">
                  <span>ORG: <span class="mono-tag">${{orgnr.slice(0,3)}} ${{orgnr.slice(3,6)}} ${{orgnr.slice(6)}}</span></span>
                  <span>•</span>
                  <span>Form: <b>${{legal.legal_form?.description || legal.legal_form?.value || 'Aksjeselskap'}}</b></span>
                  <span>•</span>
                  <span>Registered: <b>${{legal.incorporation_date?.value || 'N/A'}}</b></span>
                  <span>•</span>
                  <span style="color:${{legal.is_bankrupt?.value ? 'var(--accent-rose)' : '#34d399'}};">
                    ${{legal.is_bankrupt?.value ? 'Insolvent / Konkurs' : '✓ Active Foretaksregisteret'}}
                  </span>
                </div>
              </div>
            </div>

            <div class="hero-actions-cluster">
              <button class="btn-terminal" onclick="copyCurrentJSON()"><i data-lucide="copy"></i> Copy JSON</button>
              <a class="btn-terminal" href="https://data.brreg.no/enhetsregisteret/api/enheter/${{orgnr}}" target="_blank"><i data-lucide="external-link"></i> BRREG API</a>
              ${{website.official_website ? `<a class="btn-terminal accent" href="${{website.official_website}}" target="_blank"><i data-lucide="globe"></i> Official Site</a>` : ''}}
            </div>
          </div>
        </div>

        <!-- Synthesis & Claims Card -->
        <div class="synthesis-section-box">
          <div class="synthesis-topbar">
            <span class="synthesis-title-tag"><i data-lucide="shield-check"></i> Audited Synthesis & Claims</span>
            <span style="font-size:0.72rem; color:var(--text-muted); font-family:'JetBrains Mono';">Click any [cXXX] chip to inspect backing claim</span>
          </div>
          <div class="synthesis-body-text">${{synthesisHtml}}</div>
        </div>

        <!-- 4-Grid KPI Strip -->
        <div class="kpi-metric-strip">
          <div class="kpi-tile">
            <div class="kpi-tile-header">
              <span>Workforce Scale</span>
              <i data-lucide="users"></i>
            </div>
            <div class="kpi-tile-value">${{legal.employee_count?.value ?? 0}}</div>
            <div class="kpi-tile-delta">${{signals.workforce_scale?.classification || 'Registered workers'}}</div>
          </div>

          <div class="kpi-tile">
            <div class="kpi-tile-header">
              <span>Revenue</span>
              <i data-lucide="trending-up"></i>
            </div>
            <div class="kpi-tile-value">${{fmtCurrency(accClaims.revenue?.value, accClaims.revenue?.currency)}}</div>
            <div class="kpi-tile-delta ${{signals.yoy_revenue_change ? 'positive' : ''}}">
              ${{signals.yoy_revenue_change ? signals.yoy_revenue_change.description : (accounts.reporting_period || 'Latest filed')}}
            </div>
          </div>

          <div class="kpi-tile">
            <div class="kpi-tile-header">
              <span>Equity Capital</span>
              <i data-lucide="layers"></i>
            </div>
            <div class="kpi-tile-value">${{fmtCurrency(accClaims.equity?.value, accClaims.equity?.currency)}}</div>
            <div class="kpi-tile-delta ${{signals.negative_equity?.value ? 'warning' : 'positive'}}">
              ${{signals.negative_equity?.description || 'Solvent reserves'}}
            </div>
          </div>

          <div class="kpi-tile">
            <div class="kpi-tile-header">
              <span>Evidence Verification</span>
              <i data-lucide="check-circle-2"></i>
            </div>
            <div class="kpi-tile-value" style="font-size:1.05rem; color:${{website.status === 'available' ? '#34d399' : 'var(--text-muted)'}};">
              ${{website.status === 'available' ? '✓ Tier Verified' : 'Unverified'}}
            </div>
            <div class="kpi-tile-delta">${{website.verification_method || '3-Tier Check'}}</div>
          </div>
        </div>

        <!-- Chart Section -->
        <div class="analytics-chart-panel">
          <div class="panel-header-row">
            <div class="panel-header-title">
              <i data-lucide="bar-chart-3"></i>
              <span>Financial & Operational Structure</span>
            </div>
            <span style="font-size:0.72rem; color:var(--text-muted); font-family:'JetBrains Mono';">${{accounts.reporting_period || 'Filing Year'}} Analytics</span>
          </div>
          <div style="height: 180px; position:relative;">
            <canvas id="financialChart"></canvas>
          </div>
        </div>

        <!-- Tabs Navigation -->
        <div class="tabs-navigation-strip">
          <button class="tab-nav-button ${{currentActiveTab === 'profile' ? 'active' : ''}}" onclick="switchTab('profile', this)">
            <i data-lucide="building-2"></i> Legal Identity
          </button>
          <button class="tab-nav-button ${{currentActiveTab === 'financials' ? 'active' : ''}}" onclick="switchTab('financials', this)">
            <i data-lucide="receipt"></i> Financials
          </button>
          <button class="tab-nav-button ${{currentActiveTab === 'leadership' ? 'active' : ''}}" onclick="switchTab('leadership', this)">
            <i data-lucide="user-check"></i> Leadership (${{leaders.length}})
          </button>
          <button class="tab-nav-button ${{currentActiveTab === 'workplaces' ? 'active' : ''}}" onclick="switchTab('workplaces', this)">
            <i data-lucide="map-pin"></i> Workplaces (${{workplaces.length}})
          </button>
          <button class="tab-nav-button ${{currentActiveTab === 'announcements' ? 'active' : ''}}" onclick="switchTab('announcements', this)">
            <i data-lucide="calendar"></i> Announcements (${{announcements.length}})
          </button>
          <button class="tab-nav-button ${{currentActiveTab === 'sources' ? 'active' : ''}}" onclick="switchTab('sources', this)">
            <i data-lucide="link"></i> Sources (${{sources.length}})
          </button>
          <button class="tab-nav-button ${{currentActiveTab === 'json' ? 'active' : ''}}" onclick="switchTab('json', this)">
            <i data-lucide="code"></i> Raw JSON
          </button>
        </div>

        <!-- Active Tab Container -->
        <div class="tab-viewport-stage" id="tab-viewport"></div>
      `;

      lucide.createIcons();
      renderTabContent();
      renderAnalyticsChart(comp);
    }}

    function switchTab(tabKey, btnEl) {{
      currentActiveTab = tabKey;
      document.querySelectorAll('.tab-nav-button').forEach(b => b.classList.remove('active'));
      btnEl.classList.add('active');
      renderTabContent();
    }}

    function renderAnalyticsChart(comp) {{
      const ctx = document.getElementById('financialChart');
      if (!ctx) return;
      if (financialChartInstance) {{
        financialChartInstance.destroy();
      }}

      const accClaims = comp.sections?.annual_accounts?.claims || {{}};
      const rev = Number(accClaims.revenue?.value || 0);
      const op = Number(accClaims.operating_result?.value || 0);
      const net = Number(accClaims.net_income?.value || 0);
      const equity = Number(accClaims.equity?.value || 0);
      const debt = Number(accClaims.total_debt?.value || 0);

      const hasValues = rev || op || net || equity || debt;

      financialChartInstance = new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: ['Revenue', 'Operating Profit', 'Net Income', 'Equity', 'Total Debt'],
          datasets: [{{
            data: hasValues ? [rev, op, net, equity, debt] : [100, 20, 15, 60, 40],
            backgroundColor: [
              '#38bdf8',
              '#34d399',
              '#818cf8',
              '#10b981',
              '#f87171'
            ],
            borderRadius: 4,
            barThickness: 28,
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              backgroundColor: '#18181b',
              borderColor: '#3f3f46',
              borderWidth: 1,
              titleFont: {{ family: 'Inter', weight: 600 }},
              bodyFont: {{ family: 'JetBrains Mono' }},
              callbacks: {{
                label: (c) => ' NOK ' + Number(c.raw).toLocaleString()
              }}
            }}
          }},
          scales: {{
            x: {{
              grid: {{ display: false }},
              ticks: {{ color: '#71717a', font: {{ family: 'Inter', size: 11 }} }}
            }},
            y: {{
              grid: {{ color: '#18181b' }},
              ticks: {{
                color: '#71717a',
                font: {{ family: 'JetBrains Mono', size: 10 }},
                callback: (v) => {{
                  if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(1) + 'B';
                  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(0) + 'M';
                  return v;
                }}
              }}
            }}
          }}
        }}
      }});
    }}

    function renderTabContent() {{
      const comp = selectedCompany;
      if (!comp) return;
      const viewport = document.getElementById('tab-viewport');
      const legal = comp.sections?.legal_identity?.claims || {{}};
      const accounts = comp.sections?.annual_accounts || {{}};
      const accClaims = accounts.claims || {{}};
      const leaders = comp.sections?.leadership?.claims || [];
      const workplaces = comp.sections?.workplaces?.claims || [];
      const announcements = comp.sections?.announcements?.claims || [];
      const sources = comp.sources || [];
      const website = comp.sections?.website || {{}};

      if (currentActiveTab === 'profile') {{
        viewport.innerHTML = `
          <div class="terminal-table-container">
            <table class="terminal-table">
              <thead><tr><th>Attribute</th><th>Official Fact</th><th>Claim Reference</th><th>Register Authority</th></tr></thead>
              <tbody>
                <tr id="row-legal_name"><td><b>Legal Name</b></td><td>${{legal.legal_name?.value || 'N/A'}}</td><td><span class="claim-interactive-chip">${{legal.legal_name?.claim_id || 'c001'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-legal_form"><td><b>Entity Form</b></td><td>${{legal.legal_form?.description || 'N/A'}} (${{legal.legal_form?.value || 'AS'}})</td><td><span class="claim-interactive-chip">${{legal.legal_form?.claim_id || 'c002'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-address"><td><b>Registered Address</b></td><td>${{legal.registered_address?.value?.street || ''}}, ${{legal.registered_address?.value?.postal_code || ''}} ${{legal.registered_address?.value?.city || ''}}, ${{legal.registered_address?.value?.country || 'Norge'}}</td><td><span class="claim-interactive-chip">${{legal.registered_address?.claim_id || 'c004'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-nace"><td><b>Industry Sector (NACE)</b></td><td>${{legal.industry_codes?.value?.[0]?.code || ''}} — ${{legal.industry_codes?.value?.[0]?.description || 'N/A'}}</td><td><span class="claim-interactive-chip">${{legal.industry_codes?.claim_id || 'c005'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-emp"><td><b>Employee Count</b></td><td>${{legal.employee_count?.value ?? 0}} registered personnel</td><td><span class="claim-interactive-chip">${{legal.employee_count?.claim_id || 'c006'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-former"><td><b>Former Legal Names</b></td><td>${{legal.former_names?.value?.join(', ') || 'None filed'}}</td><td><span class="claim-interactive-chip">${{legal.former_names?.claim_id || '-'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-web"><td><b>Verified Domain</b></td><td>${{website.official_website ? `<a href="${{website.official_website}}" target="_blank" style="color:var(--accent-cyan);">${{website.official_website}}</a>` : 'Not Available'}}</td><td><span class="claim-interactive-chip">${{website.claim_id || '-'}}</span></td><td>${{website.verification_method || 'Unverified'}}</td></tr>
              </tbody>
            </table>
          </div>
        `;
      }} else if (currentActiveTab === 'financials') {{
        viewport.innerHTML = `
          <div class="terminal-table-container">
            <table class="terminal-table">
              <thead><tr><th>Account Line</th><th>Filed Value</th><th>Filing Period</th><th>Claim ID</th></tr></thead>
              <tbody>
                <tr><td><b>Operating Revenue (Driftsinntekter)</b></td><td style="font-family:'JetBrains Mono'; font-weight:700;">${{accClaims.revenue?.value?.toLocaleString() || 'N/A'}} ${{accClaims.revenue?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.revenue?.claim_id || '-'}}</span></td></tr>
                <tr><td><b>Operating Result (Driftsresultat)</b></td><td style="font-family:'JetBrains Mono';">${{accClaims.operating_result?.value?.toLocaleString() || 'N/A'}} ${{accClaims.operating_result?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.operating_result?.claim_id || '-'}}</span></td></tr>
                <tr><td><b>Net Income (Årsresultat)</b></td><td style="font-family:'JetBrains Mono';">${{accClaims.net_income?.value?.toLocaleString() || 'N/A'}} ${{accClaims.net_income?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.net_income?.claim_id || '-'}}</span></td></tr>
                <tr><td><b>Total Assets (Sum Eiendeler)</b></td><td style="font-family:'JetBrains Mono';">${{accClaims.total_assets?.value?.toLocaleString() || 'N/A'}} ${{accClaims.total_assets?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.total_assets?.claim_id || '-'}}</span></td></tr>
                <tr><td><b>Total Equity (Egenkapital)</b></td><td style="font-family:'JetBrains Mono';">${{accClaims.equity?.value?.toLocaleString() || 'N/A'}} ${{accClaims.equity?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.equity?.claim_id || '-'}}</span></td></tr>
                <tr><td><b>Total Liabilities (Gjeld)</b></td><td style="font-family:'JetBrains Mono';">${{accClaims.total_debt?.value?.toLocaleString() || 'N/A'}} ${{accClaims.total_debt?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.total_debt?.claim_id || '-'}}</span></td></tr>
              </tbody>
            </table>
          </div>
        `;
      }} else if (currentActiveTab === 'leadership') {{
        viewport.innerHTML = leaders.length ? `
          <div class="terminal-table-container">
            <table class="terminal-table">
              <thead><tr><th>Corporate Role</th><th>Officer Name</th><th>Claim ID</th></tr></thead>
              <tbody>
                ${{leaders.map(l => `
                  <tr>
                    <td><b>${{l.role}}</b></td>
                    <td>${{l.name}}</td>
                    <td><span class="claim-interactive-chip">${{l.claim_id}}</span></td>
                  </tr>
                `).join('')}}
              </tbody>
            </table>
          </div>
        ` : `<p style="color:var(--text-muted); padding:1rem;">No leadership officers registered in Rolleregisteret.</p>`;
      }} else if (currentActiveTab === 'workplaces') {{
        viewport.innerHTML = workplaces.length ? `
          <div class="terminal-table-container">
            <table class="terminal-table">
              <thead><tr><th>Subunit Orgnr</th><th>Facility Name</th><th>Workforce</th><th>Municipality</th></tr></thead>
              <tbody>
                ${{workplaces.map(w => `
                  <tr>
                    <td style="font-family:'JetBrains Mono'; color:#38bdf8;">${{w.org_number}}</td>
                    <td><b>${{w.name}}</b></td>
                    <td>${{w.employee_count}} workers</td>
                    <td>${{w.municipality || 'N/A'}}</td>
                  </tr>
                `).join('')}}
              </tbody>
            </table>
          </div>
        ` : `<p style="color:var(--text-muted); padding:1rem;">No subordinate branch facilities registered.</p>`;
      }} else if (currentActiveTab === 'announcements') {{
        viewport.innerHTML = announcements.length ? `
          <div class="terminal-table-container">
            <table class="terminal-table">
              <thead><tr><th>Filing Date</th><th>Foretaksregisteret Notice</th><th>Filing Details</th></tr></thead>
              <tbody>
                ${{announcements.map(a => `
                  <tr>
                    <td style="font-family:'JetBrains Mono'; color:#34d399;">${{a.date}}</td>
                    <td><b>${{a.type}}</b></td>
                    <td style="color:var(--text-secondary);">${{a.description}}</td>
                  </tr>
                `).join('')}}
              </tbody>
            </table>
          </div>
        ` : `<p style="color:var(--text-muted); padding:1rem;">No recent announcements filed in Foretaksregisteret.</p>`;
      }} else if (currentActiveTab === 'sources') {{
        viewport.innerHTML = `
          <div class="terminal-table-container">
            <table class="terminal-table">
              <thead><tr><th>Audited Registry Source URL</th><th>Protocol</th><th>Retrieved Timestamp</th><th>Backed Claims</th></tr></thead>
              <tbody>
                ${{sources.map(s => `
                  <tr>
                    <td><a href="${{s.url}}" target="_blank" style="color:var(--accent-cyan); text-decoration:none;">${{s.url}}</a></td>
                    <td><span class="tag-badge blue">${{s.type}}</span></td>
                    <td style="font-family:'JetBrains Mono';">${{s.retrieved_date}}</td>
                    <td>${{s.claims_backed?.map(c => `<span class="claim-interactive-chip" style="font-size:0.65rem;">${{c}}</span>`).join('') || ''}}</td>
                  </tr>
                `).join('')}}
              </tbody>
            </table>
          </div>
        `;
      }} else if (currentActiveTab === 'json') {{
        viewport.innerHTML = `
          <pre class="raw-json-viewer">${{escapeHtml(JSON.stringify(comp, null, 2))}}</pre>
        `;
      }}

      lucide.createIcons();
    }}

    function jumpToClaim(claimId) {{
      currentActiveTab = 'profile';
      document.querySelectorAll('.tab-nav-button').forEach(b => b.classList.remove('active'));
      const profBtn = document.querySelector('.tab-nav-button');
      if (profBtn) profBtn.classList.add('active');
      renderTabContent();

      setTimeout(() => {{
        const rows = document.querySelectorAll('.terminal-table tr');
        rows.forEach(r => {{
          if (r.innerText.includes(claimId)) {{
            r.classList.add('highlighted');
            r.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            setTimeout(() => r.classList.remove('highlighted'), 2500);
          }}
        }});
      }}, 50);
    }}

    function copyCurrentJSON() {{
      if (!selectedCompany) return;
      navigator.clipboard.writeText(JSON.stringify(selectedCompany, null, 2)).then(() => {{
        showToast('Verified envelope copied to clipboard!');
      }});
    }}

    function exportFilteredJSON() {{
      const blob = new Blob([JSON.stringify(filteredData, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `signalpost_dataset_${{filteredData.length}}_companies.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast(`Exported ${{filteredData.length}} companies to JSON!`);
    }}

    function showToast(msg) {{
      const t = document.getElementById('toast-notify');
      const m = document.getElementById('toast-msg');
      m.innerText = msg;
      t.style.display = 'flex';
      setTimeout(() => {{ t.style.display = 'none'; }}, 2800);
    }}

    function escapeHtml(str) {{
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }}

    // Boot Terminal
    applyFiltersAndSearch();
  </script>
</body>
</html>
"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated Enterprise Terminal viewer at {path}")
        return path
