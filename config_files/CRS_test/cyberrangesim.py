# NOTE: Edit the root cyberrangesim.py if you find this in the config folder
#MAIN 

import json
import yaml
import os
import time
from datetime import datetime, timezone
import argparse

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)
    
def generate_telemetry(topology, scenario):
    """
    Minimal time-series output for MVP.
    Produces timestep rows for dashboard plotting later.
    """
    sim_cfg = scenario.get("sim", {}) if isinstance(scenario, dict) else {}
    attack_cfg = scenario.get("attack", {}) if isinstance(scenario, dict) else {}
    svc_cfg = scenario.get("service_model", {}) if isinstance(scenario, dict) else {}
    def_cfg = scenario.get("defences", {}) if isinstance(scenario, dict) else {}

    # duration/timestep (supports both sim.duration or legacy duration)
    duration_s = sim_cfg.get("duration_s", None)
    if duration_s is None:
        duration_s = scenario.get("duration", 60) #fallback to legacy
    duration_s = int(duration_s)
    timestep_s = int(sim_cfg.get("timestep_s", 1))

    #workload parameters
    base_load_rps = float(svc_cfg.get("base_load_rps", 0))
    attack_rps = float(attack_cfg.get("rps", 0))

    burst_cfg = attack_cfg.get("burstiness", {}) if isinstance(attack_cfg, dict) else {}
    burst_mode = str(burst_cfg.get("mode", "constant")).lower()
    pulse_on_s = int(burst_cfg.get("pulse_on_s", 10))
    pulse_off_s = int(burst_cfg.get("pulse_off_s", 10))

    #service model parameters (simple queue plus capacity)
    capacity_rps = float(svc_cfg.get("capacity_rps", 1000))
    queue_size = int(svc_cfg.get("queue_size", 100))
    queue = 0.0

    #defences (can be refined later as they are simple for now)
    rate_limit_cfg = def_cfg.get("rate_limit", {}) if isinstance(def_cfg, dict) else {}
    rl_enabled = bool(rate_limit_cfg.get("enabled", False))
    rl_limit_rps = float(rate_limit_cfg.get("limit_rps", capacity_rps))

    scrubbing_cfg = def_cfg.get("scrubbing", {}) if isinstance(def_cfg, dict) else {}
    scrub_enabled = bool(scrubbing_cfg.get("enabled", False))
    scrub_pct = float(scrubbing_cfg.get("scrub_pct", 0))

    #latency model (kept simple to create sensible curve)
    base_latency_ms = 20.0
    latency_k = 80.0

    telemetry = []

    for t in range(0, duration_s, timestep_s):
        #burstiness
        effective_attack = attack_rps
        if burst_mode == "pulse":
             period = max(1, pulse_on_s + pulse_off_s)
             in_on = (t % period) < pulse_on_s
             effective_attack = attack_rps if in_on else 0.0

        #scrubbing reduces attack portion
        if scrub_enabled:
            effective_attack = effective_attack * (1.0 - scrub_pct / 100.0)

        incoming = base_load_rps + effective_attack

        #rate limiting caps total incoming
        if rl_enabled:
            incoming = min(incoming, rl_limit_rps)

        #serve from incoming + queue backlog
        served = min(capacity_rps, incoming + queue)

        #update queue (remaining demand)
        new_queue = max(0.0, (incoming + queue) - served)

        dropped = 0.0
        if queue_size > 0 and new_queue > queue_size:
            dropped = new_queue - queue_size
            new_queue = queue_size

        queue = new_queue

        pressure = 0.0 if capacity_rps <= 0 else (queue / max(1.0, capacity_rps))
        latency_ms = base_latency_ms + latency_k * pressure

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

    # Placeholder simulation
    start_time = time.time()

    kpis = {
        "attack": scenario.get("attack"),
        "availability_pct": 100.0,
        "latency_ms": 0,
        "notes": "Dummy run – no simulation yet"
    }

    run_meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topology_file": topology_path,
        "scenario_file": scenario_path,
        "duration": scenario.get("duration", scenario.get("sim", {}).get("duration_s")),
        "status": "success"
    }

    # Generate telemetry (time series)
    telemetry = generate_telemetry(topology, scenario)

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