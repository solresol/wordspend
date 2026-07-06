"""Static site generation for wordspend."""

from __future__ import annotations

import html
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .analysis import dataframe_to_records, load_analysis_outputs


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None or value == "":
        return "n/a"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return html.escape(str(value))


def _read_catalog(catalog_path: str | Path | None) -> pd.DataFrame:
    if not catalog_path:
        return pd.DataFrame()
    path = Path(catalog_path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _copy_analysis_files(analysis_dir: Path, output_dir: Path) -> None:
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in ["metrics.json", "segments.csv", "source_predictors.csv", "target_predictors.csv"]:
        source = analysis_dir / name
        if source.exists():
            shutil.copy2(source, data_dir / name)


def _layout(title: str, active: str, body: str) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    nav = []
    for href, label, key in [
        ("index.html", "Results", "results"),
        ("corpus.html", "Corpus", "corpus"),
        ("methods.html", "Methods", "methods"),
        ("paper.html", "Paper", "paper"),
    ]:
        cls = ' class="active"' if key == active else ""
        nav.append(f'<a href="{href}"{cls}>{label}</a>')
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="assets/site.css">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyebrow">wordspend.symmachus.org</p>
      <h1>Word Spend</h1>
      <p class="dek">Translation residuals as evidence for relative lexical compression.</p>
    </div>
    <nav>{"".join(nav)}</nav>
  </header>
  <main>
{body}
  </main>
  <footer>
    Generated {generated}. Bootstrap results are diagnostic until multi-corpus and translator controls are complete.
  </footer>
</body>
</html>
"""


def _metrics_panel(metrics: dict[str, Any]) -> str:
    items = [
        ("Segments", metrics.get("segment_count")),
        ("Works", metrics.get("work_count")),
        ("Metric", metrics.get("metric")),
        ("Baseline", metrics.get("baseline_model")),
        ("R squared", _fmt(metrics.get("r2"))),
        ("Residual SD", _fmt(metrics.get("residual_std"))),
        ("Source features", metrics.get("source_feature_count")),
        ("Target features", metrics.get("target_feature_count")),
    ]
    cells = "\n".join(
        f'<div class="metric"><span>{html.escape(str(label))}</span><strong>{html.escape(str(value if value is not None else "n/a"))}</strong></div>'
        for label, value in items
    )
    return f'<section class="metrics-grid">{cells}</section>'


def _predictor_table(frame: pd.DataFrame, title: str) -> str:
    if frame is None or frame.empty:
        return f"<section><h2>{html.escape(title)}</h2><p>No predictors available yet.</p></section>"
    rows = []
    for _, row in frame.head(25).iterrows():
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('feature', '')))}</td>"
            f"<td class=\"num\">{_fmt(row.get('coefficient'), 4)}</td>"
            f"<td class=\"num\">{html.escape(str(row.get('segment_count', '')))}</td>"
            f"<td class=\"num\">{_fmt(row.get('mean_residual_with_feature'), 3)}</td>"
            f"<td class=\"num\">{_fmt(row.get('mean_residual_without_feature'), 3)}</td>"
            "</tr>"
        )
    return f"""<section>
  <h2>{html.escape(title)}</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Feature</th>
          <th>Coefficient</th>
          <th>Segments</th>
          <th>Mean residual with</th>
          <th>Mean residual without</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</section>"""


def _chart_script(segments: pd.DataFrame) -> str:
    if segments is None or segments.empty:
        return "<p>No segment residuals available yet.</p>"
    records = dataframe_to_records(
        segments[
            [
                "work_slug",
                "segment_ref",
                "source_length",
                "target_length",
                "expected_target_length",
                "residual",
            ]
        ]
    )
    data = json.dumps(records)
    return f"""<div id="length-chart" class="chart"></div>
<script>
const segmentData = {data};
const trace = {{
  x: segmentData.map(d => d.source_length),
  y: segmentData.map(d => d.target_length),
  mode: 'markers',
  type: 'scattergl',
  marker: {{
    size: 7,
    color: segmentData.map(d => d.residual),
    colorscale: 'RdBu',
    reversescale: true,
    colorbar: {{title: 'Residual'}},
    opacity: 0.78
  }},
  text: segmentData.map(d => `${{d.work_slug}} ${{d.segment_ref}}<br>residual ${{Number(d.residual).toFixed(3)}}`),
  hovertemplate: '%{{text}}<br>source %{{x}}<br>target %{{y}}<extra></extra>'
}};
const sorted = [...segmentData].sort((a, b) => a.source_length - b.source_length);
const line = {{
  x: sorted.map(d => d.source_length),
  y: sorted.map(d => d.expected_target_length),
  mode: 'lines',
  type: 'scatter',
  line: {{color: '#2f6f73', width: 2}},
  name: 'expected target length',
  hoverinfo: 'skip'
}};
Plotly.newPlot('length-chart', [trace, line], {{
  margin: {{l: 58, r: 24, t: 10, b: 52}},
  xaxis: {{title: 'Source length'}},
  yaxis: {{title: 'Target length'}},
  paper_bgcolor: 'white',
  plot_bgcolor: 'white',
  showlegend: false
}}, {{responsive: true, displaylogo: false}});
</script>"""


def _corpus_table(catalog: pd.DataFrame, segments: pd.DataFrame | None = None) -> str:
    if catalog is None or catalog.empty:
        return "<p>No corpus catalog available.</p>"
    counts = {}
    if segments is not None and not segments.empty and "work_slug" in segments.columns:
        counts = segments.groupby("work_slug").size().to_dict()
    rows = []
    for _, row in catalog.iterrows():
        slug = row.get("slug", "")
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('title', '')))}</td>"
            f"<td>{html.escape(str(row.get('author', '') or ''))}</td>"
            f"<td>{html.escape(str(row.get('source_language', '')))}</td>"
            f"<td>{html.escape(str(row.get('target_languages', row.get('planned_target_languages', '')) or ''))}</td>"
            f"<td>{html.escape(str(row.get('genre', '') or ''))}</td>"
            f"<td>{html.escape(str(row.get('priority', '') or ''))}</td>"
            f"<td>{html.escape(str(row.get('status', '') or ''))}</td>"
            f"<td class=\"num\">{counts.get(slug, 0)}</td>"
            "</tr>"
        )
    return f"""<div class="table-wrap">
<table>
  <thead>
    <tr>
      <th>Work</th>
      <th>Author</th>
      <th>Source</th>
      <th>Targets</th>
      <th>Genre</th>
      <th>Priority</th>
      <th>Status</th>
      <th>Segments</th>
    </tr>
  </thead>
  <tbody>{''.join(rows)}</tbody>
</table>
</div>"""


def _write_css(output_dir: Path) -> None:
    assets = output_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "site.css").write_text(
        """
:root {
  --ink: #18211f;
  --muted: #596662;
  --line: #d8ded9;
  --paper: #ffffff;
  --wash: #f5f7f3;
  --teal: #2f6f73;
  --rust: #9f4d2f;
  --gold: #b18825;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--ink);
  background: var(--paper);
  line-height: 1.55;
}
.topbar {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: end;
  padding: 34px min(5vw, 64px) 26px;
  border-bottom: 1px solid var(--line);
  background: var(--wash);
}
.eyebrow {
  margin: 0 0 4px;
  color: var(--teal);
  font-size: 0.84rem;
  font-weight: 700;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  font-size: clamp(2.2rem, 5vw, 4.6rem);
  line-height: 0.95;
  letter-spacing: 0;
}
.dek {
  max-width: 720px;
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 1.08rem;
}
nav {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
nav a {
  color: var(--ink);
  text-decoration: none;
  padding: 7px 0;
  border-bottom: 2px solid transparent;
}
nav a.active {
  color: var(--rust);
  border-color: var(--rust);
}
main {
  padding: 0;
}
section {
  padding: 28px min(5vw, 64px);
  border-bottom: 1px solid var(--line);
}
section.narrow {
  max-width: 980px;
}
h2 {
  margin: 0 0 14px;
  font-size: 1.35rem;
}
p {
  max-width: 920px;
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1px;
  background: var(--line);
  padding: 1px;
}
.metric {
  background: white;
  padding: 16px;
  min-height: 92px;
}
.metric span {
  display: block;
  color: var(--muted);
  font-size: 0.86rem;
}
.metric strong {
  display: block;
  margin-top: 8px;
  font-size: 1.4rem;
}
.chart {
  width: 100%;
  height: min(62vh, 640px);
  min-height: 390px;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.94rem;
}
th, td {
  border-bottom: 1px solid var(--line);
  padding: 8px 10px;
  vertical-align: top;
  text-align: left;
}
th {
  background: var(--wash);
  font-weight: 700;
}
.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.downloads {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.downloads a {
  color: var(--teal);
  font-weight: 700;
}
footer {
  padding: 24px min(5vw, 64px) 36px;
  color: var(--muted);
  font-size: 0.9rem;
}
@media (max-width: 760px) {
  .topbar {
    display: block;
  }
  nav {
    margin-top: 22px;
  }
  .chart {
    min-height: 340px;
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def generate_site(
    *,
    analysis_dir: str | Path,
    output_dir: str | Path,
    catalog_path: str | Path | None = None,
) -> None:
    """Generate the static site."""
    output = Path(output_dir)
    analysis_root = Path(analysis_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_css(output)
    _copy_analysis_files(analysis_root, output)

    analysis = load_analysis_outputs(analysis_root)
    metrics = analysis.get("metrics", {})
    segments = analysis.get("segments", pd.DataFrame())
    source_predictors = analysis.get("source_predictors", pd.DataFrame())
    target_predictors = analysis.get("target_predictors", pd.DataFrame())
    catalog = _read_catalog(catalog_path)

    index_body = f"""
<section class="narrow">
  <h2>Current Results</h2>
  <p>The live analysis fits a source-to-target length baseline and then looks for source and target terms associated with unexpectedly long or short translations. Positive residuals mean the translation spends more words than expected after controlling for source length.</p>
</section>
{_metrics_panel(metrics)}
<section>
  <h2>Source Length vs Target Length</h2>
  {_chart_script(segments)}
</section>
{_predictor_table(source_predictors, "Source Terms Predicting Residuals")}
{_predictor_table(target_predictors, "Target Terms Predicting Residuals")}
<section>
  <h2>Downloads</h2>
  <p class="downloads">
    <a href="data/metrics.json">metrics.json</a>
    <a href="data/segments.csv">segments.csv</a>
    <a href="data/source_predictors.csv">source_predictors.csv</a>
    <a href="data/target_predictors.csv">target_predictors.csv</a>
  </p>
</section>
"""
    (output / "index.html").write_text(_layout("Word Spend", "results", index_body), encoding="utf-8")

    corpus_body = f"""
<section class="narrow">
  <h2>Corpus Inventory</h2>
  <p>The catalog is broader than the current analysed data. Candidate rows are included to make the intended comparison set visible before every source and translation has been imported and licensed.</p>
</section>
<section>
  {_corpus_table(catalog, segments)}
</section>
"""
    (output / "corpus.html").write_text(_layout("Word Spend Corpus", "corpus", corpus_body), encoding="utf-8")

    methods_body = """
<section class="narrow">
  <h2>Method</h2>
  <p>For each aligned segment, the default model regresses log target length on log source length. The residual is the amount by which the translation is longer or shorter than expected. A regularised lexical model then estimates which source and target terms are associated with those residuals.</p>
  <p>Paper-facing analyses should use existing translations with target language, translator, edition, and publication date recorded. Machine-generated rows are allowed only as bootstrap diagnostics and should be excluded from evidential claims.</p>
  <p>The method is intentionally cautious. Residuals may reflect lexical compression, morphology, genre, named entities, target language, translation date, translator style, alignment quality, or editorial practice. The public tables are leads for closer reading, not direct cultural conclusions.</p>
</section>
<section class="narrow">
  <h2>Controls Still Needed</h2>
  <p>The bootstrap run needs multi-work Greek checks, multiple published translators, non-English target languages, non-Greek corpora, named-entity sensitivity checks, alternate length metrics, and held-out validation before the results should be used as paper evidence.</p>
</section>
"""
    (output / "methods.html").write_text(_layout("Word Spend Methods", "methods", methods_body), encoding="utf-8")

    paper_body = """
<section class="narrow">
  <h2>Paper Plan</h2>
  <p>The planned paper is a method paper and first empirical study: translation residuals as a way to locate relative lexical, grammatical, and cultural compression. The likely first venues are Computational Humanities Research, Journal of Cultural Analytics, Digital Scholarship in the Humanities, or an ACL-adjacent humanities/NLP workshop if the corpus and tooling become central.</p>
  <p>The first paper should not claim that residuals measure cultural importance directly. It should show that the residual method finds stable, interpretable places where existing translations spend unexpected words, then validate those places across works, translators, target languages, publication periods, and language families.</p>
</section>
"""
    (output / "paper.html").write_text(_layout("Word Spend Paper", "paper", paper_body), encoding="utf-8")
