import tempfile
import unittest
from pathlib import Path
import importlib.util

from config_utils import resolve_config_files

HAS_NUMPY = importlib.util.find_spec("numpy") is not None
if HAS_NUMPY:
    from data_collection.DataCollectCore import _build_sweep_values

HAS_COLLECTOR = True
try:
    from data_collection.DataCollectCore import _build_netem_command
except Exception:  # noqa: BLE001
    HAS_COLLECTOR = False


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


if __name__ == "__main__":
    unittest.main()
