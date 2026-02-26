import json
import yaml
import os
import time
from datetime import datetime, timezone
import argparse
import random

try:
    import networkx as nx
except ImportError:
    nx = None

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)
    
def _as_bool(x, default=False):
    """Safe bool parse: supports bool, int, and common strings."""
    if x is None:
        return default
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return bool(x)
    if isinstance(x, str):
        v = x.strip().lower()
        if v in ("true", "yes", "y", "1", "on"):
            return True
        if v in ("false", "no", "n", "0", "off"):
            return False
    return default

def _build_nx_graph(topology):
    """Build a NetworkX graph from topology.yml.

    Expected topology format (current CRS style):
      nodes: { node_id: {attr: val, ...}, ... }
      edges: [ [a, b], [b, c], ... ]

    Returns an undirected Graph by default.
    """
    if nx is None:
        raise RuntimeError("NetworkX is required for malware_spread scenarios (pip install networkx).")

    topo = topology if isinstance(topology, dict) else {}
    nodes = topo.get("nodes", {}) or {}
    edges = topo.get("edges", []) or []

    G = nx.Graph()
    for node_id, attrs in nodes.items():
        G.add_node(str(node_id), **(attrs or {}))
    for e in edges:
        if not e or len(e) < 2:
            continue
        a, b = str(e[0]), str(e[1])
        G.add_edge(a, b)
    return G

def compute_kpis_from_telemetry_malware_spread(telemetry, scenario):
    """Compute end-of-run KPIs for malware spread telemetry."""
    sim_cfg = (scenario or {}).get("sim", {}) or {}
    timestep_s = int(sim_cfg.get("timestep_s", 1)) or 1

    if not telemetry:
        return {
            "attack": (scenario or {}).get("attack", {}) or {},
            "total_nodes": 0,
            "total_infected_ever": 0,
            "peak_infected": 0,
            "time_to_peak_s": 0,
            "final_infected": 0,
            "final_recovered": 0,
            "containment_time_s": None,
        }

    infected_series = [int(row.get("infected_nodes", 0)) for row in telemetry]
    new_inf_series = [int(row.get("new_infections", 0)) for row in telemetry]
    recovered_series = [int(row.get("recovered_nodes", 0)) for row in telemetry]
    total_nodes = int(telemetry[0].get("total_nodes", 0))

    peak_infected = max(infected_series)
    peak_idx = infected_series.index(peak_infected)
    time_to_peak_s = int(telemetry[peak_idx].get("t", peak_idx * timestep_s))

    final_infected = infected_series[-1]
    final_recovered = recovered_series[-1]

    # Infected-ever estimate: total_nodes - min susceptible
    susceptible_series = [int(row.get("susceptible_nodes", 0)) for row in telemetry]
    total_infected_ever = total_nodes - min(susceptible_series) if total_nodes > 0 else 0

    # containment time: first time after detection where new infections stay at 0
    attack_cfg = (scenario or {}).get("attack", {}) or {}
    detect_delay = int(attack_cfg.get("detection_delay_s", 0) or 0)
    containment_time = None
    for row in telemetry:
        t = int(row.get("t", 0))
        if t < detect_delay:
            continue
        if int(row.get("new_infections", 0)) == 0:
            # require it to remain zero thereafter
            idx = telemetry.index(row)
            if all(int(r.get("new_infections", 0)) == 0 for r in telemetry[idx:]):
                containment_time = t
                break

    return {
        "attack": attack_cfg,
        "total_nodes": total_nodes,
        "total_infected_ever": int(total_infected_ever),
        "peak_infected": int(peak_infected),
        "time_to_peak_s": int(time_to_peak_s),
        "final_infected": int(final_infected),
        "final_recovered": int(final_recovered),
        "containment_time_s": containment_time,
    }

