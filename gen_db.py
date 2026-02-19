"""
Reads telemetry.json + kpis.json (and optionally topology.yml + run_meta.json)
from a CyberRangeSim run directory and writes dashboard.html.

Usage:
  python3 gen_db.py --run-dir /path/to/run_folder

Required:
  <run-dir>/telemetry.json
  <run-dir>/kpis.json

Optional (for topology map + nice metadata):
  <run-dir>/topology.yml
  <run-dir>/run_meta.json
"""
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# Optional deps
try:
    import yaml
except Exception:
    yaml = None

try:
    import networkx as nx
except Exception:
    nx = None

try:
    import plotly.graph_objects as go
    from plotly.offline import plot as plotly_plot
except Exception:
    go = None
    plotly_plot = None


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


def try_load_yaml(path: str) -> Optional[dict]:
    if yaml is None or not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return yaml.safe_load(f)


def infer_attack_type(kpis: dict, telemetry_rows: list) -> str:
    t = safe_get(kpis, "attack", "type", default=None)
    if isinstance(t, str) and t:
        return t

    if telemetry_rows:
        sample = telemetry_rows[0]
        if isinstance(sample, dict) and ("infected_nodes" in sample or "node_states" in sample):
            return "malware_spread"
        if isinstance(sample, dict) and ("incoming_rps" in sample or "served_rps" in sample):
            return "http_get_flood"
    return "unknown"


def line_fig(title: str, y_label: str, x: list, lines: List[Tuple[str, list]]):
    fig = go.Figure()
    for name, y in lines:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title=y_label,
        hovermode="x unified",
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def build_topology_animation_div(topology: dict, telemetry_rows: list) -> Optional[str]:
    """
    Builds an animated topology map if:
      - topology.yml exists and parses
      - telemetry rows include per-node: node_states (dict node->S/I/R)
    """
    if nx is None or go is None or plotly_plot is None:
        return None
    if not isinstance(topology, dict):
        return None

    nodes_dict = topology.get("nodes", {}) or {}
    edges_list = topology.get("edges", []) or []
    if not isinstance(nodes_dict, dict) or not nodes_dict:
        return None

    # Must have per-node state history to animate
    has_node_states = False
    for r in telemetry_rows:
        if isinstance(r, dict) and isinstance(r.get("node_states"), dict):
            has_node_states = True
            break
    if not has_node_states:
        return None

    G = nx.Graph()
    for nid, attrs in nodes_dict.items():
        G.add_node(str(nid), **(attrs or {}))
    for e in edges_list:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            a, b = str(e[0]), str(e[1])
            if a in G and b in G:
                G.add_edge(a, b)

    if G.number_of_nodes() == 0:
        return None

    # Layout
    pos = nx.spring_layout(G, seed=42)

    node_ids = list(G.nodes())
    node_x = [pos[n][0] for n in node_ids]
    node_y = [pos[n][1] for n in node_ids]

    # Edges trace
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", hoverinfo="none", line=dict(width=1))

    def state_to_val(s: str) -> int:
        s = (s or "S").upper()
        if s == "I":
            return 1
        if s == "R":
            return 2
        return 0

    # Build frames from telemetry
    frames = []
    slider_steps = []
    for i, row in enumerate(telemetry_rows):
        ns = row.get("node_states")
        if not isinstance(ns, dict):
            continue

        colors = [state_to_val(ns.get(n, "S")) for n in node_ids]

        frame = go.Frame(
            name=str(i),
            data=[
                edge_trace,
                go.Scatter(
                    x=node_x, y=node_y,
                    mode="markers+text",
                    text=node_ids,
                    textposition="top center",
                    hoverinfo="text",
                    hovertext=node_ids,
                    marker=dict(
                        size=14,
                        color=colors,
                        colorscale="Viridis",
                        cmin=0, cmax=2,
                        showscale=True,
                        colorbar=dict(title="State<br>0=S<br>1=I<br>2=R", thickness=14),
                    ),
                ),
            ],
        )
        frames.append(frame)

        slider_steps.append(dict(
            method="animate",
            args=[[str(i)], {"mode": "immediate", "frame": {"duration": 200, "redraw": True}, "transition": {"duration": 0}}],
            label=f"t={row.get('t', i)}"
        ))

    if not frames:
        return None

    # Initial node trace uses first frame
    init_node = frames[0].data[1]

    fig = go.Figure(data=[edge_trace, init_node], frames=frames)
    fig.update_layout(
        title="Topology Map (Malware Spread)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=50, b=20),
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            x=0.0, y=1.15,
            xanchor="left", yanchor="top",
            buttons=[
                dict(label="Play", method="animate",
                     args=[None, {"fromcurrent": True, "frame": {"duration": 200, "redraw": True}, "transition": {"duration": 0}}]),
                dict(label="Pause", method="animate",
                     args=[[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}]),
            ],
        )],
        sliders=[dict(active=0, pad={"t": 40}, steps=slider_steps)]
    )

    # IMPORTANT: include_plotlyjs=True here so the map always renders
    return plotly_plot(fig, include_plotlyjs=True, output_type="div")


