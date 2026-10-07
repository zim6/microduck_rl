import pandas as pd

INPUT = "results/full_delay_results.csv"
POLICY_OUT = "results/policy_delay_results.csv"
SUMMARY_OUT = "results/multiseed_delay_summary.csv"

df = pd.read_csv(INPUT)

metrics = [
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

# ------------------------------------------------------------
# Level 1:
# Average evaluation-seed variability within each trained policy.
#
# Statistical unit after this step:
# one independently trained policy at one fixed delay.
# ------------------------------------------------------------

policy = (
    df.groupby(
        ["method", "train_seed", "lag_steps", "delay_ms"],
        as_index=False,
    )[metrics]
    .mean()
)

expected_policy_rows = 2 * 3 * 5

if len(policy) != expected_policy_rows:
    raise RuntimeError(
        f"Expected {expected_policy_rows} policy-delay rows, got {len(policy)}"
    )

policy.to_csv(POLICY_OUT, index=False)

# ------------------------------------------------------------
# Level 2:
# Aggregate across independent TRAINING seeds.
#
# n = 3 trained policies per method/delay.
# ------------------------------------------------------------

grouped = policy.groupby(
    ["method", "lag_steps", "delay_ms"]
)[metrics]

mean = grouped.mean().add_suffix("_mean")
std = grouped.std(ddof=1).add_suffix("_std")
count = grouped.size().rename("n_train_seeds")

summary = pd.concat(
    [mean, std, count],
    axis=1,
).reset_index()

expected_summary_rows = 2 * 5

if len(summary) != expected_summary_rows:
    raise RuntimeError(
        f"Expected {expected_summary_rows} summary rows, got {len(summary)}"
    )

summary.to_csv(SUMMARY_OUT, index=False)

print("==============================================")
print("MULTI-SEED DELAY ANALYSIS")
print("==============================================")
print(f"Raw evaluation rows:       {len(df)}")
print(f"Policy-delay rows:         {len(policy)}")
print(f"Method-delay summary rows: {len(summary)}")
print()
print(f"Saved: {POLICY_OUT}")
print(f"Saved: {SUMMARY_OUT}")
print()

display_cols = [
    "method",
    "delay_ms",
    "n_train_seeds",
    "survival_ratio_mean",
    "survival_ratio_std",
    "xy_rmse_mean",
    "xy_rmse_std",
    "yaw_rmse_mean",
    "yaw_rmse_std",
]

print(summary[display_cols].to_string(index=False))
