#!/usr/bin/env python3
"""Run a 3-scenario crypto experiment matrix with configurable network conditions.

Scenarios:
1) Classic KEX + Classic Cert
2) Hybrid(1PQ) KEX + PQ Cert
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


SUPPORTED_PROFILES = {"composite"}


def _parse_composite_cases(raw: str):
    """Parse composite cases: name:rtt_ms:loss_pct:rate_kbit[:jitter_ms];..."""
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
                "Invalid composite case format. Expected name:rtt_ms:loss_pct:rate_kbit[:jitter_ms]"
            )
        name, rtt_ms, loss_pct, rate_kbit = parts[:4]
        jitter_ms = parts[4] if len(parts) == 5 else "0"
        cases.append(
            {
                "name": name,
                "rtt_ms": float(rtt_ms),
                "loss_pct": float(loss_pct),
                "rate_kbit": float(rate_kbit),
                "jitter_ms": float(jitter_ms),
            }
        )
    return cases


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


def _build_network_config(profile: str, delay_values: List[float], args, composite_case=None) -> Dict:
    jitter = max(0.0, float(args.jitter_ms))
    loss = max(0.0, float(args.static_loss_pct))
    rate = max(0.0, float(args.static_rate_kbit))
    profile_map = _empty_network_profile()

    base_delay = delay_values[0] if delay_values else 0.0
    if base_delay > 0:
        _set_profile_value(profile_map, "delay_ms", base_delay)
    if jitter > 0:
        _set_profile_value(profile_map, "jitter_ms", jitter)
    if loss > 0:
        _set_profile_value(profile_map, "loss_pct", loss)
    if rate > 0:
        _set_profile_value(profile_map, "rate_kbit", rate)

    if profile == "rtt":
        return {
            "Interface": "eth0",
            "AdjustHost": "carol",
            "SweepKey": "delay_ms",
            "SweepValues": delay_values,
            "Profile": profile_map,
        }

    if profile == "loss":
        return {
            "Interface": "eth0",
            "AdjustHost": "carol",
            "SweepKey": "loss_pct",
            "SweepValues": _parse_list(args.loss_pct, float),
            "Profile": profile_map,
        }

    if profile == "rate":
        return {
            "Interface": "eth0",
            "AdjustHost": "carol",
            "SweepKey": "rate_kbit",
            "SweepValues": _parse_list(args.rate_kbit, float),
            "Profile": profile_map,
        }

    if profile == "mixed":
        return {
            "Interface": "eth0",
            "AdjustHost": "carol",
            "SweepKey": "delay_ms",
            "SweepValues": delay_values,
            "Profile": profile_map,
        }

    if profile == "composite":
        if composite_case is None:
            raise ValueError("profile=composite requires composite_case")
        delay_ms = round(float(composite_case["rtt_ms"]) / 2.0, 4)
        jitter_case = max(0.0, float(composite_case.get("jitter_ms", 0.0)))
        loss_case = max(0.0, float(composite_case["loss_pct"]))
        rate_case = max(0.0, float(composite_case["rate_kbit"]))

        composite_profile = _empty_network_profile()
        _set_profile_value(composite_profile, "delay_ms", delay_ms)
        _set_profile_value(composite_profile, "jitter_ms", jitter_case)
        _set_profile_value(composite_profile, "loss_pct", loss_case)
        _set_profile_value(composite_profile, "rate_kbit", rate_case)
        return {
            "Interface": "eth0",
            "AdjustHost": "carol",
            "Profile": composite_profile,
        }

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
    parser = argparse.ArgumentParser(description="Run 3 crypto scenarios with 4 composite RTT/loss network profiles")
    parser.add_argument("--result-dir", default="./results/crypto_matrix", help="Output directory for logs and plots")
    parser.add_argument(
        "--profiles",
        default="composite",
        help="Network profile mode. Only 'composite' is supported.",
    )
    parser.add_argument("--rtt-ms", default="0,20,50,100", help="RTT sweep values in ms for rtt/mixed profiles")
    parser.add_argument("--loss-pct", default="0,0.1,0.5,1,2", help="Loss sweep values in %% for loss profile")
    parser.add_argument("--rate-kbit", default="4000,2000,1000,512", help="Rate sweep values in kbit for rate profile")
    parser.add_argument("--static-loss-pct", type=float, default=0.5, help="Static loss %% used in non-loss profiles")
    parser.add_argument("--static-rate-kbit", type=float, default=0, help="Static rate kbit used in non-rate profiles (0 = unlimited)")
    parser.add_argument("--jitter-ms", type=float, default=0.0, help="Optional jitter (ms) paired with delay")
    parser.add_argument("--iterations", type=int, default=10, help="IKE iterations per sweep point")
    parser.add_argument("--warmup-iters", type=int, default=3, help="Warm-up IKE iterations before formal sampling")
    parser.add_argument(
        "--warmup-scope",
        choices=["per_config", "per_point", "off"],
        default="per_config",
        help="When to run warm-up iterations",
    )
    parser.add_argument("--max-time-s", type=int, default=7200, help="Max runtime budget per config")
    parser.add_argument("--traffic-cmd", default="ping -c 2 10.1.0.2", help="Traffic command during each iteration")
    parser.add_argument("--print-level", type=int, default=1, help="Pipeline print level")
    parser.add_argument("--collect-print-level", type=int, default=1, help="Collector print level")
    parser.add_argument(
        "--composite-cases",
        default="ideal:0:0:4000;metro:20:0.1:3200;wan:60:0.5:2200;harsh:120:2.0:1200",
        help="Composite network cases: name:rtt_ms:loss_pct:rate_kbit[:jitter_ms];...",
    )
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
    supported_profiles = set(SUPPORTED_PROFILES)
    invalid = [p for p in profile_list if p not in supported_profiles]
    if invalid:
        raise ValueError(
            f"Unsupported profile(s): {', '.join(invalid)}. Supported: {', '.join(sorted(supported_profiles))}"
        )

    rtt_values = _parse_list(args.rtt_ms, float)
    delay_values = _rtt_to_delay_values(rtt_values)
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

    generated = []
    for scenario in scenarios:
        for profile in profile_list:
            if profile != "composite":
                net_cfg = _build_network_config(profile, delay_values, args)
                note = f"{scenario['name']}__{profile}"
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
                cfg_path = cfg_dir / f"DataCollect_{scenario['name']}_{profile}.yaml"
                _write_yaml(cfg_path, cfg)
                generated.append(cfg_path)
                continue

            if not composite_cases:
                raise ValueError("No composite cases found. Use --composite-cases to provide at least one case.")

            for case in composite_cases:
                net_cfg = _build_network_config("composite", delay_values, args, composite_case=case)
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
    print(f"  Profiles   : {', '.join(profile_list)}")
    print(f"  Scenarios  : {len(scenarios)}")
    print(f"  Warm-up    : {args.warmup_iters} iterations ({args.warmup_scope})")
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
