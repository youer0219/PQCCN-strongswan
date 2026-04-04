from glob import glob
from pathlib import Path


def resolve_config_files(config_arg: str):
    """Resolve config input into a sorted list of YAML files."""
    path = Path(config_arg)

    if path.is_file():
        return [str(path)]

    if path.is_dir():
        return sorted(str(x) for x in path.glob("*.yaml"))

    # Support shell-like patterns and comma-separated paths.
    resolved = []
    for token in [x.strip() for x in config_arg.split(",") if x.strip()]:
        matches = glob(token)
        if matches:
            resolved.extend(matches)
        elif token.endswith(".yaml") or token.endswith(".yml"):
            resolved.append(token)

    seen = set()
    out = []
    for f in resolved:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out