def build_dashboard_html(run_dir: str, telemetry: list, kpis: dict, run_meta: Optional[dict], topology: Optional[dict]) -> str:
    attack_type = infer_attack_type(kpis, telemetry)

    t = [row.get("t") for row in telemetry]

    def series(key, default=0):
        return [row.get(key, default) for row in telemetry]

    plot_divs = []

    # --- MALWARE DASHBOARD ---
    if attack_type == "malware_spread":
        # 1) Topology animation (if possible)
        topo_div = build_topology_animation_div(topology, telemetry)
        if topo_div:
            plot_divs.append(topo_div)

        # 2) Counts plot (no plotly.js if topo_div already included it)
        include_js = False if topo_div else True
        fig_counts = line_fig(
            "Malware Spread: Node Counts",
            "Nodes",
            t,
            [
                ("susceptible", series("susceptible_nodes", 0)),
                ("infected", series("infected_nodes", 0)),
                ("recovered", series("recovered_nodes", 0)),
            ],
        )
        plot_divs.append(plotly_plot(fig_counts, include_plotlyjs=include_js, output_type="div"))

        fig_new = line_fig(
            "Malware Spread: New Infections",
            "New infections per step",
            t,
            [("new_infections", series("new_infections", 0))],
        )
        plot_divs.append(plotly_plot(fig_new, include_plotlyjs=False, output_type="div"))

    # --- HTTP FLOOD DASHBOARD (existing behaviour) ---
    else:
        fig_rps = line_fig(
            "Traffic (RPS)",
            "Requests per second",
            t,
            [
                ("incoming_rps", series("incoming_rps", 0)),
                ("served_rps", series("served_rps", 0)),
                ("dropped_rps", series("dropped_rps", 0)),
            ],
        )
        fig_queue = line_fig("Queue Size", "Queue", t, [("queue", series("queue", 0))])
        fig_latency = line_fig("Latency (ms)", "Milliseconds", t, [("latency_ms", series("latency_ms", 0))])

        plot_divs.append(plotly_plot(fig_rps, include_plotlyjs=True, output_type="div"))
        plot_divs.append(plotly_plot(fig_queue, include_plotlyjs=False, output_type="div"))
        plot_divs.append(plotly_plot(fig_latency, include_plotlyjs=False, output_type="div"))

    # Header / KPIs
    scenario_name = kpis.get("scenario_name", safe_get(run_meta or {}, "scenario_file", default="-"))
    target_service = safe_get(kpis, "attack", "target_service", default="-")

    # HTTP KPIs (if present)
    availability = kpis.get("availability_pct", "-")
    latency_kpi = kpis.get("peak_latency_ms", kpis.get("latency_ms", "-"))
    total_dropped = kpis.get("total_dropped", "-")

    # Malware KPIs (if present)
    peak_infected = kpis.get("peak_infected", kpis.get("peak_infected_nodes", "-"))
    total_infected_ever = kpis.get("total_infected_ever", kpis.get("total_infected", "-"))
    containment_time = kpis.get("containment_time_s", "-")

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

    if attack_type == "malware_spread":
        kpi_cards = f"""
        <div class="kpi-grid">
          <div class="kpi"><div class="label">Scenario</div><div class="value">{scenario_name}</div></div>
          <div class="kpi"><div class="label">Attack type</div><div class="value">{attack_type}</div></div>
          <div class="kpi"><div class="label">Peak infected</div><div class="value">{peak_infected}</div></div>
          <div class="kpi"><div class="label">Total infected (ever)</div><div class="value">{total_infected_ever}</div></div>
          <div class="kpi"><div class="label">Containment time (s)</div><div class="value">{containment_time}</div></div>
          <div class="kpi"><div class="label">Telemetry points</div><div class="value">{len(telemetry)}</div></div>
        </div>
        """
    else:
        kpi_cards = f"""
        <div class="kpi-grid">
          <div class="kpi"><div class="label">Attack type</div><div class="value">{attack_type}</div></div>
          <div class="kpi"><div class="label">Target service</div><div class="value">{target_service}</div></div>
          <div class="kpi"><div class="label">Availability (%)</div><div class="value">{availability}</div></div>
          <div class="kpi"><div class="label">Latency KPI (ms)</div><div class="value">{latency_kpi}</div></div>
          <div class="kpi"><div class="label">Total dropped</div><div class="value">{total_dropped}</div></div>
          <div class="kpi"><div class="label">Telemetry points</div><div class="value">{len(telemetry)}</div></div>
        </div>
        """

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
    code { background: #f4f4f4; padding: 2px 6px; border-radius: 6px; }
    """

    plots_html = "\n".join([f'<div class="section">{d}</div>' for d in plot_divs])

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

  {kpi_cards}
  {meta_line}

  {plots_html}

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

    if go is None or plotly_plot is None:
        print("ERROR: plotly is not installed in this environment. Fix: pip install plotly", file=sys.stderr)
        return 2

    run_dir = args.run_dir
    telemetry_path = os.path.join(run_dir, "telemetry.json")
    kpis_path = os.path.join(run_dir, "kpis.json")
    run_meta_path = os.path.join(run_dir, "run_meta.json")
    topology_path = os.path.join(run_dir, "topology.yml")

    if not os.path.exists(telemetry_path) or not os.path.exists(kpis_path):
        print("ERROR: Missing telemetry.json or kpis.json in run folder", file=sys.stderr)
        return 2

    telemetry = load_json(telemetry_path)
    kpis = load_json(kpis_path)
    run_meta = load_json(run_meta_path) if os.path.exists(run_meta_path) else None
    topology = try_load_yaml(topology_path)

    html = build_dashboard_html(run_dir, telemetry, kpis, run_meta, topology)

    out_path = args.out or os.path.join(run_dir, "dashboard.html")
    with open(out_path, "w") as f:
        f.write(html)

    print(f"Dashboard written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
