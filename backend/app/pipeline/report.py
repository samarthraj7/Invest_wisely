"""Step 6 - Report assembly + export.

Produces a self-contained HTML memo from the structured report, and attempts a
PDF via WeasyPrint (falls back to HTML if the system lacks the native deps).
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from ..schemas import InvestmentReport

_SEV_COLOR = {"critical": "#b91c1c", "high": "#dc2626", "medium": "#d97706", "low": "#65a30d"}

_TEMPLATE = Template(
    """<!doctype html><html><head><meta charset="utf-8">
<title>{{ r.company_snapshot.name }} — Investment Memo</title>
<style>
 body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#1e293b;max-width:820px;
      margin:0 auto;padding:40px;line-height:1.5}
 h1{font-size:26px;margin-bottom:2px} h2{border-bottom:2px solid #e2e8f0;padding-bottom:6px;
    margin-top:34px;font-size:18px;color:#0f172a}
 .muted{color:#64748b} .pill{display:inline-block;padding:2px 10px;border-radius:999px;
    font-size:12px;font-weight:600}
 .src{font-size:11px;color:#64748b} .conf{font-size:10px;text-transform:uppercase;
    letter-spacing:.04em;color:#94a3b8;margin-left:6px}
 .claim{margin:6px 0;padding:8px 12px;background:#f8fafc;border-left:3px solid #cbd5e1;border-radius:4px}
 .flag{margin:8px 0;padding:10px 14px;border-radius:6px;background:#fef2f2}
 table{width:100%;border-collapse:collapse;margin-top:8px} td,th{text-align:left;padding:6px 8px;
    border-bottom:1px solid #e2e8f0;font-size:14px;vertical-align:top}
 .note{background:#f1f5f9;border-radius:8px;padding:12px 16px;font-size:13px;color:#475569;margin-top:30px}
 .rec{font-size:20px;font-weight:700}
</style></head><body>

<h1>{{ r.company_snapshot.name }}</h1>
<div class="muted">{{ r.company_snapshot.one_liner }}</div>
<div class="muted">{{ r.company_snapshot.sector or '' }} · {{ r.company_snapshot.stage or '' }}
 · {{ r.company_snapshot.location or '' }} · Ask: {{ r.company_snapshot.ask or 'n/a' }}</div>
{% if r.mock_mode %}<p><span class="pill" style="background:#fef9c3;color:#854d0e">MOCK MODE — add API keys for live research</span></p>{% endif %}

<h2>1 · Company snapshot</h2>
{% for c in r.company_snapshot.deck_claims %}{{ claim(c) }}{% endfor %}

<h2>2 · Team analysis</h2>
{% for m in r.team_analysis %}
 <p><b>{{ m.name }}</b> — {{ m.title or '' }}
   <span class="conf">research: {{ m.research_confidence.value }}</span></p>
 {% for c in m.researched_background %}{{ claim(c) }}{% endfor %}
 {% for c in m.gaps_vs_venture %}{{ claim(c) }}{% endfor %}
{% endfor %}

<h2>3 · Competitive landscape</h2>
{% for c in r.competitive_landscape.named_in_deck %}{{ claim(c.note) }}{% endfor %}
{% for c in r.competitive_landscape.discovered %}{{ claim(c.note) }}{% endfor %}
{% for c in r.competitive_landscape.differentiation_assessment %}{{ claim(c) }}{% endfor %}

<h2>4 · Red flags</h2>
{% for f in r.red_flags %}
 <div class="flag" style="border-left:4px solid {{ sev(f.severity.value) }}">
  <b style="color:{{ sev(f.severity.value) }}">[{{ f.severity.value|upper }}]</b> {{ f.title }}<br>
  <span class="src">{{ f.reasoning.claim }} — {{ f.reasoning.source_ref }}</span></div>
{% endfor %}

<h2>5 · Suggested diligence questions</h2>
<ol>{% for q in r.diligence_questions %}<li>{{ q.question }}
 <span class="src">→ {{ q.targets_gap }}</span></li>{% endfor %}</ol>

<h2>6 · Valuation analysis</h2>
<p><b>Comp-derived range:</b> {{ r.valuation.range_low }} – {{ r.valuation.range_high }}
 &nbsp;|&nbsp; <b>Deck ask:</b> {{ r.valuation.deck_ask }}
 &nbsp;|&nbsp; <b>Multiples:</b> {{ r.valuation.multiples_used }}</p>
<table><tr><th>Comp</th><th>Detail</th><th>Source</th></tr>
 {% for c in r.valuation.comps %}<tr><td>{{ c.company }}</td><td>{{ c.detail }}</td>
   <td class="src">{{ c.source.source_ref }}</td></tr>{% endfor %}</table>
<p class="muted"><b>Assumptions:</b></p>
<ul>{% for a in r.valuation.assumptions %}<li>{{ a }}</li>{% endfor %}</ul>
{% for c in r.valuation.ask_vs_comps %}{{ claim(c) }}{% endfor %}

<h2>7 · Recommendation</h2>
<p class="rec">{{ r.recommendation.recommendation.value|upper }}
 <span class="pill" style="background:#fee2e2;color:#991b1b">Risk: {{ r.recommendation.risk_rating }}</span></p>
<p>{{ r.recommendation.rationale }}</p>
{% if r.recommendation.suggested_check_size %}<p><b>Suggested check:</b>
 {{ r.recommendation.suggested_check_size }}</p>{% endif %}
<p class="muted"><b>Named risk factors:</b></p>
{% for c in r.recommendation.risk_factors %}{{ claim(c) }}{% endfor %}

<div class="note">{{ r.analyst_note }}</div>
</body></html>""",
)


def _claim_html(c) -> str:
    return (
        f'<div class="claim">{c.claim}'
        f'<div class="src">{c.source_type.value}: {c.source_ref}'
        f'<span class="conf">{c.confidence.value}</span></div></div>'
    )


def render_html(report: InvestmentReport) -> str:
    return _TEMPLATE.render(
        r=report,
        claim=_claim_html,
        sev=lambda s: _SEV_COLOR.get(s, "#64748b"),
    )


def export_pdf(report: InvestmentReport, out_path: str | Path) -> tuple[Path, str]:
    """Write the report to disk. Returns (path, format) where format is 'pdf' or 'html'."""
    out_path = Path(out_path)
    html = render_html(report)
    try:
        from weasyprint import HTML

        pdf_path = out_path.with_suffix(".pdf")
        HTML(string=html).write_pdf(str(pdf_path))
        return pdf_path, "pdf"
    except Exception:
        html_path = out_path.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")
        return html_path, "html"
