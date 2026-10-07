import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

INPUT = "results/policy_delay_results.csv"
OUTDIR = Path("results")
OUTDIR.mkdir(exist_ok=True)

df = pd.read_csv(INPUT)

assert set(df["method"]) == {"A", "B"}
assert set(df["train_seed"]) == {42, 43, 44}
assert set(df["delay_ms"]) == {0, 10, 20, 30, 40}
assert len(df) == 30

COLORS = {
    "A": "tab:red",
    "B": "tab:gray",
}

LABELS = {
    "A": "A: No-delay training",
    "B": "B: Randomized-delay training (15–30 ms)",
}


def make_plot(metric, ylabel, filename, ylim=None):
    fig, ax = plt.subplots(figsize=(8, 5.5))

    # Training-delay region for method B.
    ax.axvspan(
        15,
        30,
        color="tab:blue",
        alpha=0.07,
        label="B training-delay range",
        zorder=0,
    )

    for method in ["A", "B"]:
        subset = df[df["method"] == method]
        color = COLORS[method]

        # Thin lines = individual independently trained policies.
        for train_seed in sorted(subset["train_seed"].unique()):
            seed_df = (
                subset[subset["train_seed"] == train_seed]
                .sort_values("delay_ms")
            )

            ax.plot(
                seed_df["delay_ms"],
                seed_df[metric],
                color=color,
                linewidth=1.2,
                alpha=0.25,
                zorder=1,
            )

        # Mean ± SD across independent training seeds.
        stats = (
            subset.groupby("delay_ms")[metric]
            .agg(["mean", "std"])
            .reset_index()
            .sort_values("delay_ms")
        )

        ax.fill_between(
            stats["delay_ms"],
            stats["mean"] - stats["std"],
            stats["mean"] + stats["std"],
            color=color,
            alpha=0.12,
            linewidth=0,
            zorder=2,
        )

        ax.plot(
            stats["delay_ms"],
            stats["mean"],
            color=color,
            marker="o",
            markersize=6,
            linewidth=2.8,
            label=LABELS[method],
            zorder=3,
        )

    ax.set_xlabel("Fixed actuator execution delay (ms)")
    ax.set_ylabel(ylabel)
    ax.set_xticks([0, 10, 20, 30, 40])

    if ylim is not None:
        ax.set_ylim(*ylim)

    ax.grid(alpha=0.22)
    ax.legend()
    fig.tight_layout()

    path = OUTDIR / filename
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {path}")


make_plot(
    "survival_ratio",
    "Survival ratio",
    "final_survival_vs_latency.png",
    ylim=(0, 1.05),
)

make_plot(
    "xy_rmse",
    "Linear XY velocity RMSE (m/s)",
    "final_xy_rmse_vs_latency.png",
)

make_plot(
    "yaw_rmse",
    "Yaw-rate RMSE (rad/s)",
    "final_yaw_rmse_vs_latency.png",
)

print("Final multi-seed figures generated.")
