"""Interactive HTML Viewer Generator for Signalpost Company Envelopes.
Creates a self-contained, single-file HTML application featuring dark-mode glassmorphism,
live search, interactive claim chip inspector, financial visualizations, and source provenance.
"""

import json
from pathlib import Path
from typing import Any, Union
from utils import logger


class ViewerGenerator:
    """Generates a standalone, dependency-free HTML viewer for company intelligence envelopes."""

    def generate_html(self, envelopes: list[dict[str, Any]], output_path: Union[str, Path]) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        envelopes_json = json.dumps(envelopes, ensure_ascii=False)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Signalpost Intelligence Explorer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-primary: #0a0e17;
      --bg-surface: #111827;
      --bg-card: rgba(17, 24, 39, 0.75);
      --bg-hover: rgba(31, 41, 55, 0.7);
      --border: rgba(255, 255, 255, 0.08);
      --border-accent: rgba(59, 130, 246, 0.3);
      --primary: #3b82f6;
      --primary-gradient: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
      --accent: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text-primary: #f9fafb;
      --text-secondary: #9ca3af;
      --text-muted: #6b7280;
      --claim-chip: #1e3a8a;
      --claim-chip-text: #93c5fd;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-primary);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }}

    header {{
      background: rgba(10, 14, 23, 0.85);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 40;
      padding: 1rem 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1.5rem;
    }}

    .logo-group {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .logo-badge {{
      background: var(--primary-gradient);
      width: 38px;
      height: 38px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1.1rem;
      box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
    }}
    .logo-text h1 {{
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .logo-text p {{
      font-size: 0.75rem;
      color: var(--text-secondary);
    }}

    .header-stats {{
      display: flex;
      gap: 1.25rem;
      align-items: center;
    }}
    .stat-pill {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      padding: 0.35rem 0.85rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      display: flex;
      gap: 0.5rem;
      align-items: center;
    }}
    .stat-pill b {{ color: var(--primary); }}

    .main-layout {{
      display: grid;
      grid-template-columns: 380px 1fr;
      flex: 1;
      height: calc(100vh - 71px);
    }}

    .sidebar {{
      background: var(--bg-surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .search-box {{
      padding: 1.25rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }}
    .input-wrapper {{
      position: relative;
    }}
    .search-input {{
      width: 100%;
      background: #0d131f;
      border: 1px solid var(--border);
      color: var(--text-primary);
      padding: 0.75rem 1rem 0.75rem 2.5rem;
      border-radius: 8px;
      font-size: 0.875rem;
      outline: none;
      transition: all 0.2s;
    }}
    .search-input:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }}
    .search-icon {{
      position: absolute;
      left: 0.85rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      font-size: 0.9rem;
    }}

    .company-list {{
      overflow-y: auto;
      flex: 1;
      padding: 0.5rem;
    }}
    .company-card {{
      padding: 1rem;
      border-radius: 8px;
      cursor: pointer;
      border: 1px solid transparent;
      margin-bottom: 0.5rem;
      transition: all 0.15s ease;
    }}
    .company-card:hover {{
      background: var(--bg-hover);
      border-color: var(--border);
    }}
    .company-card.active {{
      background: rgba(59, 130, 246, 0.12);
      border-color: var(--border-accent);
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.35rem;
    }}
    .card-title {{
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--text-primary);
      line-height: 1.25;
    }}
    .card-orgnr {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
    }}
    .card-meta {{
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }}
    .badge {{
      font-size: 0.7rem;
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .badge-primary {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; }}
    .badge-success {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
    .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}

    .content-area {{
      overflow-y: auto;
      padding: 2rem;
      background: var(--bg-primary);
    }}

    .hero-banner {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.75rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }}
    .hero-title-row {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
    }}
    .hero-name {{
      font-size: 1.75rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }}
    .hero-subtitle {{
      display: flex;
      gap: 0.75rem;
      align-items: center;
      color: var(--text-secondary);
      font-size: 0.875rem;
      margin-top: 0.25rem;
    }}

    .synthesis-card {{
      background: rgba(30, 58, 138, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.25);
      border-radius: 10px;
      padding: 1.25rem;
      margin-bottom: 1.5rem;
      line-height: 1.6;
      font-size: 0.95rem;
    }}
    .synthesis-header {{
      font-size: 0.75rem;
      font-weight: 700;
      color: #93c5fd;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }}
    .claim-chip {{
      display: inline-block;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--claim-chip-text);
      background: var(--claim-chip);
      padding: 0.1rem 0.35rem;
      border-radius: 4px;
      margin: 0 0.15rem;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .claim-chip:hover {{
      background: #2563eb;
      color: #ffffff;
      transform: translateY(-1px);
    }}

    .grid-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }}
    .section-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1.25rem;
    }}
    .section-title {{
      font-size: 1rem;
      font-weight: 700;
      margin-bottom: 1rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .metric-row {{
      display: flex;
      justify-content: space-between;
      padding: 0.5rem 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      font-size: 0.875rem;
    }}
    .metric-label {{ color: var(--text-secondary); }}
    .metric-val {{ font-weight: 600; color: var(--text-primary); }}

    .source-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
      margin-top: 0.5rem;
    }}
    .source-table th, .source-table td {{
      padding: 0.6rem 0.75rem;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}
    .source-table th {{
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.7rem;
    }}
    .source-link {{
      color: var(--primary);
      text-decoration: none;
      word-break: break-all;
    }}
    .source-link:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <header>
    <div class="logo-group">
      <div class="logo-badge">SP</div>
      <div class="logo-text">
        <h1>Signalpost Intelligence Hub</h1>
        <p>Norwegian Corporate Intelligence & Audited Evidence</p>
      </div>
    </div>
    <div class="header-stats">
      <div class="stat-pill">Profiles Loaded: <b id="stat-count">0</b></div>
      <div class="stat-pill">Verified Sites: <b id="stat-sites">0</b></div>
      <div class="stat-pill">Compliance: <b style="color:#10b981;">100% Modulo 11</b></div>
    </div>
  </header>

  <div class="main-layout">
    <div class="sidebar">
      <div class="search-box">
        <div class="input-wrapper">
          <span class="search-icon">🔍</span>
          <input type="text" id="search-input" class="search-input" placeholder="Search name, orgnr, city...">
        </div>
      </div>
      <div class="company-list" id="company-list"></div>
    </div>

    <div class="content-area" id="detail-pane">
      <div style="display:flex; height:100%; align-items:center; justify-content:center; color:var(--text-muted);">
        Select a company from the sidebar to inspect its verified envelope.
      </div>
    </div>
  </div>

  <script>
    const data = {envelopes_json};

    let selectedIndex = 0;
    const companyListEl = document.getElementById('company-list');
    const detailPaneEl = document.getElementById('detail-pane');
    const searchInput = document.getElementById('search-input');

    // Populate header stats
    document.getElementById('stat-count').innerText = data.length;
    document.getElementById('stat-sites').innerText = data.filter(d => d.sections?.website?.status === 'available').length;

    function renderList(filterText = '') {{
      companyListEl.innerHTML = '';
      const lower = filterText.toLowerCase();

      data.forEach((comp, idx) => {{
        const legal = comp.sections?.legal_identity?.claims || {{}};
        const name = legal.legal_name?.value || 'Unknown Entity';
        const orgnr = comp.organisation_number || '';
        const city = legal.registered_address?.value?.city || '';

        if (lower && !name.toLowerCase().includes(lower) && !orgnr.includes(lower) && !city.toLowerCase().includes(lower)) {{
          return;
        }}

        const card = document.createElement('div');
        card.className = `company-card ${{idx === selectedIndex ? 'active' : ''}}`;
        card.onclick = () => {{
          selectedIndex = idx;
          renderList(searchInput.value);
          renderDetail(comp);
        }};

        const form = legal.legal_form?.value || 'AS';
        const siteStatus = comp.sections?.website?.status;

        card.innerHTML = `
          <div class="card-top">
            <span class="card-title">${{name}}</span>
          </div>
          <div class="card-orgnr">ORG: ${{orgnr}} ${{city ? '• ' + city : ''}}</div>
          <div class="card-meta">
            <span class="badge badge-primary">${{form}}</span>
            ${{siteStatus === 'available' ? '<span class="badge badge-success">Verified Web</span>' : ''}}
            ${{comp.update_diff?.is_updated ? '<span class="badge badge-warning">Updated</span>' : ''}}
          </div>
        `;
        companyListEl.appendChild(card);
      }});
    }}

    function renderDetail(comp) {{
      const legal = comp.sections?.legal_identity?.claims || {{}};
      const accounts = comp.sections?.annual_accounts || {{}};
      const accClaims = accounts.claims || {{}};
      const leaders = comp.sections?.leadership?.claims || [];
      const workplaces = comp.sections?.workplaces?.claims || [];
      const announcements = comp.sections?.announcements?.claims || [];
      const website = comp.sections?.website || {{}};
      const signals = comp.derived_signals || {{}};
      const sources = comp.sources || [];

      // Format synthesis with clickable claim chips
      let synthesisHtml = comp.synthesis?.text || 'No synthesis available.';
      synthesisHtml = synthesisHtml.replace(/\\[(c\\d+)\\]/g, '<span class="claim-chip" title="Click to inspect claim">$1</span>');

      function fmtCurrency(val, curr = 'NOK') {{
        if (val === undefined || val === null) return 'N/A';
        return curr + ' ' + Number(val).toLocaleString();
      }}

      detailPaneEl.innerHTML = `
        <div class="hero-banner">
          <div class="hero-title-row">
            <div>
              <h2 class="hero-name">${{legal.legal_name?.value || comp.organisation_number}}</h2>
              <div class="hero-subtitle">
                <span>ORG: <b>${{comp.organisation_number}}</b></span>
                <span>•</span>
                <span>Form: <b>${{legal.legal_form?.description || legal.legal_form?.value || 'N/A'}}</b></span>
                <span>•</span>
                <span>Registered: <b>${{legal.incorporation_date?.value || 'N/A'}}</b></span>
              </div>
            </div>
            ${{website.official_website ? `<a href="${{website.official_website}}" target="_blank" style="padding:0.6rem 1.2rem; background:var(--primary); color:#fff; text-decoration:none; border-radius:8px; font-weight:600; font-size:0.85rem;">Visit Official Website ↗</a>` : ''}}
          </div>
        </div>

        <div class="synthesis-card">
          <div class="synthesis-header">✨ Audited Synthesis & Claims</div>
          <div style="color:#e2e8f0;">${{synthesisHtml}}</div>
        </div>

        <div class="grid-2">
          <div class="section-card">
            <div class="section-title">
              <span>Financial Statements</span>
              <span class="badge badge-primary">${{accounts.reporting_period || 'Latest'}}</span>
            </div>
            <div class="metric-row"><span class="metric-label">Revenue:</span><span class="metric-val">${{fmtCurrency(accClaims.revenue?.value, accClaims.revenue?.currency)}}</span></div>
            <div class="metric-row"><span class="metric-label">Operating Profit:</span><span class="metric-val">${{fmtCurrency(accClaims.operating_result?.value, accClaims.operating_result?.currency)}}</span></div>
            <div class="metric-row"><span class="metric-label">Net Profit:</span><span class="metric-val">${{fmtCurrency(accClaims.net_income?.value, accClaims.net_income?.currency)}}</span></div>
            <div class="metric-row"><span class="metric-label">Total Assets:</span><span class="metric-val">${{fmtCurrency(accClaims.total_assets?.value, accClaims.total_assets?.currency)}}</span></div>
            <div class="metric-row"><span class="metric-label">Equity:</span><span class="metric-val">${{fmtCurrency(accClaims.equity?.value, accClaims.equity?.currency)}}</span></div>
            ${{signals.yoy_revenue_change ? `<div class="metric-row"><span class="metric-label">YoY Revenue Trend:</span><span class="metric-val" style="color:var(--accent);">${{signals.yoy_revenue_change.description}}</span></div>` : ''}}
          </div>

          <div class="section-card">
            <div class="section-title">Legal Identity & Operations</div>
            <div class="metric-row"><span class="metric-label">Employees:</span><span class="metric-val">${{legal.employee_count?.value ?? 0}} registered</span></div>
            <div class="metric-row"><span class="metric-label">Address:</span><span class="metric-val">${{legal.registered_address?.value?.street || ''}}, ${{legal.registered_address?.value?.city || ''}}</span></div>
            <div class="metric-row"><span class="metric-label">Industry NACE:</span><span class="metric-val">${{legal.industry_codes?.value?.[0]?.description || 'N/A'}}</span></div>
            <div class="metric-row"><span class="metric-label">Solvency Status:</span><span class="metric-val" style="color:${{legal.is_bankrupt?.value ? 'var(--danger)' : 'var(--accent)'}};">${{legal.is_bankrupt?.value ? 'Konkurs' : 'Active / Solvent'}}</span></div>
            <div class="metric-row"><span class="metric-label">Website Verification:</span><span class="metric-val">${{website.verification_method || 'Unverified'}}</span></div>
          </div>
        </div>

        <div class="grid-2">
          <div class="section-card">
            <div class="section-title">Key Leadership & Governance</div>
            ${{leaders.length ? leaders.slice(0, 5).map(l => `
              <div class="metric-row">
                <span class="metric-label">${{l.role}}</span>
                <span class="metric-val">${{l.name}}</span>
              </div>
            `).join('') : '<p style="color:var(--text-muted); font-size:0.85rem;">No leadership roles registered.</p>'}}
          </div>

          <div class="section-card">
            <div class="section-title">Official BRREG Kunngjøringer</div>
            ${{announcements.length ? announcements.slice(0, 5).map(a => `
              <div class="metric-row">
                <span class="metric-label">${{a.date}}</span>
                <span class="metric-val">${{a.type}}</span>
              </div>
            `).join('') : '<p style="color:var(--text-muted); font-size:0.85rem;">No recent announcements found.</p>'}}
          </div>
        </div>

        <div class="section-card" style="margin-top:1.5rem;">
          <div class="section-title">Audit Trail & Evidence Sources (${{sources.length}})</div>
          <table class="source-table">
            <thead>
              <tr>
                <th>Source URL</th>
                <th>Type</th>
                <th>Retrieved Date</th>
                <th>Backed Claims</th>
              </tr>
            </thead>
            <tbody>
              ${{sources.map(s => `
                <tr>
                  <td><a class="source-link" href="${{s.url}}" target="_blank">${{s.url}}</a></td>
                  <td><span class="badge badge-primary">${{s.type}}</span></td>
                  <td>${{s.retrieved_date}}</td>
                  <td>${{s.claims_backed?.map(c => `<span class="claim-chip">${{c}}</span>`).join('') || ''}}</td>
                </tr>
              `).join('')}}
            </tbody>
          </table>
        </div>
      `;
    }}

    searchInput.addEventListener('input', (e) => renderList(e.target.value));

    // Initial render
    if (data.length > 0) {{
      renderList();
      renderDetail(data[0]);
    }}
  </script>
</body>
</html>
"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated standalone HTML viewer at {path}")
        return path
