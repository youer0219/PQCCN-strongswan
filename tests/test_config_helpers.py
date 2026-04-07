import tempfile
import unittest
from pathlib import Path
import importlib.util
import os
import subprocess
import sys
from unittest.mock import patch
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

HAS_PANDAS = importlib.util.find_spec("pandas") is not None
if HAS_PANDAS:
    import pandas as pd

from pqccn_strongswan.config.resolver import resolve_config_files

HAS_NUMPY = importlib.util.find_spec("numpy") is not None
if HAS_NUMPY:
    from pqccn_strongswan.collection.runner import _build_sweep_values

HAS_COLLECTOR = True
try:
    from pqccn_strongswan.collection.runner import _build_netem_command
except Exception:  # noqa: BLE001
    HAS_COLLECTOR = False

HAS_LOG_PARSER = True
try:
    from pqccn_strongswan.processing.log_conversion import _parse_runstats_segments
except Exception:  # noqa: BLE001
    HAS_LOG_PARSER = False

HAS_LOG_STATS = True
try:
    from pqccn_strongswan.processing.log_conversion import Get_Ike_State_Stats
except Exception:  # noqa: BLE001
    HAS_LOG_STATS = False

HAS_MATRIX_PLOT = True
try:
    from pqccn_strongswan.reporting.matrix_svg import generate_matrix_svgs
except Exception:  # noqa: BLE001
    HAS_MATRIX_PLOT = False

HAS_MATRIX_CLI = True
try:
    from pqccn_strongswan.cli.matrix import _parse_composite_cases
except Exception:  # noqa: BLE001
    HAS_MATRIX_CLI = False


