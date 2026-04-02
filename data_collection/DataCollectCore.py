"""Core data collection flow for PQCCN strongSwan experiments.

This module keeps the original RunConfig(ymlConfig, log_dir, plvl) API, while
adding safer config handling, retry logic, and richer constraint sweep options.
"""

import os
import shlex
import time
from typing import Dict, Iterable, List, Tuple

import numpy as np
import yaml
from python_on_whales import DockerClient
from tqdm import trange


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
        print(f"\t{k}")
        if isinstance(v, dict):
            for sk, sv in v.items():
                print(f"\t\t{sk}: {sv}")


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


def _cleanup_qdisc(docker: DockerClient, host: str, plvl: int):
    try:
        docker.execute(host, shlex.split("tc qdisc del dev eth0 root"), detach=False)
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


def _constraint_to_cmd(prefix: str, item: Dict, value=None, add_params="") -> str:
    ctype = item["Type"]
    c = item["Constraint"]
    iface = item["Interface"]
    units = item.get("Units", "")
    if value is None:
        value = item.get("StartRange", 1)
    return f"tc qdisc {prefix} dev {iface} root {ctype} {c} {value}{units} {add_params}".strip()


def _load_config(yml_config: str) -> Tuple[Dict, Dict, Dict]:
    with open(yml_config, encoding="utf-8") as f:
        conf = yaml.safe_load(f) or {}

    core = conf.get("CoreConfig") or {}
    carol = conf.get("Carol_TC_Config") or {}
    moon = conf.get("Moon_TC_Config") or {}

    if not isinstance(core, dict):
        raise ValueError("CoreConfig must be a mapping")
    if not isinstance(carol, dict):
        raise ValueError("Carol_TC_Config must be a mapping")
    if not isinstance(moon, dict):
        raise ValueError("Moon_TC_Config must be a mapping")

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


def _combine_additional_constraints(base_item: Dict, extras: Iterable[Dict]) -> str:
    add_params = str(base_item.get("AddParams", "") or "").strip()
    base_type = base_item.get("Type")
    for item in extras:
        if item.get("Type") != base_type:
            continue
        chunk = f"{item['Constraint']} {item.get('StartRange', 1)}{item.get('Units', '')} {item.get('AddParams', '')}".strip()
        add_params = f"{add_params} {chunk}".strip()
    return add_params


def _apply_static_constraints(docker, host: str, base_item: Dict, static_items: Iterable[Dict], retries: int, plvl: int):
    for item in static_items:
        if item.get("Type") == base_item.get("Type"):
            continue
        cmd = _constraint_to_cmd("add", item, value=item.get("StartRange", 1), add_params=str(item.get("AddParams", "") or ""))
        _exec_with_retry(docker, host, cmd, retries=retries, plvl=plvl)


