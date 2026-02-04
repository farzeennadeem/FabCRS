"""
Reads telemetry.json + kpis.json from a CyberRangeSim run directory and writes dashboard.html.

Typical usage (later from FabSim script):
  python3 generate_dashboard.py --run-dir /path/to/results/<group>/<run_...>

This script expects:
  <run-dir>/telemetry.json
  <run-dir>/kpis.json
"""
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional


def load_json(path: str):
    with open(path, "r") as f:
        return json.load(f)


def safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def ensure_plotly():
    try:
        import plotly.graph_objects as go
        from plotly.offline import plot as plotly_plot
        return True
    except Exception:
        return False

def build_dashboard_html(run_dir: str, telemetry: list, kpis: dict, run_meta: Optional[dict]):
    import plotly.graph_objects as go
    from plotly.offline import plot as plotly_plot

    # Basic validation
    if not isinstance(telemetry, list) or len(telemetry) == 0:
        raise ValueError("telemetry.json is empty or not a list of rows")

    # Extract time axis + series with graceful fallbacks
    t = [row.get("t") for row in telemetry]

    def series(key, default=0.0):
        return [row.get(key, default) for row in telemetry]

    incoming = series("incoming_rps")
    served = series("served_rps")
    dropped = series("dropped_rps")
    queue = series("queue")
    latency = series("latency_ms")

    def line_fig(title, y_label, x, lines: list[tuple[str, list]]):
        fig = go.Figure()
        for name, y in lines:
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title=y_label,
            legend_title="Series",
            hovermode="x unified",
            margin=dict(l=40, r=20, t=50, b=40),
        )
        return fig

    fig_rps = line_fig(
        "Traffic (RPS)",
        "Requests per second",
        t,
        [("incoming_rps", incoming), ("served_rps", served), ("dropped_rps", dropped)],
    )

    fig_queue = line_fig(
        "Queue Size",
        "Queue",
        t,
        [("queue", queue)],
    )

    fig_latency = line_fig(
        "Latency (ms)",
        "Milliseconds",
        t,
        [("latency_ms", latency)],
    )

    # Convert figures to HTML divs (embed plotly.js once to keep file self-contained)
    div_rps = plotly_plot(fig_rps, include_plotlyjs=True, output_type="div")
    div_queue = plotly_plot(fig_queue, include_plotlyjs=False, output_type="div")
    div_latency = plotly_plot(fig_latency, include_plotlyjs=False, output_type="div")

    # Header info
    attack_type = safe_get(kpis, "attack", "type", default="unknown")
    target_service = safe_get(kpis, "attack", "target_service", default="-")
    availability = kpis.get("availability_pct", kpis.get("availability_pct", "-"))
    # support both "latency_ms" (old) and "peak_latency_ms" (newer)
    latency_kpi = kpis.get("peak_latency_ms", kpis.get("latency_ms", "-"))
    total_dropped = kpis.get("total_dropped", "-")

    # Optional metadata line
    meta_line = ""
    if isinstance(run_meta, dict):
        meta_line = f"""
        <div class="meta">
          <div><b>Timestamp:</b> {run_meta.get("timestamp","-")}</div>
          <div><b>Topology:</b> {run_meta.get("topology_file","-")}</div>
          <div><b>Scenario:</b> {run_meta.get("scenario_file","-")}</div>
          <div><b>Status:</b> {run_meta.get("status","-")}</div>
        </div>
        """

    # A tiny bit of styling (MVP-friendly)
    css = """
    body { font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial; margin: 24px; }
    h1 { margin: 0 0 8px 0; }
    .sub { color: #555; margin-bottom: 16px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 16px 0 20px; }
    .kpi { border: 1px solid #ddd; border-radius: 10px; padding: 12px 14px; background: #fafafa; }
    .kpi .label { color: #666; font-size: 12px; }
    .kpi .value { font-size: 20px; font-weight: 600; margin-top: 6px; }
    .meta { border-left: 4px solid #ddd; padding-left: 12px; color: #444; margin: 10px 0 18px; }
    .section { margin: 18px 0 28px; }
    """

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>CyberRangeSim Dashboard</title>
  <style>{css}</style>
</head>
<body>
  <h1>CyberRangeSim Dashboard</h1>
  <div class="sub">Run folder: <code>{os.path.abspath(run_dir)}</code></div>

  <div class="kpi-grid">
    <div class="kpi"><div class="label">Attack type</div><div class="value">{attack_type}</div></div>
    <div class="kpi"><div class="label">Target service</div><div class="value">{target_service}</div></div>
    <div class="kpi"><div class="label">Availability (%)</div><div class="value">{availability}</div></div>
    <div class="kpi"><div class="label">Latency KPI (ms)</div><div class="value">{latency_kpi}</div></div>
    <div class="kpi"><div class="label">Total dropped</div><div class="value">{total_dropped}</div></div>
    <div class="kpi"><div class="label">Telemetry points</div><div class="value">{len(telemetry)}</div></div>
  </div>

  {meta_line}

  <div class="section">{div_rps}</div>
  <div class="section">{div_queue}</div>
  <div class="section">{div_latency}</div>

  <div class="sub">Generated: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}</div>
</body>
</html>
"""
    return html

def main():
    parser = argparse.ArgumentParser(description="Generate dashboard.html from telemetry.json + kpis.json")
    parser.add_argument("--run-dir", required=True, help="Run directory containing telemetry.json and kpis.json")
    parser.add_argument("--out", default=None, help="Output HTML path (default: <run-dir>/dashboard.html)")
    args = parser.parse_args()

    run_dir = args.run_dir
    if not os.path.isdir(run_dir):
        print(f"ERROR: --run-dir is not a directory: {run_dir}", file=sys.stderr)
        return 2

    telemetry_path = os.path.join(run_dir, "telemetry.json")
    kpis_path = os.path.join(run_dir, "kpis.json")
    run_meta_path = os.path.join(run_dir, "run_meta.json")

    missing = [p for p in [telemetry_path, kpis_path] if not os.path.exists(p)]
    if missing:
        print("ERROR: Missing required file(s):", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 2

    if not ensure_plotly():
        print("ERROR: plotly is not installed in this environment.", file=sys.stderr)
        print("Fix: pip install plotly", file=sys.stderr)
        return 2

    telemetry = load_json(telemetry_path)
    kpis = load_json(kpis_path)
    run_meta = load_json(run_meta_path) if os.path.exists(run_meta_path) else None

    html = build_dashboard_html(run_dir, telemetry, kpis, run_meta)

    out_path = args.out or os.path.join(run_dir, "dashboard.html")
    with open(out_path, "w") as f:
        f.write(html)

    print(f"Dashboard written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())