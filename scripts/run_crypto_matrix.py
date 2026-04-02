#!/usr/bin/env python3
"""Run a 3-scenario crypto experiment matrix with configurable network conditions.

Scenarios:
1) Classic KEX + Classic Cert
2) Pure-PQ KEX + PQ Cert
3) Hybrid KEX (Classic+PQ) + PQ Cert

This script generates YAML configs on the fly, runs Orchestration.py once, and
produces comparable plots and reports (including p50/p95/p99 metrics).
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import time
from pathlib import Path
from typing import Dict, List

import yaml


SUPPORTED_PROFILES = {"rtt", "loss", "rate", "mixed"}


def _parse_list(raw: str, cast=float) -> List[float]:
    values = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        values.append(cast(token))
    if not values:
        raise ValueError(f"Empty list is not allowed: {raw}")
    return values


def _rtt_to_delay_values(rtt_values_ms: List[float]) -> List[float]:
    # RTT is round-trip latency. netem delay models one-way latency.
    return [round(v / 2.0, 4) for v in rtt_values_ms]


def _core_config(compose_file: str, note: str, iterations: int, max_time_s: int, traffic_cmd: str) -> Dict:
    return {
        "TC_Iterations": int(iterations),
        "MaxTimeS": int(max_time_s),
        "RemotePath": "/var/log/charon.log",
        "CommandRetries": 2,
        "TrafficCommand": traffic_cmd,
        "PrintLevel": 1,
        "compose_files": compose_file,
        "Note": note,
    }


def _constraint(
    name: str,
    values: List[float],
    units: str,
    add_params: str,
    tc_type: str = "netem",
    iface: str = "eth0",
) -> Dict:
    return {
        "Type": tc_type,
        "Constraint": name,
        "Interface": iface,
        "SweepValues": values,
        "Units": units,
        "AddParams": add_params.strip(),
    }


def _build_profile_constraints(profile: str, delay_values: List[float], args) -> Dict:
    jitter = max(0.0, float(args.jitter_ms))
    loss = max(0.0, float(args.static_loss_pct))
    rate = max(1.0, float(args.static_rate_kbit))

    if profile == "rtt":
        add = f"{jitter}ms" if jitter > 0 else ""
        return _constraint("delay", delay_values, "ms", add)

    if profile == "loss":
        add_parts = []
        if delay_values and delay_values[0] > 0:
            add_parts.append(f"delay {delay_values[0]}ms")
            if jitter > 0:
                add_parts.append(f"{jitter}ms")
        if rate > 0:
            add_parts.append(f"rate {rate}kbit")
        return _constraint("loss", _parse_list(args.loss_pct, float), "%", " ".join(add_parts))

    if profile == "rate":
        add_parts = []
        if delay_values and delay_values[0] > 0:
            add_parts.append(f"delay {delay_values[0]}ms")
            if jitter > 0:
                add_parts.append(f"{jitter}ms")
        if loss > 0:
            add_parts.append(f"loss {loss}%")
        return _constraint("rate", _parse_list(args.rate_kbit, float), "kbit", " ".join(add_parts))

    if profile == "mixed":
        add_parts = []
        if jitter > 0:
            add_parts.append(f"{jitter}ms")
        if loss > 0:
            add_parts.append(f"loss {loss}%")
        if rate > 0:
            add_parts.append(f"rate {rate}kbit")
        return _constraint("delay", delay_values, "ms", " ".join(add_parts))

    raise ValueError(f"Unsupported profile: {profile}")


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
    parser = argparse.ArgumentParser(description="Run 3 crypto scenarios with configurable network sweeps")
    parser.add_argument("--result-dir", default="./results/crypto_matrix", help="Output directory for logs and plots")
    parser.add_argument(
        "--profiles",
        default="rtt,loss,rate,mixed",
        help="Comma-separated network profiles to run: rtt,loss,rate,mixed",
    )
    parser.add_argument("--rtt-ms", default="0,20,50,100", help="RTT sweep values in ms for rtt/mixed profiles")
    parser.add_argument("--loss-pct", default="0,0.1,0.5,1,2", help="Loss sweep values in %% for loss profile")
    parser.add_argument("--rate-kbit", default="4000,2000,1000,512", help="Rate sweep values in kbit for rate profile")
    parser.add_argument("--static-loss-pct", type=float, default=0.5, help="Static loss %% used in non-loss profiles")
    parser.add_argument("--static-rate-kbit", type=float, default=4000, help="Static rate kbit used in non-rate profiles")
    parser.add_argument("--jitter-ms", type=float, default=0.0, help="Optional jitter (ms) paired with delay")
    parser.add_argument("--iterations", type=int, default=10, help="IKE iterations per sweep point")
    parser.add_argument("--max-time-s", type=int, default=7200, help="Max runtime budget per config")
    parser.add_argument("--traffic-cmd", default="ping -c 2 10.1.0.2", help="Traffic command during each iteration")
    parser.add_argument("--print-level", type=int, default=1, help="Pipeline print level")
    parser.add_argument("--collect-print-level", type=int, default=1, help="Collector print level")
    parser.add_argument("--show-configs", action="store_true", help="Print all generated config paths")
    parser.add_argument("--dry-run", action="store_true", help="Generate configs and print command only")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    result_dir = (repo_root / args.result_dir).resolve()
    cfg_dir = result_dir / "generated_configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    profile_list = [p.strip().lower() for p in args.profiles.split(",") if p.strip()]
    if not profile_list:
        raise ValueError("At least one profile is required")
    invalid = [p for p in profile_list if p not in SUPPORTED_PROFILES]
    if invalid:
        raise ValueError(
            f"Unsupported profile(s): {', '.join(invalid)}. Supported: {', '.join(sorted(SUPPORTED_PROFILES))}"
        )

    rtt_values = _parse_list(args.rtt_ms, float)
    delay_values = _rtt_to_delay_values(rtt_values)

    scenarios = [
        {
            "name": "classic_classic",
            "label": "Classic-KEX + Classic-Cert",
            "compose": "./pq-strongswan/baseline-docker-compose.yml",
        },
        {
            "name": "purepq_pqcert",
            "label": "PurePQ-KEX + PQ-Cert",
            "compose": "./pq-strongswan/pq-only-docker-compose.yml",
        },
        {
            "name": "hybridkex_pqcert",
            "label": "Hybrid-KEX + PQ-Cert",
            "compose": "./pq-strongswan/docker-compose.yml",
        },
    ]

    generated = []
    for scenario in scenarios:
        for profile in profile_list:
            con1 = _build_profile_constraints(profile, delay_values, args)
            note = f"{scenario['name']}__{profile}"
            cfg = {
                "CoreConfig": _core_config(
                    compose_file=scenario["compose"],
                    note=note,
                    iterations=args.iterations,
                    max_time_s=args.max_time_s,
                    traffic_cmd=args.traffic_cmd,
                ),
                "Carol_TC_Config": {
                    "Constraint1": con1,
                },
            }
            cfg_path = cfg_dir / f"DataCollect_{scenario['name']}_{profile}.yaml"
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
    print(f"  Profiles   : {', '.join(profile_list)}")
    print(f"  Scenarios  : {len(scenarios)}")
    print(f"  Iterations : {args.iterations} per sweep point")
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