def RunConfig(ymlConfig, log_dir, plvl):
    core, carol_cfg, moon_cfg = _load_config(ymlConfig)

    pLvl = int(core.get("PrintLevel", 0) if plvl == "" else plvl)
    log_local_path = _ensure_local_path(log_dir if log_dir != "" else core.get("LocalPath", "./"))
    max_run_time = float(core.get("MaxTimeS", 3600))
    remote_path = str(core.get("RemotePath", "/var/log/charon.log"))
    compose_files = _normalize_compose_files(core.get("compose_files"))
    note = str(core.get("Note", ""))
    mirror_moon = _as_bool(core.get("MirrorMoon", False))
    fresh_run = _as_bool(core.get("FreshRun", False))
    retries = max(1, int(core.get("CommandRetries", 1)))
    traffic_cmd = str(core.get("TrafficCommand", "ping -c 2 10.1.0.2"))
    ipsec_n = _resolve_iteration_count(core)

    if pLvl > 0:
        print("\n\nCORE CONFIG")
        for k, v in core.items():
            print(f"\t{k}: {v}")
        if carol_cfg:
            _print_nested("CAROL CONFIG", carol_cfg)
        if moon_cfg:
            _print_nested("MOON CONFIG", moon_cfg)

    print("\n\n -----------------------------------------------")
    print(f"Max Run Time: {max_run_time / 60} minutes")
    print("----------------------------------------------- \n\n")

    docker = DockerClient(compose_files=compose_files)
    docker.compose.ps()

    base_carol = carol_cfg.get("Constraint1") if carol_cfg else None
    base_moon = moon_cfg.get("Constraint1") if moon_cfg else None
    startrun_tic = time.perf_counter()

    try:
        if not fresh_run:
            docker.compose.down()
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

        if base_carol:
            adjust_host = base_carol.get("AdjustHost", "carol")
            target_hosts = _target_hosts(adjust_host, mirror_moon)
            extra_items = [v for k, v in carol_cfg.items() if k != "Constraint1"]
            c_add_params = _combine_additional_constraints(base_carol, extra_items)

            starter = _constraint_to_cmd("add", base_carol, value=base_carol.get("StartRange", 1), add_params=c_add_params)
            for host in target_hosts:
                _exec_with_retry(docker, host, starter, retries=retries, plvl=pLvl)
            for host in target_hosts:
                _apply_static_constraints(docker, host, base_carol, extra_items, retries, pLvl)

        if base_moon:
            extra_items = [v for k, v in moon_cfg.items() if k != "Constraint1"]
            m_add_params = _combine_additional_constraints(base_moon, extra_items)
            starter = _constraint_to_cmd("add", base_moon, value=base_moon.get("StartRange", 1), add_params=m_add_params)
            _exec_with_retry(docker, "moon", starter, retries=retries, plvl=pLvl)
            _apply_static_constraints(docker, "moon", base_moon, extra_items, retries, pLvl)

        time.sleep(1)
        if pLvl > 0:
            print(" -- Starting Data Collection Run -- ")

        c_vals = _build_sweep_values(base_carol) if base_carol else np.array([1.0])
        if pLvl > 0:
            cname = base_carol.get("Constraint", "baseline") if base_carol else "baseline"
            print(" -- Begin Constraint 1 Loop -- ")
            print(f"Total Planned Iterations: {len(c_vals)}")
            print(f"Planned Values for Carol Constraint {cname}: {c_vals.tolist()}\n\n")

        for i in trange(len(c_vals)):
            l1_tic = time.perf_counter()
            c_add_params = ""
            tc_cmd = ""

            if base_carol:
                c_add_params = _combine_additional_constraints(base_carol, [v for k, v in carol_cfg.items() if k != "Constraint1"])
                tc_cmd = _constraint_to_cmd("change", base_carol, value=c_vals[i], add_params=c_add_params)
                adjust_host = base_carol.get("AdjustHost", "carol")
                for host in _target_hosts(adjust_host, mirror_moon):
                    _exec_with_retry(docker, host, tc_cmd, retries=retries, plvl=pLvl)
                if pLvl > 2:
                    print(f"Updated constraints with: {tc_cmd}")

            for _ in trange(ipsec_n):
                _exec_with_retry(docker, "carol", "swanctl --initiate --child net", retries=retries, plvl=pLvl)
                _exec_with_retry(docker, "carol", traffic_cmd, retries=retries, plvl=pLvl)
                _exec_with_retry(docker, "carol", "swanctl --terminate --ike home", retries=retries, plvl=pLvl)
                if time.perf_counter() - startrun_tic > max_run_time:
                    break

            date_time = time.strftime("%Y%m%d_%H%M")
            if base_carol:
                c_units = str(base_carol.get("Units", ""))
                c_name = str(base_carol.get("Constraint", "constraint"))
                log_name = f"{log_local_path}charon-{date_time}-{c_name}_{c_vals[i]}{c_units}-iter_{ipsec_n}_{note}.log"
            else:
                log_name = f"{log_local_path}charon-{date_time}-baseline-iter_{ipsec_n}.log"

            try:
                docker.copy(("carol", remote_path), log_name)
            except Exception as exc:  # noqa: BLE001
                if pLvl > 0:
                    print(f"copy log failed: {exc}")
            _exec_with_retry(docker, "carol", "sh -lc \"echo 'newlog' > /var/log/charon.log\"", retries=retries, plvl=pLvl)
            _exec_with_retry(docker, "carol", "swanctl --reload-settings", retries=retries, plvl=pLvl)

            total_time = time.perf_counter() - startrun_tic
            l1_time = time.perf_counter() - l1_tic
            est_rem = (len(c_vals) - i - 1) * l1_time
            if pLvl > 1:
                print(f"Total Time: {total_time} seconds")
                print(f"Last Run Time: {l1_time} seconds")
                print(f"Estimated Remaining Time: {est_rem} seconds")

            with open(f"{log_local_path}runstats.txt", "a", encoding="utf-8") as f:
                f.writelines(
                    log_name
                    + "; ScenarioNote: "
                    + note
                    + "; Additional Params: "
                    + c_add_params
                    + "; tc_command: "
                    + tc_cmd
                    + "; IterationTime: "
                    + str(l1_time)
                    + " seconds"
                    + "; Total Run Time: "
                    + str(total_time)
                    + " seconds\n"
                )

            if time.perf_counter() - startrun_tic > max_run_time:
                break

    finally:
        if pLvl > 0:
            print(" -- Wrapping Up Run -- ")
        _cleanup_qdisc(docker, "carol", pLvl)
        _cleanup_qdisc(docker, "moon", pLvl)
        docker.compose.down()

    return time.perf_counter() - startrun_tic
