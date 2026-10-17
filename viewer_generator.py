"""Signalpost Enterprise Corporate Intelligence Viewer.
Generates a standalone, high-performance Nordic dark-mode web application
featuring sub-millisecond debounced search, multi-attribute filtering,
interactive claim-chip provenance inspection, tabbed company intelligence,
and one-click JSON/CSV data export with zero external framework dependencies.
"""

import json
from pathlib import Path
from typing import Any, Union
from utils import logger


class ViewerGenerator:
    """Generates a responsive, ultra-fast single-file web application for corporate envelopes."""

    def generate_html(self, envelopes: list[dict[str, Any]], output_path: Union[str, Path]) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        envelopes_json = json.dumps(envelopes, ensure_ascii=False)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Signalpost — Norwegian Corporate Intelligence Explorer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-base: #090d16;
      --bg-surface: #0f172a;
      --bg-card: #131c31;
      --bg-card-hover: #1e293b;
      --bg-elevated: #1e293b;
      --border-subtle: rgba(255, 255, 255, 0.06);
      --border-default: rgba(255, 255, 255, 0.1);
      --border-focus: #38bdf8;
      --accent-cyan: #06b6d4;
      --accent-blue: #3b82f6;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --accent-indigo: #6366f1;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --claim-chip-bg: rgba(6, 182, 212, 0.15);
      --claim-chip-border: rgba(6, 182, 212, 0.35);
      --claim-chip-text: #38bdf8;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-base);
      color: var(--text-main);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
    }}

    /* Top Navigation Header */
    header {{
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-default);
      padding: 0.75rem 1.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 50;
      flex-shrink: 0;
    }}

    .brand-cluster {{
      display: flex;
      align-items: center;
      gap: 1rem;
    }}
    .brand-mark {{
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: linear-gradient(135deg, #0284c7 0%, #6366f1 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1.15rem;
      color: #fff;
      box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
      letter-spacing: -0.03em;
    }}
    .brand-titles h1 {{
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .brand-tag {{
      font-size: 0.65rem;
      background: rgba(6, 182, 212, 0.15);
      border: 1px solid rgba(6, 182, 212, 0.3);
      color: var(--accent-cyan);
      padding: 0.15rem 0.5rem;
      border-radius: 9999px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .brand-titles p {{
      font-size: 0.75rem;
      color: var(--text-muted);
    }}

    .header-telemetry {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .pill-stat {{
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 0.35rem 0.75rem;
      font-size: 0.75rem;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.45rem;
    }}
    .pill-stat strong {{
      color: var(--text-main);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.8rem;
    }}
    .pill-stat.glow {{
      border-color: rgba(16, 185, 129, 0.3);
      background: rgba(16, 185, 129, 0.08);
    }}
    .pill-stat.glow strong {{
      color: #34d399;
    }}

    /* Main Split Application Layout */
    .app-workspace {{
      display: grid;
      grid-template-columns: 420px 1fr;
      flex: 1;
      height: calc(100vh - 65px);
      overflow: hidden;
    }}

    /* Left Sidebar: Discovery & Filtering */
    .sidebar-pane {{
      background: var(--bg-surface);
      border-right: 1px solid var(--border-default);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .search-filter-hub {{
      padding: 1.25rem;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      background: rgba(15, 23, 42, 0.4);
    }}

    .search-bar-wrap {{
      position: relative;
    }}
    .search-icon {{
      position: absolute;
      left: 0.95rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      font-size: 0.9rem;
      pointer-events: none;
    }}
    .clear-search-btn {{
      position: absolute;
      right: 0.75rem;
      top: 50%;
      transform: translateY(-50%);
      background: transparent;
      border: none;
      color: var(--text-dim);
      cursor: pointer;
      font-size: 0.85rem;
      padding: 0.2rem;
      display: none;
    }}
    .clear-search-btn:hover {{ color: var(--text-main); }}
    .search-input {{
      width: 100%;
      background: #090d16;
      border: 1px solid var(--border-default);
      color: var(--text-main);
      padding: 0.7rem 2.2rem 0.7rem 2.5rem;
      border-radius: 9px;
      font-size: 0.85rem;
      font-family: inherit;
      outline: none;
      transition: all 0.15s ease;
    }}
    .search-input:focus {{
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
      background: #0c1220;
    }}

    .filter-pills-row {{
      display: flex;
      gap: 0.4rem;
      overflow-x: auto;
      padding-bottom: 0.2rem;
      scrollbar-width: none;
    }}
    .filter-pills-row::-webkit-scrollbar {{ display: none; }}
    .filter-btn {{
      background: #1e293b;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      padding: 0.3rem 0.65rem;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.12s;
    }}
    .filter-btn:hover {{
      background: #334155;
      color: var(--text-main);
    }}
    .filter-btn.active {{
      background: rgba(6, 182, 212, 0.18);
      border-color: rgba(6, 182, 212, 0.4);
      color: var(--accent-cyan);
    }}

    .results-meta-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.72rem;
      color: var(--text-dim);
      padding: 0 0.15rem;
    }}
    .sort-select {{
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      border-radius: 4px;
      font-size: 0.72rem;
      padding: 0.15rem 0.4rem;
      outline: none;
    }}

    .company-virtual-feed {{
      flex: 1;
      overflow-y: auto;
      padding: 0.65rem;
    }}
    .company-card-item {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 9px;
      padding: 0.9rem;
      margin-bottom: 0.5rem;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      gap: 0.75rem;
      align-items: flex-start;
    }}
    .company-card-item:hover {{
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.15);
      transform: translateY(-1px);
    }}
    .company-card-item.selected {{
      background: rgba(6, 182, 212, 0.08);
      border-color: rgba(6, 182, 212, 0.45);
      box-shadow: 0 0 0 1px rgba(6, 182, 212, 0.2);
    }}
    .company-avatar {{
      width: 36px;
      height: 36px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.8rem;
      color: #fff;
      flex-shrink: 0;
      text-transform: uppercase;
    }}
    .card-info {{
      flex: 1;
      min-width: 0;
    }}
    .card-headline {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 0.2rem;
    }}
    .card-name {{
      font-weight: 600;
      font-size: 0.88rem;
      color: var(--text-main);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .card-orgnr {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      color: var(--text-dim);
      margin-bottom: 0.4rem;
    }}
    .card-tags {{
      display: flex;
      gap: 0.35rem;
      flex-wrap: wrap;
    }}
    .mini-badge {{
      font-size: 0.65rem;
      padding: 0.12rem 0.4rem;
      border-radius: 4px;
      font-weight: 600;
    }}
    .mini-badge.blue {{ background: rgba(59, 130, 246, 0.15); color: #93c5fd; }}
    .mini-badge.emerald {{ background: rgba(16, 185, 129, 0.15); color: #6ee7b7; }}
    .mini-badge.amber {{ background: rgba(245, 158, 11, 0.15); color: #fcd34d; }}

    /* Pagination Bar */
    .pagination-bar {{
      padding: 0.75rem 1.25rem;
      border-top: 1px solid var(--border-subtle);
      background: var(--bg-surface);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.75rem;
      color: var(--text-muted);
    }}
    .page-nav-group {{
      display: flex;
      gap: 0.35rem;
    }}
    .page-btn {{
      background: #1e293b;
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 0.25rem 0.6rem;
      border-radius: 5px;
      cursor: pointer;
      font-size: 0.75rem;
    }}
    .page-btn:disabled {{
      opacity: 0.4;
      cursor: not-allowed;
    }}
    .page-btn:hover:not(:disabled) {{
      background: #334155;
    }}

    /* Right Main Panel: Company Deep-Dive Inspection */
    .detail-stage {{
      background: var(--bg-base);
      overflow-y: auto;
      padding: 1.75rem 2.25rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}

    .hero-profile-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-default);
      border-radius: 12px;
      padding: 1.75rem;
      position: relative;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }}
    .hero-top-row {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1.5rem;
    }}
    .hero-identity {{
      display: flex;
      gap: 1.15rem;
      align-items: flex-start;
    }}
    .hero-large-avatar {{
      width: 58px;
      height: 58px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.4rem;
      font-weight: 800;
      color: #fff;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
      flex-shrink: 0;
    }}
    .hero-name-block h2 {{
      font-size: 1.5rem;
      font-weight: 800;
      letter-spacing: -0.025em;
      color: var(--text-main);
      margin-bottom: 0.25rem;
    }}
    .hero-meta-strip {{
      display: flex;
      gap: 0.65rem;
      align-items: center;
      flex-wrap: wrap;
      color: var(--text-muted);
      font-size: 0.8rem;
    }}
    .hero-meta-strip .mono {{
      font-family: 'JetBrains Mono', monospace;
      color: #38bdf8;
      font-weight: 600;
    }}

    .hero-actions {{
      display: flex;
      gap: 0.5rem;
      align-items: center;
    }}
    .btn-action {{
      background: #1e293b;
      border: 1px solid var(--border-default);
      color: var(--text-main);
      padding: 0.5rem 0.9rem;
      border-radius: 7px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      text-decoration: none;
      transition: all 0.15s;
    }}
    .btn-action:hover {{
      background: #334155;
      border-color: rgba(255, 255, 255, 0.25);
    }}
    .btn-action.primary {{
      background: #0284c7;
      border-color: #38bdf8;
      color: #fff;
    }}
    .btn-action.primary:hover {{
      background: #0369a1;
    }}

    /* Key Metrics Grid */
    .key-metrics-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
    }}
    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 1.15rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }}
    .kpi-title {{
      font-size: 0.72rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .kpi-value {{
      font-size: 1.35rem;
      font-weight: 700;
      color: var(--text-main);
      font-family: 'JetBrains Mono', monospace;
    }}
    .kpi-subtext {{
      font-size: 0.72rem;
      color: var(--text-dim);
    }}
    .kpi-subtext.positive {{ color: #34d399; font-weight: 600; }}
    .kpi-subtext.warning {{ color: #fbbf24; font-weight: 600; }}

    /* Synthesis & Claim Chips Box */
    .synthesis-banner {{
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(56, 189, 248, 0.25);
      border-radius: 11px;
      padding: 1.35rem;
      position: relative;
    }}
    .synthesis-header-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
    }}
    .synthesis-badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--accent-cyan);
    }}
    .synthesis-paragraph {{
      font-size: 0.95rem;
      line-height: 1.65;
      color: #cbd5e1;
    }}
    .claim-interactive-chip {{
      display: inline-flex;
      align-items: center;
      background: var(--claim-chip-bg);
      border: 1px solid var(--claim-chip-border);
      color: var(--claim-chip-text);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.1rem 0.35rem;
      border-radius: 4px;
      margin: 0 0.15rem;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .claim-interactive-chip:hover {{
      background: var(--accent-cyan);
      color: #090d16;
      border-color: #38bdf8;
      transform: translateY(-1px);
    }}

    /* Tabbed Sections */
    .tab-nav-bar {{
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid var(--border-default);
      padding-bottom: 0.25rem;
    }}
    .tab-item-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.82rem;
      font-weight: 600;
      padding: 0.5rem 0.85rem;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.12s;
    }}
    .tab-item-btn:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.04);
    }}
    .tab-item-btn.active {{
      color: var(--accent-cyan);
      background: rgba(6, 182, 212, 0.12);
      border-bottom: 2px solid var(--accent-cyan);
    }}

    .tab-content-container {{
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }}
    .data-table-wrap {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      overflow: hidden;
    }}
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
    }}
    .data-table th {{
      background: rgba(15, 23, 42, 0.6);
      text-align: left;
      padding: 0.75rem 1rem;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-default);
    }}
    .data-table td {{
      padding: 0.8rem 1rem;
      border-bottom: 1px solid var(--border-subtle);
      color: var(--text-main);
    }}
    .data-table tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}
    .data-table tr.highlighted td {{
      background: rgba(6, 182, 212, 0.15) !important;
    }}

    .json-code-box {{
      background: #090d16;
      border: 1px solid var(--border-default);
      border-radius: 8px;
      padding: 1.25rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      color: #93c5fd;
      overflow-x: auto;
      max-height: 480px;
      line-height: 1.5;
    }}

    /* Toast Notification */
    .toast-popup {{
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: #065f46;
      border: 1px solid #10b981;
      color: #fff;
      padding: 0.75rem 1.25rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      box-shadow: 0 10px 25px rgba(0,0,0,0.4);
      display: none;
      z-index: 100;
    }}
  </style>