def generate_telemetry_malware_spread(topology, scenario):
    """Worm-like malware spread on a topology graph (MVP).

    Telemetry rows (per timestep) include:
      t, phase, total_nodes, susceptible_nodes, infected_nodes, recovered_nodes, new_infections
    """
    scenario = scenario if isinstance(scenario, dict) else {}
    sim_cfg = scenario.get("sim", {}) or {}
    attack_cfg = scenario.get("attack", {}) or {}
    def_cfg = scenario.get("defences", {}) or {}

    duration_s = sim_cfg.get("duration_s", scenario.get("duration", 60))
    duration_s = int(duration_s)
    timestep_s = int(sim_cfg.get("timestep_s", 1)) or 1
    seed = int(scenario.get("seed", 0) or 0)
    rng = random.Random(seed)

    G = _build_nx_graph(topology)
    nodes = list(G.nodes())
    total_nodes = len(nodes)

    beta = float(attack_cfg.get("infection_probability", 0.2))
    detect_delay_s = int(attack_cfg.get("detection_delay_s", 0) or 0)

    # optional recovery (post-detection containment / cleaning)
    recovery_rate = attack_cfg.get("recovery_rate", None)
    recovery_rate = float(recovery_rate) if recovery_rate is not None else 0.0

    # patching defence: reduces susceptibility on patched nodes
    patch_cfg = def_cfg.get("patching", {}) or {}
    patch_enabled = _as_bool(patch_cfg.get("enabled", False), default=False)
    susceptibility_reduction_pct = float(patch_cfg.get("susceptibility_reduction_pct", 0.0))
    patched_nodes = set(str(x) for x in (patch_cfg.get("patched_nodes", []) or []))

    # also respect topology node attribute: patched: true
    for n, attrs in G.nodes(data=True):
        if _as_bool(attrs.get("patched", False), default=False):
            patched_nodes.add(str(n))

    # segmentation defence: block specific edges after detection
    seg_cfg = def_cfg.get("segmentation", {}) or {}
    seg_enabled = _as_bool(seg_cfg.get("enabled", False), default=False)
    blocked_edges = set()
    for e in (seg_cfg.get("blocked_edges", []) or []):
        if e and len(e) >= 2:
            a, b = str(e[0]), str(e[1])
            blocked_edges.add(tuple(sorted((a, b))))

    # initial infected: list of node ids, or integer count
    init = attack_cfg.get("initial_infected", 1)
    if isinstance(init, list):
        initial_infected = [str(x) for x in init]
    else:
        try:
            k = int(init)
        except Exception:
            k = 1
        k = max(1, min(k, total_nodes)) if total_nodes > 0 else 0
        initial_infected = rng.sample(nodes, k) if k > 0 else []

    state = {n: "S" for n in nodes}
    for n in initial_infected:
        if n in state:
            state[n] = "I"

    telemetry = []

    for t in range(0, duration_s, timestep_s):
        post_detect = t >= detect_delay_s
        phase = "post_detection" if post_detect else "pre_detection"

        # spread
        newly_infected = set()
        infected_now = [n for n, s in state.items() if s == "I"]

        for src in infected_now:
            for dst in G.neighbors(src):
                if state.get(dst) != "S":
                    continue
                if seg_enabled and post_detect:
                    edge_key = tuple(sorted((str(src), str(dst))))
                    if edge_key in blocked_edges:
                        continue

                p = beta
                if patch_enabled and str(dst) in patched_nodes:
                    p *= max(0.0, (1.0 - susceptibility_reduction_pct / 100.0))

                if rng.random() < p:
                    newly_infected.add(dst)

        for n in newly_infected:
            state[n] = "I"

        # recovery/cleanup after detection
        if post_detect and recovery_rate > 0.0:
            for n in list(state.keys()):
                if state[n] == "I" and rng.random() < recovery_rate:
                    state[n] = "R"

        susceptible = sum(1 for s in state.values() if s == "S")
        infected = sum(1 for s in state.values() if s == "I")
        recovered = sum(1 for s in state.values() if s == "R")

        telemetry.append({
            "t": int(t),
            "phase": phase,
            "total_nodes": int(total_nodes),
            "susceptible_nodes": int(susceptible),
            "infected_nodes": int(infected),
            "recovered_nodes": int(recovered),
            "new_infections": int(len(newly_infected)),
            "node_states": dict(state),
        })

    return telemetry

