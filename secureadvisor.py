import argparse
import json
import os
import yaml
from typing import Dict, Any, List

def load_json(path: str) -> Dict:
    with open(path, "r") as f:
        return json.load(f)

def load_yaml(path: str) -> Dict:
    if not os.path.exists(path): return {}
    with open(path, "r") as f:
        return yaml.safe_load(f)

def analyze_http_flood(kpis: Dict, scenario: Dict) -> (List[str], Dict):
    recommendations = []
    patch = {"service_model": {}, "defences": {}}
    
    availability = kpis.get("availability_pct", 100)
    total_dropped = kpis.get("total_dropped", 0)
    capacity = scenario.get("service_model", {}).get("capacity_rps", 1000)
    queue_size = scenario.get("service_model", {}).get("queue_size", 100)
    
    # Rule 1: Capacity Bottleneck
    if availability < 95:
        new_capacity = int(capacity * 1.3)
        recommendations.append(f"- Increase capacity_rps to {new_capacity} [Availability was only {availability}% due to server exhaustion].")
        patch["service_model"]["capacity_rps"] = new_capacity

    # Rule 2: Queue Overflow
    if total_dropped > 0:
        new_queue = int(queue_size * 1.5)
        recommendations.append(f"- Increase queue_size to {new_queue} [Detected {total_dropped} dropped requests due to full buffer].")
        patch["service_model"]["queue_size"] = new_queue

    # Rule 3: Missing Defences
    if availability < 100 and not scenario.get("defences", {}).get("rate_limit", {}).get("enabled"):
        recommendations.append("- Enable rate_limiting [Unfiltered attack traffic is reaching the service].")
        patch["defences"]["rate_limit"] = {"enabled": True, "limit_rps": capacity}

    return recommendations, patch

def analyze_malware(kpis: Dict, scenario: Dict) -> (List[str], Dict):
    recommendations = []
    patch = {"defences": {}}
    
    peak_infected = kpis.get("peak_infected", 0)
    total_nodes = kpis.get("total_nodes", 1)
    infection_pct = (peak_infected / total_nodes) * 100
    
    # Rule 1: High Infection Spread
    if infection_pct > 30:
        recommendations.append("- Enable node patching [Over 30% of your network was compromised].")
        patch["defences"]["patching"] = {"enabled": True, "susceptibility_reduction_pct": 80}

    # Rule 2: Lack of Segmentation
    if not scenario.get("defences", {}).get("segmentation", {}).get("enabled"):
        recommendations.append("- Enable network segmentation [Lateral movement is currently unrestricted post-detection].")
        patch["defences"]["segmentation"] = {"enabled": True}

    return recommendations, patch

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()

    # Load data
    kpis = load_json(os.path.join(args.run_dir, "kpis.json"))
    scenario = load_yaml(os.path.join(args.run_dir, "scenario.yml"))
    
    attack_type = kpis.get("attack", {}).get("type", "unknown")
    
    if "malware" in attack_type:
        recs, patch = analyze_malware(kpis, scenario)
    else:
        recs, patch = analyze_http_flood(kpis, scenario)

    # Output 1: recommendations.md
    with open(os.path.join(args.run_dir, "recommendations.md"), "w") as f:
        f.write("# SecureAdvisor Recommendations\n\n")
        if recs:
            f.write("\n".join(recs))
        else:
            f.write("Your current configuration is optimal for this scenario.")

    # Output 2: patch.yml
    with open(os.path.join(args.run_dir, "patch.yml"), "w") as f:
        f.write(
            "# Paste this in to FabSim3 > plugins > FabCRS > config_files > "
            "(scenario name) > scenario.yml, replacing the text in the relevant places.\n"
        )
        yaml.dump(patch, f)

    print(f"SecureAdvisor finished. Files written to {args.run_dir}")

if __name__ == "__main__":
    main()