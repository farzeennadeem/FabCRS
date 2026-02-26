# FabCRS Test Suite

Comprehensive test suite for FabCRS plugin covering all main tasks and scenarios.

## Test Coverage

### 1. Plugin Installation
- Tests FabCRS plugin installation via FabSim3

### 2. Simulation Execution (`run_crs`)
- **http_flood scenario**: Tests HTTP flood attack simulation
- **malware_spread scenario**: Tests malware propagation simulation
- Verifies output files: `run_meta.json`, `kpis.json`, `telemetry.json`

### 3. Dashboard Generation (`crs_generate_dashboard`)
- Tests dashboard HTML generation for each scenario
- Verifies `dashboard.html` creation with interactive visualizations

### 4. Security Advisor (`crs_secure_advisor`)
- Tests security recommendation generation
- Verifies `recommendations.md` and `patch.yml` creation

### 5. Integration Tests
- Full workflow testing: simulation → dashboard → advisor
- End-to-end verification for each scenario

## Prerequisites

1. **FabSim3 installed** with FabCRS plugin
2. **Python dependencies**:
   ```bash
   pip install pytest>=7.0
   pip install -r requirements.txt
   ```
3. **localhost machine configured** in FabSim3

## Running Tests

### Run all tests
From FabSim3 root directory:
```bash
pytest plugins/FabCRS/tests/ -v
```

### Run specific test classes
```bash
# Only installation tests
pytest plugins/FabCRS/tests/test_fabcrs.py::TestFabCRSInstallation -v

# Only simulation tests
pytest plugins/FabCRS/tests/test_fabcrs.py::TestRunCRS -v

# Only dashboard tests
pytest plugins/FabCRS/tests/test_fabcrs.py::TestDashboardGeneration -v

# Only advisor tests
pytest plugins/FabCRS/tests/test_fabcrs.py::TestSecureAdvisor -v

# Integration tests
pytest plugins/FabCRS/tests/test_fabcrs.py::TestIntegration -v
```

### Run tests for specific scenario
```bash
# HTTP flood scenario only
pytest plugins/FabCRS/tests/test_fabcrs.py -k "http_flood" -v

# Malware spread scenario only
pytest plugins/FabCRS/tests/test_fabcrs.py -k "malware_spread" -v
```

### Generate coverage report
```bash
pytest plugins/FabCRS/tests/ --cov=plugins/FabCRS --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py              # Package marker
├── conftest.py              # Pytest configuration and fixtures
├── test_fabcrs.py           # Main test suite
└── README.md                # This file
```

## Expected Test Duration

- **Installation**: ~5 seconds
- **Simulation tests**: ~30-60 seconds (per scenario)
- **Dashboard tests**: ~15-30 seconds (per scenario)
- **Advisor tests**: ~10-20 seconds (per scenario)
- **Integration tests**: ~60-90 seconds (per scenario)

**Total estimated time**: 5-10 minutes for complete test suite

## Troubleshooting

### Tests fail with "FabCRS plugin not found"
```bash
cd FabSim3
fabsim localhost install_plugin:FabCRS
```

### Tests fail with "NetworkX not installed"
```bash
pip install networkx plotly pyyaml
```

### Tests fail with "localhost not configured"
Ensure `machines_user.yml` in FabSim3 includes localhost configuration.

### Clean up test results
```bash
# Remove generated test results
rm -rf localhost_exe/FabSim/results/*_localhost_1/
```

## CI/CD Integration

Add to your CI pipeline:
```yaml
- name: Run FabCRS tests
  run: |
    cd FabSim3
    pytest plugins/FabCRS/tests/ -v --junitxml=test-results.xml
```

## Contributing

When adding new scenarios or tasks:
1. Add corresponding test cases to `test_fabcrs.py`
2. Update this README with new test descriptions
3. Ensure all tests pass before submitting PR
