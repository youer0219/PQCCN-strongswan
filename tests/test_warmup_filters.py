import tempfile
import unittest
from pathlib import Path
import importlib.util
import inspect
import sys
from unittest import mock

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

HAS_PANDAS = importlib.util.find_spec("pandas") is not None
if HAS_PANDAS:
    import pandas as pd
    from pqccn_strongswan.processing import logs
    from pqccn_strongswan.reporting import PlotVariParam, generate_experiment_report


@unittest.skipUnless(HAS_PANDAS, "pandas is required for warmup filter tests")
class TestWarmupFilters(unittest.TestCase):
    def test_plotting_api_does_not_accept_include_warmup(self):
        params = inspect.signature(PlotVariParam).parameters

        self.assertNotIn("include_warmup", params)

    def test_reporting_api_does_not_accept_include_warmup(self):
        params = inspect.signature(generate_experiment_report).parameters

        self.assertNotIn("include_warmup", params)

    def test_plotting_handles_none_input(self):
        audit_df = PlotVariParam(None, tempfile.gettempdir(), 0)

        self.assertTrue(audit_df.empty)

    def test_report_generation_handles_none_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = generate_experiment_report(tmpdir, None, pd.DataFrame())
            report_text = Path(report_path).read_text(encoding="utf-8")

        self.assertIn("- Total rows: 0", report_text)

    def test_process_logs_filters_warmup_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runstats_path = Path(tmpdir) / "runstats.csv"
            runstats_path.write_text(
                (
                    "FilePath: /logs/,FileName: cold.log,ScenarioCase: ideal,IsWarmup: 0,TotalTime: 1.0,IterationTime: 1.0,\n"
                    "FilePath: /logs/,FileName: warm.log,ScenarioCase: warmup,IsWarmup: 1,TotalTime: 2.0,IterationTime: 2.0,\n"
                ),
                encoding="utf-8",
            )

            with mock.patch.object(logs, "RunStats", return_value=str(runstats_path)), \
                 mock.patch.object(logs, "get_Ike_State", return_value={"state": ["ok"]}), \
                 mock.patch.object(logs, "Get_Ike_State_Stats", return_value={"ConnectionPercent": 1.0}):
                result = logs.Log_stats(tmpdir, 0)

        self.assertEqual(result["ScenarioCase"].tolist(), ["ideal"])
        self.assertEqual(result["FullFilePath"].tolist(), ["/logs/cold.log"])

    def test_report_generation_excludes_warmup_by_default(self):
        df = pd.DataFrame(
            [
                {
                    "Algorithm": "Classic-KEX + Classic-Cert",
                    "ScenarioCase": "ideal",
                    "VariParam": "network_profile",
                    "mean": 0.1,
                    "median": 0.1,
                    "p50": 0.1,
                    "p75": 0.15,
                    "p90": 0.18,
                    "p95": 0.2,
                    "ConnectionPercent": 1.0,
                    "IterationTime": 0.1,
                    "IsWarmup": "0",
                },
                {
                    "Algorithm": "Classic-KEX + Classic-Cert",
                    "ScenarioCase": "warmup",
                    "VariParam": "network_profile",
                    "mean": 0.2,
                    "median": 0.2,
                    "p50": 0.2,
                    "p75": 0.25,
                    "p90": 0.28,
                    "p95": 0.3,
                    "ConnectionPercent": 1.0,
                    "IterationTime": 0.2,
                    "IsWarmup": "1",
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filtered_df = df.loc[df["IsWarmup"] == "0"].copy()
            report_path = generate_experiment_report(tmpdir, filtered_df, pd.DataFrame())
            report_text = Path(report_path).read_text(encoding="utf-8")

        self.assertIn("ideal", report_text)
        self.assertNotIn("warmup", report_text.lower())


if __name__ == "__main__":
    unittest.main()