def compute_kpis_from_telemetry(telemetry, scenario):
    # Dispatch KPIs based on scenario attack type
    attack_type = str((scenario or {}).get("attack", {}).get("type", "")).lower()
    if attack_type in ("malware_spread", "worm_spread", "malware_worm"):
        return compute_kpis_from_telemetry_malware_spread(telemetry, scenario)

    sim_cfg = scenario.get("sim", {})
    timestep_s = int(sim_cfg.get("timestep_s", 1))

    total_in = sum(row["incoming_rps"] * timestep_s for row in telemetry)
    total_served = sum(row["served_rps"] * timestep_s for row in telemetry)
    total_dropped = sum(row["dropped_rps"] * timestep_s for row in telemetry)

    availability_pct = 100.0 if total_in <= 0 else (100.0 * total_served / total_in)

    #latency_kpi_ms = max latency OR p95 latency (worst-case experience for 95% of users while filtering out extreme 'one-time' spikes)
    latencies = [row["latency_ms"] for row in telemetry] or [0.0]
    latencies_sorted = sorted(latencies)
    p95_idx = int(0.95 * (len(latencies_sorted) - 1))
    latency_kpi_ms = latencies_sorted[p95_idx]

    attack_cfg = scenario.get("attack", {})
    return {
        "attack": attack_cfg,
        "availability_pct": round(availability_pct, 3),
        "latency_kpi_ms": round(latency_kpi_ms, 3),
        "total_dropped": round(total_dropped, 3),
        "total_incoming": round(total_in, 3),
        "total_served": round(total_served, 3),
    }


def generate_telemetry(topology, scenario):
    """
    Minimal time-series output for MVP
    Produces timestep rows for dashboard plotting later
    All tunables live in scenario.yml
    """
    # Dispatch telemetry generation based on scenario attack type
    attack_type = str((scenario or {}).get("attack", {}).get("type", "")).lower()
    if attack_type in ("malware_spread", "worm_spread", "malware_worm"):
        return generate_telemetry_malware_spread(topology, scenario)

    scenario = scenario if isinstance(scenario, dict) else {}

    sim_cfg = scenario.get("sim", {}) or {}
    attack_cfg = scenario.get("attack", {}) or {}
    svc_cfg = scenario.get("service_model", {}) or {}
    def_cfg = scenario.get("defences", {}) or {}
    lat_cfg = scenario.get("latency_model", {}) or {}

    # sim duration/timestep
    duration_s = sim_cfg.get("duration_s", None)
    if duration_s is None:
        duration_s = scenario.get("duration", 60) #fallback to legacy
    duration_s = int(duration_s)
    timestep_s = int(sim_cfg.get("timestep_s", 1))
    if timestep_s <= 0:
        timestep_s = 1

    #workload parameters
    base_load_rps = float(svc_cfg.get("base_load_rps", 0.0))
    attack_rps = float(attack_cfg.get("rps", 0.0))

    # attack window + ramping up/down attack
    attack_start_s = int(attack_cfg.get("start_s", 0))
    attack_end_s = int(attack_cfg.get("end_s", duration_s))
    ramp_up_s = int(attack_cfg.get("ramp_up_s", 0))       # 0 = no ramp
    ramp_down_s = int(attack_cfg.get("ramp_down_s", 0))   # 0 = no ramp


    burst_cfg = attack_cfg.get("burstiness", {}) or {} #empty dict. if no value given in scenario.yml -> sets default val later
    burst_mode = str(burst_cfg.get("mode", "constant")).lower()
    pulse_on_s = int(burst_cfg.get("pulse_on_s", 10))
    pulse_off_s = int(burst_cfg.get("pulse_off_s", 10))

    #service model parameters (simple queue plus capacity)
    capacity_rps = float(svc_cfg.get("capacity_rps", 1000))
    queue_size = int(svc_cfg.get("queue_size", 100))
    queue = float(svc_cfg.get("initial_queue", 0.0))

    #defences
    rate_limit_cfg = def_cfg.get("rate_limit", {}) or {}
    rl_enabled = _as_bool(rate_limit_cfg.get("enabled", False), default=False)
    rl_limit_rps = float(rate_limit_cfg.get("limit_rps", capacity_rps))

    scrubbing_cfg = def_cfg.get("scrubbing", {}) or {}
    scrub_enabled = _as_bool(scrubbing_cfg.get("enabled", False), default=False)
    scrub_pct = float(scrubbing_cfg.get("reduction_pct", 0))

    base_latency_ms = float(lat_cfg.get("base_latency_ms", 20.0))
    latency_k = float(lat_cfg.get("latency_k", 80.0))
    max_latency_ms = lat_cfg.get("max_latency_ms", None)
    if max_latency_ms is not None:
        max_latency_ms = float(max_latency_ms)

    telemetry = []

    def _ramp_factor(t, start, end, up_s, down_s):
        """0..1 factor with optional ramp up/down inside [start,end]."""
        if t < start or t >= end:
            return 0.0
        # ramp up
        if up_s > 0 and t < start + up_s:
            return max(0.0, min(1.0, (t - start) / float(up_s)))
        # ramp down
        if down_s > 0 and t >= end - down_s:
            return max(0.0, min(1.0, (end - t) / float(down_s)))
        return 1.0

    for t in range(0, duration_s, timestep_s):
        # baseline attack presence (start/end + ramp)
        a_fac = _ramp_factor(t, attack_start_s, attack_end_s, ramp_up_s, ramp_down_s)
        effective_attack = attack_rps * a_fac

        # burstiness modulation (on top of ramp/window)
        if burst_mode == "pulse" and effective_attack > 0.0:
            period = max(1, pulse_on_s + pulse_off_s)
            in_on = (t % period) < pulse_on_s
            effective_attack = effective_attack if in_on else 0.0

        # scrubbing reduces attack portion
        if scrub_enabled:
            effective_attack *= (1.0 - scrub_pct / 100.0)

        incoming = base_load_rps + effective_attack

        # rate limiting caps total incoming
        if rl_enabled:
            incoming = min(incoming, rl_limit_rps)

        # serve from incoming + queue backlog
        served = min(capacity_rps, incoming + queue)

        # update queue (remaining demand)
        new_queue = max(0.0, (incoming + queue) - served)

        dropped = 0.0
        if queue_size > 0 and new_queue > queue_size:
            dropped = new_queue - queue_size
            new_queue = float(queue_size)

        queue = new_queue

        # latency rises with queue pressure
        pressure = 0.0 if capacity_rps <= 0 else (queue / max(1.0, capacity_rps))
        latency_ms = base_latency_ms + latency_k * pressure
        if max_latency_ms is not None:
            latency_ms = min(latency_ms, max_latency_ms)

        telemetry.append({
            "t": t,
            "incoming_rps": round(incoming, 3),
            "served_rps": round(served, 3),
            "dropped_rps": round(dropped, 3),
            "queue": round(queue, 3),
            "latency_ms": round(latency_ms, 3),
        })

    return telemetry        