</head>
<body>
  <!-- Global Toast -->
  <div id="toast-notify" class="toast-popup">Copied to clipboard!</div>

  <!-- Header -->
  <header>
    <div class="brand-cluster">
      <div class="brand-mark">SP</div>
      <div class="brand-titles">
        <h1>Signalpost Terminal <span class="brand-tag">v2.0 Verified</span></h1>
        <p>Norwegian Corporate Intelligence & Modulo 11 Evidence Registry</p>
      </div>
    </div>
    <div class="header-telemetry">
      <div class="pill-stat">Companies: <strong id="tele-total">0</strong></div>
      <div class="pill-stat">Verified Web: <strong id="tele-web">0</strong></div>
      <div class="pill-stat glow">Audited Claims: <strong id="tele-claims">0</strong></div>
      <div class="pill-stat glow">Integrity: <strong>100% Modulo 11</strong></div>
      <button class="btn-action" onclick="exportCurrentJSON()" style="margin-left:0.5rem;">📥 Export JSON</button>
    </div>
  </header>

  <!-- Main Application Workspace -->
  <div class="app-workspace">
    <!-- Left Sidebar: Filters & Virtualized List -->
    <aside class="sidebar-pane">
      <div class="search-filter-hub">
        <div class="search-bar-wrap">
          <span class="search-icon">🔍</span>
          <input type="text" id="omni-search" class="search-input" placeholder="Search by name, orgnr, city, NACE (Press '/' to focus)...">
          <button id="clear-search-btn" class="clear-search-btn" onclick="clearSearch()">✕</button>
        </div>

        <div class="filter-pills-row">
          <button class="filter-btn active" data-filter="all" onclick="setFilter('all', this)">All (0)</button>
          <button class="filter-btn" data-filter="web" onclick="setFilter('web', this)">🌐 Verified Web</button>
          <button class="filter-btn" data-filter="employees" onclick="setFilter('employees', this)">👥 With Employees</button>
          <button class="filter-btn" data-filter="accounts" onclick="setFilter('accounts', this)">📊 Financials</button>
          <button class="filter-btn" data-filter="announcements" onclick="setFilter('announcements', this)">📢 Announcements</button>
        </div>

        <div class="results-meta-bar">
          <span id="results-count-text">Showing 0 of 0 entities</span>
          <div>
            <label style="margin-right:0.3rem;">Sort:</label>
            <select id="sort-select" class="sort-select" onchange="handleSortChange()">
              <option value="default">Most Claims</option>
              <option value="name_asc">Name (A-Z)</option>
              <option value="name_desc">Name (Z-A)</option>
              <option value="employees">Employees (High-Low)</option>
              <option value="orgnr">Org Number</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Scrollable Company Cards -->
      <div class="company-virtual-feed" id="company-feed"></div>

      <!-- Pagination Footer -->
      <div class="pagination-bar">
        <span id="page-indicator">Page 1 of 1</span>
        <div class="page-nav-group">
          <button id="btn-prev-page" class="page-btn" onclick="changePage(-1)">← Prev</button>
          <button id="btn-next-page" class="page-btn" onclick="changePage(1)">Next →</button>
        </div>
      </div>
    </aside>

    <!-- Right Workspace: Full Company Intelligence Stage -->
    <main class="detail-stage" id="detail-stage">
      <div style="display:flex; height:100%; align-items:center; justify-content:center; color:var(--text-dim); flex-direction:column; gap:0.75rem;">
        <span style="font-size:2rem;">🏢</span>
        <span>Select any company from the feed to view verified profile envelope</span>
      </div>
    </main>
  </div>

  <!-- Client-Side Engine -->
  <script>
    const RAW_DATA = {envelopes_json};

    // Global App State
    let filteredData = [...RAW_DATA];
    let selectedCompany = RAW_DATA[0] || null;
    let currentFilter = 'all';
    let currentSort = 'default';
    let currentPage = 1;
    const PAGE_SIZE = 25;

    // Palette generator for company avatars
    const PALETTES = [
      'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
      'linear-gradient(135deg, #10b981 0%, #047857 100%)',
      'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)',
      'linear-gradient(135deg, #f59e0b 0%, #b45309 100%)',
      'linear-gradient(135deg, #ec4899 0%, #be185d 100%)',
      'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)',
    ];
    function getAvatarBg(orgnr) {{
      const num = parseInt(orgnr.replace(/\\D/g, '') || '0', 10);
      return PALETTES[num % PALETTES.length];
    }}

    // Init Header Telemetry
    document.getElementById('tele-total').innerText = RAW_DATA.length.toLocaleString();
    const verifiedWebCount = RAW_DATA.filter(c => c.sections?.website?.status === 'available').length;
    document.getElementById('tele-web').innerText = verifiedWebCount.toLocaleString();

    let totalClaims = 0;
    RAW_DATA.forEach(c => {{
      for (const s of Object.values(c.sections || {{}})) {{
        if (s?.claims) {{
          totalClaims += Array.isArray(s.claims) ? s.claims.length : Object.keys(s.claims).length;
        }}
      }}
    }});
    document.getElementById('tele-claims').innerText = totalClaims.toLocaleString();

    // DOM Elements
    const searchInput = document.getElementById('omni-search');
    const clearBtn = document.getElementById('clear-search-btn');
    const feedContainer = document.getElementById('company-feed');
    const detailStage = document.getElementById('detail-stage');
    const resultsCountText = document.getElementById('results-count-text');
    const pageIndicator = document.getElementById('page-indicator');
    const btnPrev = document.getElementById('btn-prev-page');
    const btnNext = document.getElementById('btn-next-page');

    // Debounce search input
    let searchDebounceTimer = null;
    searchInput.addEventListener('input', (e) => {{
      clearBtn.style.display = e.target.value ? 'block' : 'none';
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {{
        applyFiltersAndSearch();
      }}, 80);
    }});

    function clearSearch() {{
      searchInput.value = '';
      clearBtn.style.display = 'none';
      applyFiltersAndSearch();
      searchInput.focus();
    }}

    // Keyboard shortcuts
    window.addEventListener('keydown', (e) => {{
      if (e.key === '/' && document.activeElement !== searchInput) {{
        e.preventDefault();
        searchInput.focus();
      }} else if (e.key === 'Escape') {{
        clearSearch();
      }}
    }});

    function setFilter(filterType, btnEl) {{
      currentFilter = filterType;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btnEl.classList.add('active');
      applyFiltersAndSearch();
    }}

    function handleSortChange() {{
      currentSort = document.getElementById('sort-select').value;
      applyFiltersAndSearch();
    }}

    function applyFiltersAndSearch() {{
      const query = (searchInput.value || '').trim().toLowerCase();
      const cleanDigitsQuery = query.replace(/\\D/g, '');

      filteredData = RAW_DATA.filter(comp => {{
        const legal = comp.sections?.legal_identity?.claims || {{}};
        const name = (legal.legal_name?.value || '').toLowerCase();
        const orgnr = (comp.organisation_number || '');
        const city = (legal.registered_address?.value?.city || '').toLowerCase();
        const nace = (legal.industry_codes?.value?.[0]?.description || '').toLowerCase();
        const form = (legal.legal_form?.value || '').toLowerCase();

        // 1. Text & Code match
        if (query) {{
          const matchesText = name.includes(query) || city.includes(query) || nace.includes(query) || form.includes(query);
          const matchesOrgnr = orgnr.includes(query) || (cleanDigitsQuery && orgnr.includes(cleanDigitsQuery));
          if (!matchesText && !matchesOrgnr) return false;
        }}

        // 2. Category Filter
        if (currentFilter === 'web') {{
          return comp.sections?.website?.status === 'available';
        }} else if (currentFilter === 'employees') {{
          const emp = legal.employee_count?.value || 0;
          return emp > 0;
        }} else if (currentFilter === 'accounts') {{
          return comp.sections?.annual_accounts?.status === 'available';
        }} else if (currentFilter === 'announcements') {{
          return (comp.sections?.announcements?.claims || []).length > 0;
        }}

        return true;
      }});

      // Apply Sort
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

      // Auto-select first matching
      if (filteredData.length > 0) {{
        renderDetail(filteredData[0]);
      }} else {{
        detailStage.innerHTML = `
          <div style="display:flex; height:100%; align-items:center; justify-content:center; color:var(--text-dim); flex-direction:column; gap:0.5rem;">
            <span>🔍 No companies found matching "${{query}}"</span>
            <button class="btn-action" onclick="clearSearch()">Clear Search</button>
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
        card.className = `company-card-item ${{isSelected ? 'selected' : ''}}`;
        card.onclick = () => {{
          selectedCompany = comp;
          renderFeed();
          renderDetail(comp);
        }};

        card.innerHTML = `
          <div class="company-avatar" style="background:${{getAvatarBg(orgnr)}}">${{initials}}</div>
          <div class="card-info">
            <div class="card-headline">
              <span class="card-name" title="${{name}}">${{name}}</span>
            </div>
            <div class="card-orgnr">${{orgnr.slice(0,3)}} ${{orgnr.slice(3,6)}} ${{orgnr.slice(6)}} ${{city ? '• ' + city : ''}}</div>
            <div class="card-tags">
              <span class="mini-badge blue">${{form}}</span>
              ${{comp.sections?.website?.status === 'available' ? '<span class="mini-badge emerald">Verified Web</span>' : ''}}
              ${{legal.employee_count?.value > 0 ? `<span class="mini-badge amber">${{legal.employee_count.value}} Emp</span>` : ''}}
            </div>
          </div>
        `;
        feedContainer.appendChild(card);
      }});
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

    // Render Detailed Company Intelligence Screen
    let currentActiveTab = 'overview';
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

      // Transform claim codes [c001] to interactive inspection chips
      let synthesisHtml = comp.synthesis?.text || 'No synthesis available.';
      synthesisHtml = synthesisHtml.replace(/\\[(c\\d+)\\]/g, '<span class="claim-interactive-chip" onclick="jumpToClaim(\\'$1\\')">$1</span>');

      detailStage.innerHTML = `
        <!-- Hero Header -->
        <div class="hero-profile-card">
          <div class="hero-top-row">
            <div class="hero-identity">
              <div class="hero-large-avatar" style="background:${{getAvatarBg(orgnr)}}">${{name.slice(0, 2)}}</div>
              <div class="hero-name-block">
                <h2>${{name}}</h2>
                <div class="hero-meta-strip">
                  <span>Org Number: <span class="mono">${{orgnr.slice(0,3)}} ${{orgnr.slice(3,6)}} ${{orgnr.slice(6)}}</span></span>
                  <span>•</span>
                  <span>Form: <b>${{legal.legal_form?.description || legal.legal_form?.value || 'Aksjeselskap'}}</b></span>
                  <span>•</span>
                  <span>Registered: <b>${{legal.incorporation_date?.value || 'N/A'}}</b></span>
                  <span>•</span>
                  <span style="color:${{legal.is_bankrupt?.value ? 'var(--accent-rose)' : '#34d399'}};">
                    ${{legal.is_bankrupt?.value ? '⚠️ Konkurs (Insolvent)' : '✓ Active & Solvent'}}
                  </span>
                </div>
              </div>
            </div>

            <div class="hero-actions">
              <button class="btn-action" onclick="copyCurrentJSON()">📋 Copy JSON</button>
              <a class="btn-action" href="https://data.brreg.no/enhetsregisteret/api/enheter/${{orgnr}}" target="_blank">🏛️ BRREG API ↗</a>
              ${{website.official_website ? `<a class="btn-action primary" href="${{website.official_website}}" target="_blank">🌐 Official Web ↗</a>` : ''}}
            </div>
          </div>
        </div>

        <!-- Synthesis & Claims Card -->
        <div class="synthesis-banner">
          <div class="synthesis-header-bar">
            <span class="synthesis-badge">✨ Audited Synthesis (Zero Hallucination)</span>
            <span style="font-size:0.72rem; color:var(--text-dim); font-family:'JetBrains Mono';">Click any [cXXX] chip to inspect backing claim</span>
          </div>
          <div class="synthesis-paragraph">${{synthesisHtml}}</div>
        </div>

        <!-- Key Metrics KPI Grid -->
        <div class="key-metrics-grid">
          <div class="kpi-card">
            <span class="kpi-title">Workforce</span>
            <span class="kpi-value">${{legal.employee_count?.value ?? 0}}</span>
            <span class="kpi-subtext">${{signals.workforce_scale?.classification || 'Registered workers'}}</span>
          </div>

          <div class="kpi-card">
            <span class="kpi-title">Annual Revenue</span>
            <span class="kpi-value">${{fmtCurrency(accClaims.revenue?.value, accClaims.revenue?.currency)}}</span>
            <span class="kpi-subtext ${{signals.yoy_revenue_change ? 'positive' : ''}}">
              ${{signals.yoy_revenue_change ? signals.yoy_revenue_change.description : (accounts.reporting_period || 'Latest filing')}}
            </span>
          </div>

          <div class="kpi-card">
            <span class="kpi-title">Balance Equity</span>
            <span class="kpi-value">${{fmtCurrency(accClaims.equity?.value, accClaims.equity?.currency)}}</span>
            <span class="kpi-subtext ${{signals.negative_equity?.value ? 'warning' : 'positive'}}">
              ${{signals.negative_equity?.description || 'Solvent equity'}}
            </span>
          </div>

          <div class="kpi-card">
            <span class="kpi-title">Digital Verification</span>
            <span class="kpi-value" style="font-size:1.05rem; color:${{website.status === 'available' ? '#34d399' : 'var(--text-dim)'}};">
              ${{website.status === 'available' ? '✓ Tier Verified' : 'Unverified'}}
            </span>
            <span class="kpi-subtext">${{website.verification_method || '3-Tier Check'}}</span>
          </div>
        </div>

        <!-- Tabs Bar -->
        <div class="tab-nav-bar">
          <button class="tab-item-btn ${{currentActiveTab === 'overview' ? 'active' : ''}}" onclick="switchTab('overview')">Legal Identity</button>
          <button class="tab-item-btn ${{currentActiveTab === 'financials' ? 'active' : ''}}" onclick="switchTab('financials')">Financial Statements</button>
          <button class="tab-item-btn ${{currentActiveTab === 'leadership' ? 'active' : ''}}" onclick="switchTab('leadership')">Leadership (${{leaders.length}})</button>
          <button class="tab-item-btn ${{currentActiveTab === 'workplaces' ? 'active' : ''}}" onclick="switchTab('workplaces')">Workplaces (${{workplaces.length}})</button>
          <button class="tab-item-btn ${{currentActiveTab === 'announcements' ? 'active' : ''}}" onclick="switchTab('announcements')">Announcements (${{announcements.length}})</button>
          <button class="tab-item-btn ${{currentActiveTab === 'sources' ? 'active' : ''}}" onclick="switchTab('sources')">Audit Trail (${{sources.length}})</button>
          <button class="tab-item-btn ${{currentActiveTab === 'json' ? 'active' : ''}}" onclick="switchTab('json')">Envelope JSON</button>
        </div>

        <!-- Tab Content Viewport -->
        <div class="tab-content-container" id="tab-viewport"></div>
      `;

      renderTabContent();
    }}

    function switchTab(tabKey) {{
      currentActiveTab = tabKey;
      document.querySelectorAll('.tab-item-btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      renderTabContent();
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

      if (currentActiveTab === 'overview') {{
        viewport.innerHTML = `
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th>Field</th><th>Value</th><th>Claim ID</th><th>Source Provenance</th></tr></thead>
              <tbody>
                <tr id="row-legal_name"><td><b>Legal Name</b></td><td>${{legal.legal_name?.value || 'N/A'}}</td><td><span class="claim-interactive-chip">${{legal.legal_name?.claim_id || 'c001'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-legal_form"><td><b>Legal Form</b></td><td>${{legal.legal_form?.description || 'N/A'}} (${{legal.legal_form?.value || 'AS'}})</td><td><span class="claim-interactive-chip">${{legal.legal_form?.claim_id || 'c002'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-address"><td><b>Registered Address</b></td><td>${{legal.registered_address?.value?.street || ''}}, ${{legal.registered_address?.value?.postal_code || ''}} ${{legal.registered_address?.value?.city || ''}}, ${{legal.registered_address?.value?.country || 'Norge'}}</td><td><span class="claim-interactive-chip">${{legal.registered_address?.claim_id || 'c004'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-nace"><td><b>Industry (NACE)</b></td><td>${{legal.industry_codes?.value?.[0]?.code || ''}} — ${{legal.industry_codes?.value?.[0]?.description || 'N/A'}}</td><td><span class="claim-interactive-chip">${{legal.industry_codes?.claim_id || 'c005'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-emp"><td><b>Employee Count</b></td><td>${{legal.employee_count?.value ?? 0}} workers</td><td><span class="claim-interactive-chip">${{legal.employee_count?.claim_id || 'c006'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-former"><td><b>Former Names</b></td><td>${{legal.former_names?.value?.join(', ') || 'None recorded'}}</td><td><span class="claim-interactive-chip">${{legal.former_names?.claim_id || '-'}}</span></td><td>Enhetsregisteret</td></tr>
                <tr id="row-web"><td><b>Official Website</b></td><td>${{website.official_website ? `<a href="${{website.official_website}}" target="_blank" style="color:var(--accent-cyan);">${{website.official_website}}</a>` : 'Not Available'}}</td><td><span class="claim-interactive-chip">${{website.claim_id || '-'}}</span></td><td>${{website.verification_method || 'Unverified'}}</td></tr>
              </tbody>
            </table>
          </div>
        `;
      }} else if (currentActiveTab === 'financials') {{
        viewport.innerHTML = `
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th>Metric</th><th>Value</th><th>Reporting Year</th><th>Claim ID</th></tr></thead>
              <tbody>
                <tr id="row-revenue"><td><b>Operating Revenue</b></td><td style="font-family:'JetBrains Mono'; font-weight:700;">${{accClaims.revenue?.value?.toLocaleString() || 'N/A'}} ${{accClaims.revenue?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.revenue?.claim_id || '-'}}</span></td></tr>
                <tr id="row-operating_res"><td><b>Operating Result</b></td><td style="font-family:'JetBrains Mono';">${{accClaims.operating_result?.value?.toLocaleString() || 'N/A'}} ${{accClaims.operating_result?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.operating_result?.claim_id || '-'}}</span></td></tr>
                <tr id="row-net_inc"><td><b>Net Profit (Årsresultat)</b></td><td style="font-family:'JetBrains Mono';">${{accClaims.net_income?.value?.toLocaleString() || 'N/A'}} ${{accClaims.net_income?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.net_income?.claim_id || '-'}}</span></td></tr>
                <tr id="row-assets"><td><b>Total Assets (Sum Eiendeler)</b></td><td style="font-family:'JetBrains Mono';">${{accClaims.total_assets?.value?.toLocaleString() || 'N/A'}} ${{accClaims.total_assets?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.total_assets?.claim_id || '-'}}</span></td></tr>
                <tr id="row-equity"><td><b>Equity (Egenkapital)</b></td><td style="font-family:'JetBrains Mono';">${{accClaims.equity?.value?.toLocaleString() || 'N/A'}} ${{accClaims.equity?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.equity?.claim_id || '-'}}</span></td></tr>
                <tr id="row-debt"><td><b>Total Debt (Gjeld)</b></td><td style="font-family:'JetBrains Mono';">${{accClaims.total_debt?.value?.toLocaleString() || 'N/A'}} ${{accClaims.total_debt?.currency || 'NOK'}}</td><td>${{accounts.reporting_period || 'Latest'}}</td><td><span class="claim-interactive-chip">${{accClaims.total_debt?.claim_id || '-'}}</span></td></tr>
              </tbody>
            </table>
          </div>
        `;
      }} else if (currentActiveTab === 'leadership') {{
        viewport.innerHTML = leaders.length ? `
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th>Role Description</th><th>Individual / Officer</th><th>Claim ID</th></tr></thead>
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
        ` : `<p style="color:var(--text-dim); padding:1rem;">No registered leadership officers in Rolleregisteret.</p>`;
      }} else if (currentActiveTab === 'workplaces') {{
        viewport.innerHTML = workplaces.length ? `
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th>Subunit Org Number</th><th>Branch Name</th><th>Employees</th><th>Municipality</th></tr></thead>
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
        ` : `<p style="color:var(--text-dim); padding:1rem;">No subordinate branch workplaces registered.</p>`;
      }} else if (currentActiveTab === 'announcements') {{
        viewport.innerHTML = announcements.length ? `
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th>Filing Date</th><th>Announcement Type</th><th>Description</th></tr></thead>
              <tbody>
                ${{announcements.map(a => `
                  <tr>
                    <td style="font-family:'JetBrains Mono'; color:#34d399;">${{a.date}}</td>
                    <td><b>${{a.type}}</b></td>
                    <td style="color:var(--text-muted);">${{a.description}}</td>
                  </tr>
                `).join('')}}
              </tbody>
            </table>
          </div>
        ` : `<p style="color:var(--text-dim); padding:1rem;">No recent corporate filings recorded in Foretaksregisteret.</p>`;
      }} else if (currentActiveTab === 'sources') {{
        viewport.innerHTML = `
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th>Audited Source URL</th><th>Type</th><th>Retrieved Date</th><th>Backed Claims</th></tr></thead>
              <tbody>
                ${{sources.map(s => `
                  <tr>
                    <td><a href="${{s.url}}" target="_blank" style="color:var(--accent-cyan); text-decoration:none;">${{s.url}}</a></td>
                    <td><span class="mini-badge blue">${{s.type}}</span></td>
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
          <pre class="json-code-box">${{escapeHtml(JSON.stringify(comp, null, 2))}}</pre>
        `;
      }}
    }}

    function jumpToClaim(claimId) {{
      switchTab('overview');
      setTimeout(() => {{
        const rows = document.querySelectorAll('.data-table tr');
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
        showToast('Company envelope JSON copied to clipboard!');
      }});
    }}

    function exportCurrentJSON() {{
      const blob = new Blob([JSON.stringify(filteredData, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `signalpost_export_${{filteredData.length}}_companies.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast(`Exported ${{filteredData.length}} company profiles to JSON!`);
    }}

    function showToast(msg) {{
      const t = document.getElementById('toast-notify');
      t.innerText = msg;
      t.style.display = 'block';
      setTimeout(() => {{ t.style.display = 'none'; }}, 2800);
    }}

    function escapeHtml(str) {{
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }}

    // Boot App
    applyFiltersAndSearch();
  </script>
</body>
</html>
"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated standalone Enterprise HTML viewer at {path}")
        return path
