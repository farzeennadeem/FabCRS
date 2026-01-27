# NOTE: This is a staged copy for FabSim runs. Edit the root cyberrangesim.py instead.

import json
import yaml
import os
import time
from datetime import datetime, timezone
import argparse

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

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
        "duration": scenario.get("duration"),
        "status": "success"
    }

    # Write outputs
    with open(os.path.join(outdir, "kpis.json"), "w") as f:
        json.dump(kpis, f, indent=2)

    with open(os.path.join(outdir, "run_meta.json"), "w") as f:
        json.dump(run_meta, f, indent=2)

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