def run(topology_path, scenario_path, outdir):
    os.makedirs(outdir, exist_ok=True)

    topology = load_yaml(topology_path)
    scenario = load_yaml(scenario_path)  

    run_meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topology_file": topology_path,
        "scenario_file": scenario_path,
        "duration": scenario.get("duration", scenario.get("sim", {}).get("duration_s")),
        "status": "success"
    }

    # Generate telemetry
    telemetry = generate_telemetry(topology, scenario)

    # Compute KPIs from telemetry
    kpis = compute_kpis_from_telemetry(telemetry, scenario)

    # Write outputs
    with open(os.path.join(outdir, "kpis.json"), "w") as f:
        json.dump(kpis, f, indent=2)

    with open(os.path.join(outdir, "run_meta.json"), "w") as f:
        json.dump(run_meta, f, indent=2)

    with open(os.path.join(outdir, "telemetry.json"), "w") as f:
        json.dump(telemetry, f, indent=2)

    print(f"Run complete. Outputs written to {outdir}")

if __name__ == "__main__":
    # This section was used when we ran this file directly for testing.
    '''
    run(
        "examples/topology.yml",
        "examples/scenario.yml",
        "outputs/test_run"
        
        "config_files/http_flood/topology.yml",
        "config_files/http_flood/scenario.yml",
        "outputs/test_run"
    )
    '''   

    # Command line argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()
    run(args.topology, args.scenario, args.outdir)