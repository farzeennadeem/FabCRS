## FabCRS

FabCRS is a Cyber Range Simulation (CRS) plugin for FabSim3 that automates cyberattack scenarios to help analyze network vulnerability and security defenses. It simulates realistic attack patterns (HTTP floods and lateral malware spread) on configurable topologies and generates interactive dashboards and security recommendations.

## Installation

First, install FabSim3 by following the [FabSim3 Getting Started Guide](https://fabsim3.readthedocs.io/en/latest/installation/).

### ⚠️ macOS Security Notice (Important)

If you are using macOS, **do NOT clone or install FabSim3/FabCRS inside**:

- Desktop  
- Documents  
- Downloads  

macOS applies additional security protections (e.g. TCC / sandboxing) to these directories. This can cause:

- Permission denied errors  
- Virtual environment execution failures  
- FabSim job execution issues  
- Python scripts being blocked  
- Unexpected security pop-ups

Once FabSim3 is set up and everything is configured for your device, install FabCRS from inside your FabSim3 directory:

```bash
fabsim localhost install_plugin:FabCRS
```

Install dependencies:

```bash
pip install -r plugins/FabCRS/requirements.txt
```

## Configuration

Configure machine paths by copying the template and editing with your details:

```bash
cd plugins/FabCRS
cp machines_FabCRS_user_template.yml machines_FabCRS_user.yml
# Edit machines_FabCRS_user.yml with your paths and username
```

Key paths to set:
- `local_results`: FabSim3 results directory
- `local_configs`: FabSim3 config_files directory  
- `home_path_template`: FabSim3 localhost_exe directory
- `virtual_env_path`: Path to your Python virtual environment
- `fabcrs_location`: Path to FabCRS plugin (usually `plugins/FabCRS`)

## Quick Start

Run a simulation for the HTTP flood scenario:

```bash
fabsim localhost run_crs:http_flood
```

Or test malware spread:

```bash
fabsim localhost run_crs:malware_spread
```

The simulation generates output files in `localhost_exe/FabSim/results/`. A run folder name is printed when the job completes (format: `run_DD_MM_YYYY_HHMMSS`).

## Main Commands

### run_crs

Run a cyber range simulation for a given scenario.

```bash
fabsim localhost run_crs:<scenario>
```

Scenarios:
- `http_flood` - DDoS attack on a web service
- `malware_spread` - Malware propagation through a network

Output files in the run folder:
- `run_meta.json` - Metadata and configuration
- `kpis.json` - Key performance indicators and attack metrics
- `telemetry.json` - Full simulation timeline events

### crs_generate_dashboard

Generate an interactive HTML dashboard visualizing simulation results.

```bash
fabsim localhost crs_generate_dashboard:<results_group>,run=<run_folder>
```

Example:

```bash
fabsim localhost crs_generate_dashboard:http_flood_localhost_1,run=run_27_02_2026_100000
```

Output:
- `dashboard.html` - Interactive visualization with graphs, timeline, and topology map

### crs_secure_advisor

Analyze results and provide security hardening recommendations.

**Tip: on Command-Line, press 'UP' key in terminal to auto-fill the command with previous arguments, then just change the method name from 'crs_generate_dashboard' to 'crs_secure_advisor'. **
```bash
fabsim localhost crs_secure_advisor:<results_group>,run=<run_folder>
```

Example:

```bash
fabsim localhost crs_secure_advisor:malware_spread_localhost_1,run=run_27_02_2026_100000
```

Output:
- `recommendations.md` - Hardening suggestions based on KPIs
- `patch.yml` - Configuration patch to improve defenses

## Scenarios

### HTTP Flood

Models a volumetric DDoS attack targeting a web service. The attack floods the service with requests, degrading availability.

Configuration file: `config_files/http_flood/`

Key parameters in `scenario.yml`:
- `service_model.capacity_rps` - Request handling capacity
- `service_model.queue_size` - Buffer size for pending requests
- `attack.rate_rps` - Attack traffic rate
- `defences.rate_limit.enabled` - Enable rate limiting defense

### Malware Spread

Simulates malware propagation across a network graph. Infected nodes can spread infection to neighbors based on connectivity and susceptibility.

Configuration file: `config_files/malware_spread/`

Key parameters in `scenario.yml`:
- `nodes` - Network topology nodes
- `defences.patching.enabled` - Enable defensive patching
- `defences.segmentation.enabled` - Enable network segmentation
- `attack.infection_spread_rate` - Probability of infection spread

## Configuration Files

Each scenario has:

- `topology.yml` - Network graph definition (nodes and connections)
- `scenario.yml` - Attack parameters, defenses, and KPI targets

Edit these files to customize scenarios for your testing needs.

## Testing

Run the test suite to verify installation:

```bash
pytest plugins/FabCRS/tests/ -v
```

Tests cover all main commands and scenarios. Full test documentation is in `tests/README.md`.

## Workflow Example

Complete workflow from simulation to analysis:

```bash
# 1. Run simulation
fabsim localhost run_crs:http_flood

# Wait for output, note the run folder (run_DD_MM_YYYY_HHMMSS)

# 2. Generate dashboard
fabsim localhost crs_generate_dashboard:http_flood_localhost_1,run=run_DD_MM_YYYY_HHMMSS

# 3. Get security recommendations
fabsim localhost crs_secure_advisor:http_flood_localhost_1,run=run_DD_MM_YYYY_HHMMSS

# 4. View results
open localhost_exe/FabSim/results/http_flood_localhost_1/run_DD_MM_YYYY_HHMMSS/dashboard.html
cat localhost_exe/FabSim/results/http_flood_localhost_1/run_DD_MM_YYYY_HHMMSS/recommendations.md
```

## File Structure

```
FabCRS/
├── FabCRS.py                 # Main plugin commands
├── cyberrangesim.py          # Simulation engine
├── gen_db.py                 # Dashboard generator
├── secureadvisor.py          # Security recommendation engine
├── requirements.txt          # Python dependencies
├── config_files/
│   ├── http_flood/           # HTTP flood scenario
│   │   ├── scenario.yml
│   │   └── topology.yml
│   └── malware_spread/       # Malware spread scenario
│       ├── scenario.yml
│       └── topology.yml
├── templates/
│   ├── crs_run               # Simulation execution template
│   ├── crs_db                # Dashboard generation template
│   └── crs_secureadvisor     # Advisor execution template
└── tests/
    └── test_fabcrs.py        # Comprehensive test suite
```

## Troubleshooting

**Plugin not found**

Reinstall the plugin:
```bash
fabsim localhost install_plugin:FabCRS
```

**Missing dependencies**

Install all requirements:
```bash
pip install -r plugins/FabCRS/requirements.txt
```

**Run folder not found for dashboard**

Check the results directory:
```bash
ls localhost_exe/FabSim/results/
```

Use the correct results group name (format: `<scenario>_<machine>_<index>`).

**Virtual environment path issues**

Verify your `machines_FabCRS_user.yml` has correct paths:
```bash
cat plugins/FabCRS/machines_FabCRS_user.yml
```

## License

FabCRS is part of the FabSim3 toolkit and follows the same BSD 3-Clause license.