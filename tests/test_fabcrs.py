"""
FabCRS Test Suite

Tests all main FabCRS tasks and scenarios:
- Plugin installation
- Simulation execution (run_crs) for all scenarios
- Dashboard generation (crs_generate_dashboard)
- Security advisor (crs_secure_advisor)

Run from FabSim3 root directory:
    pytest plugins/FabCRS/tests/test_fabcrs.py -v
"""

import os
import sys
import subprocess
import pytest
import re


# Helper function to extract run folder from command output
def extract_run_folder(output: str, results_group: str) -> str:
    """
    Extract the run folder name from command output.
    Expected pattern: run_DD_MM_YYYY_HHMMSS
    """
    # Look for patterns like: run_26_02_2026_210519
    pattern = r'run_\d{2}_\d{2}_\d{4}_\d{6}'
    matches = re.findall(pattern, output)
    if matches:
        return matches[-1]  # Return the last match (most recent)
    return None


@pytest.fixture
def execute_cmd(request):
    """Execute a FabSim command and return output."""
    raw_cmd = request.param.strip()

    # Replace 'fabsim' with full path
    cmd_parts = raw_cmd.split()
    if cmd_parts and cmd_parts[0] == "fabsim":
        fabsim_path = os.path.join(os.getcwd(), "fabsim", "bin", "fabsim")
        cmd_parts[0] = fabsim_path
        cmd = " ".join(cmd_parts)
    else:
        cmd = raw_cmd

    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = proc.communicate()
        output = stdout.decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while executing '{cmd}': {e}")

    if proc.returncode != 0:
        print(f"Command output:\n{output}")
        raise RuntimeError(
            f"\njob execution encountered an error (return code {proc.returncode})"
            f"\nwhile executing: '{cmd}'"
            f"\n\nOutput:\n{output}"
        )

    yield output
    proc.terminate()


class TestFabCRSInstallation:
    """Test FabCRS plugin installation."""

    @pytest.mark.parametrize(
        "execute_cmd,search_for",
        [
            (
                "fabsim localhost install_plugin:FabCRS",
                "FabCRS plugin installed",
            ),
        ],
        indirect=["execute_cmd"],
        ids=["FabCRS installation"],
    )
    def test_install_plugin(self, execute_cmd, search_for):
        """Test that FabCRS plugin installs successfully."""
        output = execute_cmd
        assert search_for in output or "already installed" in output.lower()


class TestRunCRS:
    """Test run_crs command for all scenarios."""

    @pytest.mark.parametrize(
        "execute_cmd,scenario_name,success_message",
        [
            (
                "fabsim localhost run_crs:http_flood",
                "http_flood",
                "CRS job finished",
            ),
            (
                "fabsim localhost run_crs:malware_spread",
                "malware_spread",
                "CRS job finished",
            ),
        ],
        indirect=["execute_cmd"],
        ids=["http_flood_simulation", "malware_spread_simulation"],
    )
    def test_run_crs_scenarios(self, execute_cmd, scenario_name, success_message):
        """Test that CRS simulations complete successfully for each scenario."""
        output = execute_cmd
        assert success_message in output, f"Expected '{success_message}' in output"
        
        # Verify that a run folder was created
        run_folder = extract_run_folder(output, f"{scenario_name}_localhost_1")
        assert run_folder is not None, "Run folder should be created"

        # Verify output files exist in results directory
        results_group = f"{scenario_name}_localhost_1"
        results_path = os.path.join(
            os.getcwd(),
            "localhost_exe",
            "FabSim",
            "results",
            results_group,
            run_folder
        )
        
        # Check for expected output files
        expected_files = ["run_meta.json", "kpis.json", "telemetry.json"]
        for expected_file in expected_files:
            file_path = os.path.join(results_path, expected_file)
            assert os.path.exists(file_path), f"{expected_file} should exist in {results_path}"


class TestDashboardGeneration:
    """Test crs_generate_dashboard for all scenarios."""

    @pytest.fixture(scope="class")
    def scenario_runs(self):
        """
        Run simulations first to generate data for dashboard tests.
        Returns dict mapping scenario names to their run folders.
        """
        runs = {}
        scenarios = ["http_flood", "malware_spread"]
        
        for scenario in scenarios:
            cmd = f"{os.path.join(os.getcwd(), 'fabsim', 'bin', 'fabsim')} localhost run_crs:{scenario}"
            proc = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            stdout, _ = proc.communicate()
            output = stdout.decode("utf-8")
            
            if proc.returncode == 0:
                results_group = f"{scenario}_localhost_1"
                run_folder = extract_run_folder(output, results_group)
                if run_folder:
                    runs[scenario] = {
                        "run_folder": run_folder,
                        "results_group": results_group
                    }
        
        return runs

    @pytest.mark.parametrize(
        "scenario_name",
        ["http_flood", "malware_spread"],
        ids=["http_flood_dashboard", "malware_spread_dashboard"],
    )
    def test_generate_dashboard(self, scenario_runs, scenario_name):
        """Test dashboard generation for each scenario."""
        if scenario_name not in scenario_runs:
            pytest.skip(f"No run data available for {scenario_name}")
        
        run_info = scenario_runs[scenario_name]
        results_group = run_info["results_group"]
        run_folder = run_info["run_folder"]
        
        cmd = (
            f"{os.path.join(os.getcwd(), 'fabsim', 'bin', 'fabsim')} localhost "
            f"crs_generate_dashboard:{results_group},run={run_folder}"
        )
        
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = proc.communicate()
        output = stdout.decode("utf-8")
        
        assert proc.returncode == 0, f"Dashboard generation failed: {output}"
        assert "Dashboard written" in output, "Expected 'Dashboard written' in output"
        
        # Verify dashboard.html was created
        dashboard_path = os.path.join(
            os.getcwd(),
            "localhost_exe",
            "FabSim",
            "results",
            results_group,
            run_folder,
            "dashboard.html"
        )
        assert os.path.exists(dashboard_path), f"dashboard.html should exist at {dashboard_path}"


