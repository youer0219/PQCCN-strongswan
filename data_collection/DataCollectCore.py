"""Core data collection flow for PQCCN strongSwan experiments.

The collector now uses unified comprehensive network profiles:
- No legacy Constraint1/Constraint2 sections are supported.
- Empty profile values mean no restriction for that dimension.
- Log naming and run metadata are tied to full network profile signatures.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import shlex
import time
from typing import Dict, List, Tuple

import numpy as np
import yaml
from python_on_whales import DockerClient
from tqdm import trange

NETWORK_PROFILE_KEYS = (
    "delay_ms",
    "jitter_ms",
    "loss_pct",
    "duplicate_pct",
    "corrupt_pct",
    "reorder_pct",
    "reorder_corr_pct",
    "rate_kbit",
)

SWEEPABLE_PROFILE_KEYS = (
    "delay_ms",
    "jitter_ms",
    "loss_pct",
    "duplicate_pct",
    "corrupt_pct",
    "reorder_pct",
    "reorder_corr_pct",
    "rate_kbit",
)


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _normalize_compose_files(compose_value):
    if compose_value is None:
        return ["./pq-strongswan/hybrid2pq-docker-compose.yml"]
    if isinstance(compose_value, str):
        return [compose_value]
    if isinstance(compose_value, list):
        return compose_value
    raise ValueError("CoreConfig.compose_files must be a string or a list of strings")


def _build_sweep_values(cfg: Dict) -> np.ndarray:
    if cfg.get("SweepValues"):
        return np.array(cfg["SweepValues"], dtype=float)

    start = float(cfg.get("StartRange", 1))
    end = float(cfg.get("EndRange", start))
    steps = int(cfg.get("Steps", 1))
    steps = max(1, steps)

    mode = str(cfg.get("SweepMode", "linear")).strip().lower()
    if steps == 1:
        return np.array([start], dtype=float)

    if mode == "log":
        if start <= 0 or end <= 0:
            raise ValueError("SweepMode=log requires StartRange and EndRange > 0")
        vals = np.logspace(np.log10(start), np.log10(end), steps)
    else:
        vals = np.linspace(start, end, steps)
    return np.round(vals, 4)


def _print_nested(title: str, data: Dict):
    print(f"\n\n{title}")
    for k, v in data.items():
        if isinstance(v, dict):
            print(f"\t{k}")
            for sk, sv in v.items():
                print(f"\t\t{sk}: {sv}")
        else:
            print(f"\t{k}: {v}")


def _exec_with_retry(docker: DockerClient, host: str, command: str, retries=1, plvl=0, detach=False):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            docker.execute(host, shlex.split(command), detach=detach)
            return True
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if plvl > 1:
                print(f"[{host}] command failed ({attempt}/{retries}): {command}")
                print(f"  reason: {exc}")
            if attempt < retries:
                time.sleep(0.2)
    if plvl > 0:
        print(f"[{host}] final failure: {command}")
        print(f"  reason: {last_err}")
    return False


def _cleanup_qdisc(docker: DockerClient, host: str, plvl: int, interface: str = "eth0"):
    try:
        docker.execute(host, shlex.split(f"tc qdisc del dev {interface} root"), detach=False)
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "Cannot delete qdisc with handle of zero" in msg:
            return
        if plvl > 0:
            print(f"[{host}] qdisc cleanup warning: {exc}")


def _target_hosts(adjust_host: str, mirror_moon: bool) -> List[str]:
    mode = str(adjust_host or "carol").strip().lower()
    if mode == "both":
        return ["carol", "moon"]
    if mode == "moon":
        return ["moon"]
    if mirror_moon:
        return ["carol", "moon"]
    return ["carol"]


def _resolve_warmup_config(core: Dict) -> Tuple[int, str]:
    warmup_iterations = max(0, int(core.get("WarmupIterations", 0) or 0))
    warmup_scope = str(core.get("WarmupScope", "per_config")).strip().lower()
    if warmup_iterations == 0 or warmup_scope == "off":
        return 0, "off"
    if warmup_scope not in {"per_config", "per_point"}:
        raise ValueError("WarmupScope must be one of: per_config, per_point, off")
    return warmup_iterations, warmup_scope


def _clear_remote_log(docker: DockerClient, host: str, remote_path: str, retries: int, plvl: int):
    _exec_with_retry(docker, host, f"sh -lc \"echo 'newlog' > {remote_path}\"", retries=retries, plvl=plvl)


def _copy_remote_log(docker: DockerClient, remote_path: str, local_path: str, plvl: int):
    try:
        docker.copy(("carol", remote_path), local_path)
        return True
    except Exception as exc:  # noqa: BLE001
        if plvl > 0:
            print(f"copy log failed: {exc}")
        return False


def _append_runstats_line(
    runstats_path: str,
    *,
    log_name: str,
    note: str,
    sweep_key: str,
    profile_signature: str,
    carol_profile_text: str,
    moon_profile_text: str,
    tc_cmd: str,
    iteration_time: float,
    total_time: float,
    is_warmup: bool,
):
    with open(runstats_path, "a", encoding="utf-8") as f:
        f.writelines(
            log_name
            + "; ScenarioNote: "
            + note
            + "; SweepKey: "
            + (sweep_key if sweep_key else "none")
            + "; NetworkProfile: "
            + profile_signature
            + "; CarolProfile: "
            + carol_profile_text
            + "; MoonProfile: "
            + moon_profile_text
            + "; tc_command: "
            + tc_cmd
            + "; IsWarmup: "
            + ("1" if is_warmup else "0")
            + "; IterationTime: "
            + str(iteration_time)
            + " seconds"
            + "; Total Run Time: "
            + str(total_time)
            + " seconds\n"
        )


def _run_iteration_batch(
    docker: DockerClient,
    traffic_cmd: str,
    ipsec_n: int,
    retries: int,
    plvl: int,
    run_start_tic: float | None = None,
    elapsed_offset: float = 0.0,
    max_run_time: float | None = None,
):
    batch_start = time.perf_counter()
    for _ in trange(ipsec_n):
        _exec_with_retry(docker, "carol", "swanctl --initiate --child net", retries=retries, plvl=plvl)
        _exec_with_retry(docker, "carol", traffic_cmd, retries=retries, plvl=plvl)
        _exec_with_retry(docker, "carol", "swanctl --terminate --ike home", retries=retries, plvl=plvl)
        if run_start_tic is not None and max_run_time is not None:
            effective_elapsed = time.perf_counter() - run_start_tic - elapsed_offset
            if effective_elapsed > max_run_time:
                break
    return time.perf_counter() - batch_start


def _load_config(yml_config: str) -> Tuple[Dict, Dict, Dict]:
    with open(yml_config, encoding="utf-8") as f:
        conf = yaml.safe_load(f) or {}

    if "Carol_TC_Config" in conf or "Moon_TC_Config" in conf:
        raise ValueError(
            "Legacy constraint sections are no longer supported. Use Carol_Network_Config and Moon_Network_Config."
        )

    core = conf.get("CoreConfig") or {}
    carol = conf.get("Carol_Network_Config") or {}
    moon = conf.get("Moon_Network_Config") or {}

    if not isinstance(core, dict):
        raise ValueError("CoreConfig must be a mapping")
    if not isinstance(carol, dict):
        raise ValueError("Carol_Network_Config must be a mapping")
    if not isinstance(moon, dict):
        raise ValueError("Moon_Network_Config must be a mapping")

    return core, carol, moon


def _ensure_local_path(path_value: str) -> str:
    path_value = path_value or "./"
    os.makedirs(path_value, exist_ok=True)
    if not path_value.endswith("/"):
        return path_value + "/"
    return path_value


def _resolve_iteration_count(core: Dict) -> int:
    if core.get("TC_Interations") is not None:
        return max(1, int(core.get("TC_Interations")))
    return max(1, int(core.get("TC_Iterations", 1)))


def _empty_profile() -> Dict[str, float | None]:
    return {k: None for k in NETWORK_PROFILE_KEYS}


def _optional_number(value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"", "none", "null", "na", "n/a", "off", "unlimited"}:
            return None
    try:
        result = float(value)
    except Exception:  # noqa: BLE001
        return None
    if not math.isfinite(result) or result <= 0:
        return None
    return result


def _fmt_num(value: float | None) -> str:
    if value is None:
        return "none"
    rendered = f"{value:.6f}".rstrip("0").rstrip(".")
    return rendered or "0"


def _slugify(text: str, max_len: int = 140) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip()).strip("_").lower()
    slug = re.sub(r"_+", "_", slug)
    if not slug:
        return "network_profile"
    if len(slug) <= max_len:
        return slug
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    head = slug[: max_len - 11].rstrip("_")
    return f"{head}_{digest}"


def _normalize_network_config(section: Dict, section_name: str, default_adjust_host: str) -> Dict:
    profile_src = section.get("Profile") or {}
    if profile_src and not isinstance(profile_src, dict):
        raise ValueError(f"{section_name}.Profile must be a mapping")

    profile = _empty_profile()
    for key in NETWORK_PROFILE_KEYS:
        profile[key] = _optional_number(profile_src.get(key))

    interface = str(section.get("Interface", "eth0")).strip() or "eth0"
    adjust_host = str(section.get("AdjustHost", default_adjust_host)).strip().lower() or default_adjust_host
    if adjust_host not in {"carol", "moon", "both"}:
        raise ValueError(f"{section_name}.AdjustHost must be one of: carol, moon, both")

    add_params = section.get("AddParams", profile_src.get("add_params", ""))
    add_params = str(add_params or "").strip()

    sweep_key = str(section.get("SweepKey", "")).strip()
    if sweep_key and sweep_key not in SWEEPABLE_PROFILE_KEYS:
        raise ValueError(f"{section_name}.SweepKey must be one of: {', '.join(SWEEPABLE_PROFILE_KEYS)}")

    has_sweep_spec = any(section.get(k) is not None for k in ("SweepValues", "StartRange", "EndRange", "Steps"))
    if sweep_key:
        if has_sweep_spec:
            sweep_values = _build_sweep_values(section).astype(float).tolist()
        elif profile.get(sweep_key) is not None:
            sweep_values = [float(profile[sweep_key])]
        else:
            raise ValueError(
                f"{section_name}.SweepKey={sweep_key} requires SweepValues/StartRange/EndRange or a non-empty Profile value"
            )
    else:
        sweep_values = [None]

    return {
        "interface": interface,
        "adjust_host": adjust_host,
        "profile": profile,
        "add_params": add_params,
        "sweep_key": sweep_key,
        "sweep_values": sweep_values,
    }


def _build_netem_command(prefix: str, interface: str, profile: Dict[str, float | None], add_params: str) -> str:
    chunks = []

    delay = profile.get("delay_ms")
    jitter = profile.get("jitter_ms")
    if delay is not None:
        delay_chunk = f"delay {_fmt_num(delay)}ms"
        if jitter is not None:
            delay_chunk += f" {_fmt_num(jitter)}ms"
        chunks.append(delay_chunk)

    loss = profile.get("loss_pct")
    if loss is not None:
        chunks.append(f"loss {_fmt_num(loss)}%")

    duplicate = profile.get("duplicate_pct")
    if duplicate is not None:
        chunks.append(f"duplicate {_fmt_num(duplicate)}%")

    corrupt = profile.get("corrupt_pct")
    if corrupt is not None:
        chunks.append(f"corrupt {_fmt_num(corrupt)}%")

    reorder = profile.get("reorder_pct")
    reorder_corr = profile.get("reorder_corr_pct")
    if reorder is not None:
        reorder_chunk = f"reorder {_fmt_num(reorder)}%"
        if reorder_corr is not None:
            reorder_chunk += f" {_fmt_num(reorder_corr)}%"
        chunks.append(reorder_chunk)

    rate = profile.get("rate_kbit")
    if rate is not None:
        chunks.append(f"rate {_fmt_num(rate)}kbit")

    if add_params:
        chunks.append(add_params)

    if not chunks:
        return ""

    return f"tc qdisc {prefix} dev {interface} root netem {' '.join(chunks)}"


def _apply_profile_for_hosts(
    docker: DockerClient,
    hosts: List[str],
    interface: str,
    profile: Dict[str, float | None],
    add_params: str,
    retries: int,
    plvl: int,
) -> str:
    cmd = _build_netem_command("add", interface, profile, add_params)
    for host in hosts:
        _cleanup_qdisc(docker, host, plvl, interface=interface)
        if cmd:
            _exec_with_retry(docker, host, cmd, retries=retries, plvl=plvl)
    return cmd or "none"


def _profile_text(profile: Dict[str, float | None], add_params: str) -> str:
    pieces = [f"{k}={_fmt_num(profile.get(k))}" for k in NETWORK_PROFILE_KEYS]
    pieces.append(f"add_params={add_params if add_params else 'none'}")
    return "|".join(pieces)


def _network_signature(carol_profile, carol_add_params: str, moon_profile, moon_add_params: str) -> str:
    return f"carol[{_profile_text(carol_profile, carol_add_params)}]|moon[{_profile_text(moon_profile, moon_add_params)}]"


def RunConfig(ymlConfig, log_dir, plvl):
    core, carol_raw_cfg, moon_raw_cfg = _load_config(ymlConfig)

    pLvl = int(core.get("PrintLevel", 0) if plvl == "" else plvl)
    log_local_path = _ensure_local_path(log_dir if log_dir != "" else core.get("LocalPath", "./"))
    max_run_time = float(core.get("MaxTimeS", 3600))
    remote_path = str(core.get("RemotePath", "/var/log/charon.log"))
    compose_files = _normalize_compose_files(core.get("compose_files"))
    note = str(core.get("Note", "")).strip()
    mirror_moon = _as_bool(core.get("MirrorMoon", False))
    fresh_run = _as_bool(core.get("FreshRun", False))
    retries = max(1, int(core.get("CommandRetries", 1)))
    traffic_cmd = str(core.get("TrafficCommand", "ping -c 2 10.1.0.2"))
    ipsec_n = _resolve_iteration_count(core)
    warmup_n, warmup_scope = _resolve_warmup_config(core)

    carol_cfg = _normalize_network_config(carol_raw_cfg, "Carol_Network_Config", default_adjust_host="carol")
    moon_cfg = _normalize_network_config(moon_raw_cfg, "Moon_Network_Config", default_adjust_host="moon")

    if moon_cfg.get("sweep_key"):
        raise ValueError("Moon_Network_Config sweep is not supported in this release; keep Moon profile static")

    if pLvl > 0:
        print("\n\nCORE CONFIG")
        for k, v in core.items():
            print(f"\t{k}: {v}")
        _print_nested("CAROL NETWORK CONFIG", carol_cfg)
        _print_nested("MOON NETWORK CONFIG", moon_cfg)

    print("\n\n -----------------------------------------------")
    print(f"Max Run Time: {max_run_time / 60} minutes")
    print("----------------------------------------------- \n\n")

    docker = DockerClient(compose_files=compose_files)
    docker.compose.ps()

    startrun_tic = time.perf_counter()
    warmup_elapsed_total = 0.0

    try:
        if not fresh_run:
            try:
                import subprocess

                subprocess.run(["docker", "rm", "-f", "moon", "carol"], capture_output=True)
                docker.compose.down(remove_orphans=True)
            except Exception:
                pass

            if pLvl > 0:
                print(" -- Starting Docker Containers -- ")
            docker.compose.up(detach=True)
            time.sleep(5)
        elif pLvl > 0:
            print("Use Existing Containers")

        if pLvl > 0:
            print(" -- Enable qdisc in Carol & Moon -- ")
        _exec_with_retry(docker, "carol", "ip link set eth0 qlen 1000", retries=retries, plvl=pLvl)
        _exec_with_retry(docker, "moon", "ip link set eth0 qlen 1000", retries=retries, plvl=pLvl)

        if pLvl > 0:
            print(" -- Enable charon daemon -- ")
        _exec_with_retry(docker, "moon", "./charon", retries=retries, plvl=pLvl, detach=True)
        _exec_with_retry(docker, "moon", "swanctl --list-conns", retries=retries, plvl=pLvl)
        _exec_with_retry(docker, "carol", "./charon", retries=retries, plvl=pLvl, detach=True)
        _exec_with_retry(docker, "carol", "swanctl --list-conns", retries=retries, plvl=pLvl)

        if warmup_n > 0 and warmup_scope == "per_config":
            if pLvl > 0:
                print(" -- Warm-up Run (per_config) -- ")
            warmup_t = _run_iteration_batch(docker, traffic_cmd, warmup_n, retries, pLvl)
            warmup_elapsed_total += warmup_t

            date_time = time.strftime("%Y%m%d_%H%M")
            warmup_name = f"{log_local_path}charon-{date_time}-global_warmup__iter_{warmup_n}.log"
            if _copy_remote_log(docker, remote_path, warmup_name, pLvl):
                _append_runstats_line(
                    f"{log_local_path}runstats.txt",
                    log_name=warmup_name,
                    note=(note + "__warmup") if note else "warmup",
                    sweep_key="none",
                    profile_signature="global_warmup",
                    carol_profile_text="global_warmup",
                    moon_profile_text="global_warmup",
                    tc_cmd="warmup",
                    iteration_time=warmup_t,
                    total_time=(time.perf_counter() - startrun_tic - warmup_elapsed_total),
                    is_warmup=True,
                )

            _clear_remote_log(docker, "carol", remote_path, retries, pLvl)
            _exec_with_retry(docker, "carol", "swanctl --reload-settings", retries=retries, plvl=pLvl)
            time.sleep(1)

        time.sleep(1)
        if pLvl > 0:
            print(" -- Starting Data Collection Run -- ")

        c_vals = carol_cfg["sweep_values"]
        sweep_key = carol_cfg.get("sweep_key", "")
        if pLvl > 0:
            print(" -- Begin Network Profile Loop -- ")
            print(f"Total Planned Iterations: {len(c_vals)}")
            if sweep_key:
                print(f"Sweep Key: {sweep_key}")
                print(f"Planned Values: {c_vals}\n\n")
            else:
                print("No sweep configured; running single profile point\n\n")

        for i in trange(len(c_vals)):
            l1_tic = time.perf_counter()
            warmup_elapsed_this_point = 0.0

            current_carol_profile = dict(carol_cfg["profile"])
            if sweep_key:
                current_carol_profile[sweep_key] = _optional_number(c_vals[i])

            current_moon_profile = dict(moon_cfg["profile"])

            carol_targets = _target_hosts(carol_cfg["adjust_host"], mirror_moon)
            carol_cmd = _apply_profile_for_hosts(
                docker,
                carol_targets,
                carol_cfg["interface"],
                current_carol_profile,
                carol_cfg["add_params"],
                retries,
                pLvl,
            )
            moon_cmd = _apply_profile_for_hosts(
                docker,
                ["moon"],
                moon_cfg["interface"],
                current_moon_profile,
                moon_cfg["add_params"],
                retries,
                pLvl,
            )
            tc_cmd = f"carol[{','.join(carol_targets)}]: {carol_cmd} | moon[moon]: {moon_cmd}"

            if warmup_n > 0 and warmup_scope == "per_point":
                if pLvl > 0:
                    print(f" -- Warm-up Run (point {i + 1}/{len(c_vals)}) -- ")
                warmup_elapsed_this_point = _run_iteration_batch(docker, traffic_cmd, warmup_n, retries, pLvl)
                warmup_elapsed_total += warmup_elapsed_this_point

                date_time = time.strftime("%Y%m%d_%H%M")
                warmup_signature = _network_signature(
                    current_carol_profile,
                    carol_cfg["add_params"],
                    current_moon_profile,
                    moon_cfg["add_params"],
                )
                warmup_slug = _slugify(warmup_signature)
                note_slug = _slugify(note) if note else ""
                warmup_parts = [warmup_slug, f"iter_{warmup_n}"]
                if note_slug:
                    warmup_parts.append(note_slug)
                warmup_parts.append("warmup")
                warmup_name = f"{log_local_path}charon-{date_time}-{'__'.join(warmup_parts)}.log"

                if _copy_remote_log(docker, remote_path, warmup_name, pLvl):
                    _append_runstats_line(
                        f"{log_local_path}runstats.txt",
                        log_name=warmup_name,
                        note=(note + "__warmup") if note else "warmup",
                        sweep_key=(sweep_key if sweep_key else "none"),
                        profile_signature=warmup_signature,
                        carol_profile_text=_profile_text(current_carol_profile, carol_cfg["add_params"]),
                        moon_profile_text=_profile_text(current_moon_profile, moon_cfg["add_params"]),
                        tc_cmd=tc_cmd,
                        iteration_time=warmup_elapsed_this_point,
                        total_time=(time.perf_counter() - startrun_tic - warmup_elapsed_total),
                        is_warmup=True,
                    )

                _clear_remote_log(docker, "carol", remote_path, retries, pLvl)
                _exec_with_retry(docker, "carol", "swanctl --reload-settings", retries=retries, plvl=pLvl)
                time.sleep(1)

            _run_iteration_batch(
                docker,
                traffic_cmd,
                ipsec_n,
                retries,
                pLvl,
                run_start_tic=startrun_tic,
                elapsed_offset=warmup_elapsed_total,
                max_run_time=max_run_time,
            )

            date_time = time.strftime("%Y%m%d_%H%M")
            profile_signature = _network_signature(
                current_carol_profile,
                carol_cfg["add_params"],
                current_moon_profile,
                moon_cfg["add_params"],
            )
            profile_slug = _slugify(profile_signature)
            note_slug = _slugify(note) if note else ""

            name_parts = [profile_slug, f"iter_{ipsec_n}"]
            if note_slug:
                name_parts.append(note_slug)
            run_name = "__".join(name_parts)
            log_name = f"{log_local_path}charon-{date_time}-{run_name}.log"

            _copy_remote_log(docker, remote_path, log_name, pLvl)
            _clear_remote_log(docker, "carol", remote_path, retries, pLvl)
            _exec_with_retry(docker, "carol", "swanctl --reload-settings", retries=retries, plvl=pLvl)

            total_time = time.perf_counter() - startrun_tic - warmup_elapsed_total
            l1_time = time.perf_counter() - l1_tic - warmup_elapsed_this_point
            est_rem = (len(c_vals) - i - 1) * l1_time
            if pLvl > 1:
                print(f"Total Time: {total_time} seconds")
                print(f"Last Run Time: {l1_time} seconds")
                print(f"Estimated Remaining Time: {est_rem} seconds")

            _append_runstats_line(
                f"{log_local_path}runstats.txt",
                log_name=log_name,
                note=note,
                sweep_key=(sweep_key if sweep_key else "none"),
                profile_signature=profile_signature,
                carol_profile_text=_profile_text(current_carol_profile, carol_cfg["add_params"]),
                moon_profile_text=_profile_text(current_moon_profile, moon_cfg["add_params"]),
                tc_cmd=tc_cmd,
                iteration_time=l1_time,
                total_time=total_time,
                is_warmup=False,
            )

            if time.perf_counter() - startrun_tic - warmup_elapsed_total > max_run_time:
                break

    finally:
        if pLvl > 0:
            print(" -- Wrapping Up Run -- ")
        _cleanup_qdisc(docker, "carol", pLvl, interface=carol_cfg["interface"])
        _cleanup_qdisc(docker, "moon", pLvl, interface=moon_cfg["interface"])
        try:
            docker.compose.down(remove_orphans=True)
        except Exception:
            pass

    return time.perf_counter() - startrun_tic
