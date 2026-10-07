from pathlib import Path
import re
import csv

INPUT_DIR = Path("results/full_delay_sweep")
OUTPUT = Path("results/full_delay_results.csv")

pattern = re.compile(
    r"(?P<method>[AB])_train(?P<train_seed>\d+)_eval(?P<eval_seed>\d+)_lag(?P<lag>\d+)\.txt$"
)

fields = {
    "completed_episodes": r"Completed episodes:\s+(\d+)",
    "survived_episodes": r"Timeout/survived:\s+(\d+)",
    "failure_episodes": r"Failure episodes:\s+(\d+)",
    "survival_ratio": r"Survival ratio:\s+([0-9.]+)",
    "mean_survival_time_s": r"Mean survival time:\s+([0-9.]+)",
    "xy_rmse": r"Linear XY RMSE:\s+([0-9.]+)",
    "vx_rmse": r"Forward vx RMSE:\s+([0-9.]+)",
    "vy_rmse": r"Lateral vy RMSE:\s+([0-9.]+)",
    "yaw_rmse": r"Yaw-rate RMSE:\s+([0-9.]+)",
    "mean_vx": r"Mean actual vx:\s+([-0-9.]+)",
    "mean_vy": r"Mean actual vy:\s+([-0-9.]+)",
    "mean_wz": r"Mean actual wz:\s+([-0-9.]+)",
}

integer_fields = {
    "completed_episodes",
    "survived_episodes",
    "failure_episodes",
}

rows = []

for path in sorted(INPUT_DIR.glob("*.txt")):
    match = pattern.match(path.name)
    if not match:
        print(f"[WARN] filename not recognized: {path.name}")
        continue

    text = path.read_text(errors="replace")

    if "[EVAL] Tracking evaluation completed successfully." not in text:
        raise RuntimeError(f"Incomplete evaluation: {path}")

    row = {
        "method": match.group("method"),
        "train_seed": int(match.group("train_seed")),
        "eval_seed": int(match.group("eval_seed")),
        "lag_steps": int(match.group("lag")),
        "delay_ms": int(match.group("lag")) * 5,
    }

    for name, regex in fields.items():
        m = re.search(regex, text)
        if not m:
            raise RuntimeError(f"Missing {name} in {path}")

        if name in integer_fields:
            row[name] = int(m.group(1))
        else:
            row[name] = float(m.group(1))

    rows.append(row)

expected = 2 * 3 * 3 * 5

if len(rows) != expected:
    raise RuntimeError(
        f"Expected {expected} evaluations, parsed {len(rows)}."
    )

keys = [
    (
        r["method"],
        r["train_seed"],
        r["eval_seed"],
        r["lag_steps"],
    )
    for r in rows
]

if len(keys) != len(set(keys)):
    raise RuntimeError("Duplicate evaluation configurations detected.")

rows.sort(
    key=lambda r: (
        r["method"],
        r["train_seed"],
        r["eval_seed"],
        r["lag_steps"],
    )
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

fieldnames = [
    "method",
    "train_seed",
    "eval_seed",
    "lag_steps",
    "delay_ms",
    "completed_episodes",
    "survived_episodes",
    "failure_episodes",
    "survival_ratio",
    "mean_survival_time_s",
    "xy_rmse",
    "vx_rmse",
    "vy_rmse",
    "yaw_rmse",
    "mean_vx",
    "mean_vy",
    "mean_wz",
]

with OUTPUT.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Parsed {len(rows)} evaluations.")
print(f"Unique configurations: {len(set(keys))}")
print(f"Saved: {OUTPUT}")
