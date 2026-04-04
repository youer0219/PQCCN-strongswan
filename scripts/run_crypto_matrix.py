#!/usr/bin/env python3
"""Run fixed crypto/network matrix experiments in one integrated serial flow.

Default matrix:
- Algorithms: Classic, Hybrid(1PQ), Hybrid(2PQ)
- Networks: ideal, metro, wan, lossy

Warmup and formal sampling are both executed by the same collection pipeline.
Warmup samples are explicitly marked and excluded in later statistics.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import time
from pathlib import Path
from typing import Dict, List

import yaml


DEFAULT_NETWORK_CASES = [
    {"name": "ideal", "rtt_ms": 0.0, "jitter_ms": 0.0, "loss_pct": 0.0, "rate_kbit": -1.0},
    {"name": "metro", "rtt_ms": 12.0, "jitter_ms": 2.0, "loss_pct": 0.1, "rate_kbit": -1.0},
    {"name": "wan", "rtt_ms": 68.0, "jitter_ms": 12.0, "loss_pct": 0.6, "rate_kbit": -1.0},
    {"name": "lossy", "rtt_ms": 135.0, "jitter_ms": 22.0, "loss_pct": 2.0, "rate_kbit": -1.0},
]


def _parse_composite_cases(raw: str):
    """Parse composite cases: name:rtt_ms:jitter_ms:loss_pct[:rate_kbit];..."""
    cases = []
    if not raw:
        return cases
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [x.strip() for x in chunk.split(":")]
        if len(parts) not in {4, 5}:
            raise ValueError(
                "Invalid case format. Expected name:rtt_ms:jitter_ms:loss_pct[:rate_kbit]"
            )
        name, rtt_ms, jitter_ms, loss_pct = parts[:4]
        rate_kbit = parts[4] if len(parts) == 5 else "-1"
        cases.append(
            {
                "name": name,
                "rtt_ms": float(rtt_ms),
                "jitter_ms": float(jitter_ms),
                "loss_pct": float(loss_pct),
                "rate_kbit": float(rate_kbit),
            }
        )
    return cases


def _core_config(
    compose_file: str,
    note: str,
    iterations: int,
    max_time_s: int,
    traffic_cmd: str,
    warmup_iterations: int,
    warmup_scope: str,
) -> Dict:
    return {
        "TC_Iterations": int(iterations),
        "MaxTimeS": int(max_time_s),
        "RemotePath": "/var/log/charon.log",
        "CommandRetries": 2,
        "TrafficCommand": traffic_cmd,
        "WarmupIterations": int(warmup_iterations),
        "WarmupScope": str(warmup_scope),
        "PrintLevel": 1,
        "compose_files": compose_file,
        "Note": note,
    }


def _empty_network_profile() -> Dict[str, str]:
    return {
        "delay_ms": "",
        "jitter_ms": "",
        "loss_pct": "",
        "duplicate_pct": "",
        "corrupt_pct": "",
        "reorder_pct": "",
        "reorder_corr_pct": "",
        "rate_kbit": "",
    }


def _set_profile_value(profile_map: Dict[str, str], key: str, value: float):
    if value is None:
        profile_map[key] = ""
        return
    if float(value) <= 0:
        profile_map[key] = ""
        return
    rendered = f"{float(value):.6f}".rstrip("0").rstrip(".")
    profile_map[key] = rendered


def _build_network_config(composite_case: Dict) -> Dict:
    delay_ms = round(float(composite_case["rtt_ms"]) / 2.0, 4)
    jitter_case = max(0.0, float(composite_case.get("jitter_ms", 0.0)))
    loss_case = max(0.0, float(composite_case["loss_pct"]))
    rate_raw = float(composite_case.get("rate_kbit", -1.0))

    composite_profile = _empty_network_profile()
    _set_profile_value(composite_profile, "delay_ms", delay_ms)
    _set_profile_value(composite_profile, "jitter_ms", jitter_case)
    _set_profile_value(composite_profile, "loss_pct", loss_case)
    if rate_raw > 0:
        _set_profile_value(composite_profile, "rate_kbit", rate_raw)

    return {
        "Interface": "eth0",
        "AdjustHost": "carol",
        "Profile": composite_profile,
    }


def _write_yaml(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def _preview_paths(paths: List[Path], max_items: int = 3) -> str:
    if len(paths) <= max_items:
        return "\n".join(f"  - {p}" for p in paths)
    head = "\n".join(f"  - {p}" for p in paths[:max_items])
    return f"{head}\n  ... ({len(paths) - max_items} more)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full fixed matrix for crypto algorithms x network profiles")
    parser.add_argument("--result-dir", default="./results/crypto_matrix", help="Output directory for logs and plots")
    parser.add_argument("--iterations", type=int, default=200, help="Formal IKE iterations per matrix point")
    parser.add_argument("--warmup-iters", type=int, default=20, help="Warmup IKE iterations per matrix point")
    parser.add_argument(
        "--warmup-scope",
        choices=["per_config", "per_point", "off"],
        default="per_point",
        help="When to run warm-up iterations",
    )
    parser.add_argument("--max-time-s", type=int, default=7200, help="Max runtime budget per config")
    parser.add_argument("--traffic-cmd", default="ping -c 2 10.1.0.2", help="Traffic command during each iteration")
    parser.add_argument("--print-level", type=int, default=1, help="Pipeline print level")
    parser.add_argument("--collect-print-level", type=int, default=1, help="Collector print level")
    parser.add_argument(
        "--composite-cases",
        default="",
        help="Override default cases with: name:rtt_ms:jitter_ms:loss_pct[:rate_kbit];...",
    )
    parser.add_argument("--show-configs", action="store_true", help="Print all generated config paths")
    parser.add_argument("--dry-run", action="store_true", help="Generate configs and print command only")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    result_dir = (repo_root / args.result_dir).resolve()
    cfg_dir = result_dir / "generated_configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    composite_cases = list(DEFAULT_NETWORK_CASES)
    if args.composite_cases.strip():
        composite_cases = _parse_composite_cases(args.composite_cases)

    scenarios = [
        {
            "name": "classic_classic",
            "label": "Classic-KEX + Classic-Cert",
            "compose": "./pq-strongswan/baseline-docker-compose.yml",
        },
        {
            "name": "hybrid1pq_pqcert",
            "label": "Hybrid(1PQ)-KEX + PQ-Cert",
            "compose": "./pq-strongswan/hybrid1pq-docker-compose.yml",
        },
        {
            "name": "hybrid2pq_pqcert",
            "label": "Hybrid(2PQ)-KEX + PQ-Cert",
            "compose": "./pq-strongswan/hybrid2pq-docker-compose.yml",
        },
    ]

    if not composite_cases:
        raise ValueError("At least one network case is required")

    generated = []
    for scenario in scenarios:
        for case in composite_cases:
            net_cfg = _build_network_config(case)
            note = f"{scenario['name']}__composite__{case['name']}"
            cfg = {
                "CoreConfig": _core_config(
                    compose_file=scenario["compose"],
                    note=note,
                    iterations=args.iterations,
                    max_time_s=args.max_time_s,
                    traffic_cmd=args.traffic_cmd,
                    warmup_iterations=args.warmup_iters,
                    warmup_scope=args.warmup_scope,
                ),
                "Carol_Network_Config": net_cfg,
            }
            cfg_path = cfg_dir / f"DataCollect_{scenario['name']}_composite_{case['name']}.yaml"
            _write_yaml(cfg_path, cfg)
            generated.append(cfg_path)

    config_arg = ",".join(str(p) for p in generated)
    orch_cmd = [
        "python3",
        "Orchestration.py",
        str(result_dir),
        config_arg,
        "--print-level",
        str(args.print_level),
        "--collect-print-level",
        str(args.collect_print_level),
    ]

    print("[Matrix] Plan")
    print(f"  Result dir : {result_dir}")
    print("  Mode       : integrated serial matrix")
    print(f"  Scenarios  : {len(scenarios)}")
    print(f"  Networks   : {len(composite_cases)}")
    print(f"  Warm-up    : {args.warmup_iters} iterations ({args.warmup_scope})")
    print(f"  Iterations : {args.iterations} formal samples per matrix point")
    print(f"  Configs    : {len(generated)} files in {cfg_dir}")

    if args.show_configs:
        print("[Matrix] Generated config files:")
        print("\n".join(f"  - {p}" for p in generated))
    else:
        print("[Matrix] Config preview:")
        print(_preview_paths(generated))

    print("[Matrix] Orchestration command:")
    print(f"  {shlex.join(orch_cmd)}")

    if args.dry_run:
        print("[Matrix] Dry-run mode enabled. No experiment executed.")
        return 0

    start = time.perf_counter()
    print("[Matrix] Running orchestration...")
    try:
        subprocess.run(orch_cmd, check=True, cwd=repo_root)
    except subprocess.CalledProcessError as exc:
        print(f"[Matrix] FAILED with exit code: {exc.returncode}")
        print("[Matrix] Tip: run from repo root and keep the command on one line or use '\\' line continuations.")
        return exc.returncode

    elapsed = time.perf_counter() - start
    print("[Matrix] Done")
    print(f"  Duration   : {elapsed:.1f}s")
    print(f"  Results    : {result_dir}")
    print(f"  Configs    : {cfg_dir}")
    print(f"  Report     : {result_dir / 'ExperimentReport.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
