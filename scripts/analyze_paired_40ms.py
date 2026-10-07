import pandas as pd

df = pd.read_csv("results/policy_delay_results.csv")

d40 = df[df["delay_ms"] == 40].copy()

metrics = [
    "survival_ratio",
    "xy_rmse",
    "yaw_rmse",
]

for metric in metrics:
    pivot = d40.pivot(
        index="train_seed",
        columns="method",
        values=metric,
    )

    pivot["B_minus_A"] = pivot["B"] - pivot["A"]

    print()
    print("=" * 60)
    print(f"40 ms: {metric}")
    print("=" * 60)
    print(pivot.to_string())
    print()
    print(
        f"Mean B-A: {pivot['B_minus_A'].mean():.6f}"
    )
    print(
        f"SD B-A:   {pivot['B_minus_A'].std(ddof=1):.6f}"
    )