class TestConfigHelpers(unittest.TestCase):
    @unittest.skipUnless(HAS_NUMPY, "numpy is required for sweep-value tests")
    def test_build_sweep_values_uses_explicit_values(self):
        vals = _build_sweep_values({"SweepValues": [1, 2.5, 7]})
        self.assertEqual(vals.tolist(), [1.0, 2.5, 7.0])

    @unittest.skipUnless(HAS_NUMPY, "numpy is required for sweep-value tests")
    def test_build_sweep_values_linear(self):
        vals = _build_sweep_values({"StartRange": 1, "EndRange": 5, "Steps": 3, "SweepMode": "linear"})
        self.assertEqual(vals.tolist(), [1.0, 3.0, 5.0])

    @unittest.skipUnless(HAS_NUMPY, "numpy is required for sweep-value tests")
    def test_build_sweep_values_log(self):
        vals = _build_sweep_values({"StartRange": 1, "EndRange": 100, "Steps": 3, "SweepMode": "log"})
        self.assertEqual(vals.tolist(), [1.0, 10.0, 100.0])

    @unittest.skipUnless(HAS_COLLECTOR, "collector module dependencies are required")
    def test_build_netem_command_empty_profile_returns_blank(self):
        profile = {
            "delay_ms": None,
            "jitter_ms": None,
            "loss_pct": None,
            "duplicate_pct": None,
            "corrupt_pct": None,
            "reorder_pct": None,
            "reorder_corr_pct": None,
            "rate_kbit": None,
        }
        cmd = _build_netem_command("add", "eth0", profile, "")
        self.assertEqual(cmd, "")

    @unittest.skipUnless(HAS_COLLECTOR, "collector module dependencies are required")
    def test_build_netem_command_compose_all_dimensions(self):
        profile = {
            "delay_ms": 20,
            "jitter_ms": 2,
            "loss_pct": 0.5,
            "duplicate_pct": 0.1,
            "corrupt_pct": 0.05,
            "reorder_pct": 3,
            "reorder_corr_pct": 25,
            "rate_kbit": 1200,
        }
        cmd = _build_netem_command("add", "eth0", profile, "")
        self.assertIn("tc qdisc add dev eth0 root netem", cmd)
        self.assertIn("delay 20ms 2ms", cmd)
        self.assertIn("loss 0.5%", cmd)
        self.assertIn("duplicate 0.1%", cmd)
        self.assertIn("corrupt 0.05%", cmd)
        self.assertIn("reorder 3% 25%", cmd)
        self.assertIn("rate 1200kbit", cmd)

    def test_resolve_config_files_from_directory(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "a.yaml").write_text("---\n", encoding="utf-8")
            (p / "b.yaml").write_text("---\n", encoding="utf-8")
            out = resolve_config_files(str(p))
            self.assertEqual(len(out), 2)
            self.assertTrue(out[0].endswith("a.yaml"))

    def test_resolve_config_files_comma_list(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            a = p / "a.yaml"
            b = p / "b.yaml"
            a.write_text("---\n", encoding="utf-8")
            b.write_text("---\n", encoding="utf-8")
            out = resolve_config_files(f"{a},{b}")
            self.assertEqual(len(out), 2)

    def test_resolve_config_files_from_presets_directory(self):
        presets_dir = PROJECT_ROOT / "configs" / "experiments" / "presets"
        out = resolve_config_files(str(presets_dir))
        self.assertGreaterEqual(len(out), 6)
        self.assertTrue(any(path.endswith("composite_ideal.yaml") for path in out))

    def test_presets_target_lanhost_and_define_moon_profile(self):
        presets_dir = PROJECT_ROOT / "configs" / "experiments" / "presets"
        preset_paths = sorted(presets_dir.glob("*.yaml"))
        self.assertGreaterEqual(len(preset_paths), 6)

        for path in preset_paths:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(data["CoreConfig"]["TrafficCommand"], "ping -c 2 10.1.0.3")
            self.assertIn("Moon_Network_Config", data)
            self.assertEqual(data["Moon_Network_Config"]["AdjustHost"], "moon")

    def test_moon_virtual_ip_pools_use_dedicated_remote_access_subnet(self):
        moon_cfg_paths = [
            PROJECT_ROOT / "pq-strongswan" / "moon" / "DH" / "swanctl.conf",
            PROJECT_ROOT / "pq-strongswan" / "moon" / "swanctl_hybrid1pq.conf",
            PROJECT_ROOT / "pq-strongswan" / "moon" / "swanctl_hybrid2pq.conf",
            PROJECT_ROOT / "pq-strongswan" / "moon" / "swanctl_hybrid2pq_cert.conf",
        ]

        for path in moon_cfg_paths:
            text = path.read_text(encoding="utf-8")
            self.assertIn("addrs = 10.3.0.0/24", text, msg=str(path))

    @unittest.skipUnless(HAS_LOG_PARSER, "log parser dependencies are required")
    def test_parse_runstats_segments_keeps_is_warmup(self):
        line = (
            "/tmp/charon.log; ScenarioNote: demo; SweepKey: none; "
            "NetworkProfile: n1; IsWarmup: 1; IterationTime: 1.23 seconds"
        )
        path, fields = _parse_runstats_segments(line)
        self.assertEqual(path, "/tmp/charon.log")
        self.assertEqual(fields.get("IsWarmup"), "1")

    @unittest.skipUnless(HAS_LOG_STATS and HAS_PANDAS, "log stats dependencies are required")
    def test_get_ike_state_stats_reports_new_percentiles_without_p99(self):
        df = pd.DataFrame(
            [
                {"Time": 0.0, "NewState": "CONNECTING"},
                {"Time": 1.0, "NewState": "ESTABLISHED"},
                {"Time": 2.0, "NewState": "CONNECTING"},
                {"Time": 4.0, "NewState": "ESTABLISHED"},
                {"Time": 6.0, "NewState": "CONNECTING"},
                {"Time": 9.0, "NewState": "ESTABLISHED"},
                {"Time": 12.0, "NewState": "CONNECTING"},
                {"Time": 16.0, "NewState": "ESTABLISHED"},
            ]
        )

        stats = Get_Ike_State_Stats(df)

        self.assertAlmostEqual(stats["p50"], 2.5)
        self.assertAlmostEqual(stats["p75"], 3.25)
        self.assertAlmostEqual(stats["p90"], 3.7)
        self.assertAlmostEqual(stats["p95"], 3.85)
        self.assertNotIn("p99", stats)

    @unittest.skipUnless(HAS_MATRIX_PLOT and HAS_PANDAS, "matrix plotting dependencies are required")
    def test_generate_matrix_svgs_outputs_percentile_heatmaps(self):
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            df = pd.DataFrame(
                [
                    {"Algorithm": "Classic-KEX + Classic-Cert", "ScenarioCase": "ideal", "p50": 0.01, "p75": 0.015, "p90": 0.018, "p95": 0.02},
                    {"Algorithm": "Hybrid(1PQ)-KEX + PQ-Cert", "ScenarioCase": "ideal", "p50": 0.02, "p75": 0.025, "p90": 0.028, "p95": 0.03},
                    {"Algorithm": "Hybrid(2PQ)-KEX + PQ-Cert", "ScenarioCase": "ideal", "p50": 0.03, "p75": 0.035, "p90": 0.038, "p95": 0.04},
                ]
            )
            audit = generate_matrix_svgs(df, out_dir)
            self.assertFalse(audit.empty)
            self.assertTrue((out_dir / "matrix_algo_scenario_p50.svg").exists())
            self.assertTrue((out_dir / "matrix_algo_scenario_p75.svg").exists())
            self.assertTrue((out_dir / "matrix_algo_scenario_p90.svg").exists())
            self.assertTrue((out_dir / "matrix_algo_scenario_p95.svg").exists())
            self.assertTrue((out_dir / "matrix_latency_percentiles.svg").exists())
            self.assertTrue((out_dir / "matrix_overhead_percentiles.svg").exists())

    @unittest.skipUnless(HAS_MATRIX_CLI, "matrix cli dependencies are required")
    def test_parse_composite_cases_rejects_legacy_jitter_format(self):
        with self.assertRaises(ValueError):
            _parse_composite_cases("metro:15:1.875:0.05:1200")

    def test_python_module_help_smoke(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC_DIR) + (f":{env['PYTHONPATH']}" if env.get("PYTHONPATH") else "")
        proc = subprocess.run(
            [sys.executable, "-m", "pqccn_strongswan", "--help"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("Run end-to-end PQCCN test orchestration", proc.stdout)

    def test_matrix_module_help_smoke(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC_DIR) + (f":{env['PYTHONPATH']}" if env.get("PYTHONPATH") else "")
        proc = subprocess.run(
            [sys.executable, "-m", "pqccn_strongswan.cli.matrix", "--help"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("Run full fixed matrix for crypto algorithms x network profiles", proc.stdout)

    def test_matrix_dry_run_generates_lanhost_target_and_mirrored_profiles(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC_DIR) + (f":{env['PYTHONPATH']}" if env.get("PYTHONPATH") else "")

        with tempfile.TemporaryDirectory() as td:
            result_dir = Path(td) / "matrix_out"
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pqccn_strongswan.cli.matrix",
                    "--dry-run",
                    "--result-dir",
                    str(result_dir),
                ],
                cwd=PROJECT_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            cfg_path = result_dir / "generated_configs" / "composite_classic_classic_metro.yaml"
            self.assertTrue(cfg_path.exists())

            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            self.assertEqual(data["CoreConfig"]["TrafficCommand"], "ping -c 2 10.1.0.3")
            self.assertIn("Moon_Network_Config", data)
            self.assertEqual(
                data["Carol_Network_Config"]["Profile"],
                data["Moon_Network_Config"]["Profile"],
            )
            self.assertEqual(data["Carol_Network_Config"]["Profile"]["delay_ms"], "7.5")
            self.assertEqual(data["Carol_Network_Config"]["Profile"]["jitter_ms"], "1.875")
            self.assertEqual(data["Carol_Network_Config"]["Profile"]["loss_pct"], "0.05")

    @unittest.skipUnless(HAS_MATRIX_CLI, "matrix cli dependencies are required")
    def test_matrix_uses_current_interpreter_for_orchestration(self):
        from pqccn_strongswan.cli import matrix

        with tempfile.TemporaryDirectory() as td:
            result_dir = Path(td) / "matrix_exec"
            argv = [
                "pqccn_strongswan.cli.matrix",
                "--result-dir",
                str(result_dir),
                "--iterations",
                "1",
                "--warmup-iters",
                "0",
            ]

            with patch.object(sys, "argv", argv):
                with patch("pqccn_strongswan.cli.matrix.subprocess.run") as run_mock:
                    run_mock.return_value = subprocess.CompletedProcess(args=[], returncode=0)

                    rc = matrix.main()

        self.assertEqual(rc, 0)
        run_mock.assert_called_once()

        cmd = run_mock.call_args.args[0]
        kwargs = run_mock.call_args.kwargs

        self.assertEqual(cmd[0], sys.executable)
        self.assertEqual(cmd[1:3], ["-m", "pqccn_strongswan"])
        self.assertEqual(kwargs["cwd"], PROJECT_ROOT)
        self.assertIn("env", kwargs)
        self.assertIn(str(SRC_DIR), kwargs["env"]["PYTHONPATH"].split(":"))


if __name__ == "__main__":
    unittest.main()