class TestSecureAdvisor:
    """Test crs_secure_advisor for all scenarios."""

    @pytest.fixture(scope="class")
    def scenario_runs(self):
        """
        Run simulations first to generate data for advisor tests.
        Returns dict mapping scenario names to their run folders.
        """
        runs = {}
        scenarios = ["http_flood", "malware_spread"]
        
        for scenario in scenarios:
            cmd = f"{os.path.join(os.getcwd(), 'fabsim', 'bin', 'fabsim')} localhost run_crs:{scenario}"
            proc = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            stdout, _ = proc.communicate()
            output = stdout.decode("utf-8")
            
            if proc.returncode == 0:
                results_group = f"{scenario}_localhost_1"
                run_folder = extract_run_folder(output, results_group)
                if run_folder:
                    runs[scenario] = {
                        "run_folder": run_folder,
                        "results_group": results_group
                    }
        
        return runs

    @pytest.mark.parametrize(
        "scenario_name",
        ["http_flood", "malware_spread"],
        ids=["http_flood_advisor", "malware_spread_advisor"],
    )
    def test_secure_advisor(self, scenario_runs, scenario_name):
        """Test secure advisor for each scenario."""
        if scenario_name not in scenario_runs:
            pytest.skip(f"No run data available for {scenario_name}")
        
        run_info = scenario_runs[scenario_name]
        results_group = run_info["results_group"]
        run_folder = run_info["run_folder"]
        
        cmd = (
            f"{os.path.join(os.getcwd(), 'fabsim', 'bin', 'fabsim')} localhost "
            f"crs_secure_advisor:{results_group},run={run_folder}"
        )
        
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = proc.communicate()
        output = stdout.decode("utf-8")
        
        assert proc.returncode == 0, f"SecureAdvisor failed: {output}"
        assert "SecureAdvisor finished" in output, "Expected 'SecureAdvisor finished' in output"
        
        # Verify output files were created
        run_path = os.path.join(
            os.getcwd(),
            "localhost_exe",
            "FabSim",
            "results",
            results_group,
            run_folder
        )
        
        recommendations_path = os.path.join(run_path, "recommendations.md")
        patch_path = os.path.join(run_path, "patch.yml")
        
        assert os.path.exists(recommendations_path), f"recommendations.md should exist at {recommendations_path}"
        assert os.path.exists(patch_path), f"patch.yml should exist at {patch_path}"


class TestIntegration:
    """Integration test: full workflow from simulation to dashboard and advisor."""

    @pytest.mark.parametrize(
        "scenario_name",
        ["http_flood", "malware_spread"],
        ids=["http_flood_full_workflow", "malware_spread_full_workflow"],
    )
    def test_full_workflow(self, scenario_name):
        """Test complete workflow: run -> dashboard -> advisor."""
        fabsim_bin = os.path.join(os.getcwd(), "fabsim", "bin", "fabsim")
        
        # Step 1: Run simulation
        run_cmd = f"{fabsim_bin} localhost run_crs:{scenario_name}"
        proc = subprocess.Popen(
            run_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = proc.communicate()
        run_output = stdout.decode("utf-8")
        
        assert proc.returncode == 0, f"Simulation failed: {run_output}"
        assert "CRS job finished" in run_output
        
        results_group = f"{scenario_name}_localhost_1"
        run_folder = extract_run_folder(run_output, results_group)
        assert run_folder is not None, "Run folder should be extracted"
        
        # Step 2: Generate dashboard
        dashboard_cmd = f"{fabsim_bin} localhost crs_generate_dashboard:{results_group},run={run_folder}"
        proc = subprocess.Popen(
            dashboard_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = proc.communicate()
        dashboard_output = stdout.decode("utf-8")
        
        assert proc.returncode == 0, f"Dashboard generation failed: {dashboard_output}"
        assert "Dashboard written" in dashboard_output
        
        # Step 3: Run secure advisor
        advisor_cmd = f"{fabsim_bin} localhost crs_secure_advisor:{results_group},run={run_folder}"
        proc = subprocess.Popen(
            advisor_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = proc.communicate()
        advisor_output = stdout.decode("utf-8")
        
        assert proc.returncode == 0, f"SecureAdvisor failed: {advisor_output}"
        assert "SecureAdvisor finished" in advisor_output
        
        # Verify all expected files exist
        run_path = os.path.join(
            os.getcwd(),
            "localhost_exe",
            "FabSim",
            "results",
            results_group,
            run_folder
        )
        
        expected_files = [
            "run_meta.json",
            "kpis.json",
            "telemetry.json",
            "dashboard.html",
            "recommendations.md",
            "patch.yml"
        ]
        
        for expected_file in expected_files:
            file_path = os.path.join(run_path, expected_file)
            assert os.path.exists(file_path), f"{expected_file} should exist in {run_path}"
