import pandas as pd
import matplotlib.pyplot as plt

INPUT = "results/policy_delay_results.csv"
OUTPUT = "results/final_paired_survival_40ms.png"

df = pd.read_csv(INPUT)
d40 = df[df["delay_ms"] == 40]

pivot = d40.pivot(
    index="train_seed",
    columns="method",
    values="survival_ratio",
)

fig, ax = plt.subplots(figsize=(6.5, 5.5))

x = [0, 1]

# Paired result for each training seed
for seed in pivot.index:
    a = pivot.loc[seed, "A"]
    b = pivot.loc[seed, "B"]

    ax.plot(
        x,
        [a, b],
        marker="o",
        linewidth=1.5,
        alpha=0.55,
    )

    ax.text(
        1.03,
        b,
        f"seed {seed}: +{(b-a)*100:.1f} pp",
        va="center",
        fontsize=9,
    )

# Mean values
mean_a = pivot["A"].mean()
mean_b = pivot["B"].mean()

ax.plot(
    x,
    [mean_a, mean_b],
    linewidth=3.5,
    marker="o",
    markersize=8,
    label=f"Mean: +{(mean_b-mean_a)*100:.1f} pp",
)

ax.set_xticks(x)
ax.set_xticklabels([
    "A\nNo-delay training",
    "B\nRandomized-delay training",
])

ax.set_ylabel("Survival ratio at 40 ms")
ax.set_ylim(0, 1.05)
ax.set_xlim(-0.15, 1.42)

ax.set_title("Unseen 40 ms Actuator Delay")
ax.grid(axis="y", alpha=0.22)
ax.legend(loc="lower right")

fig.tight_layout()
fig.savefig(
    OUTPUT,
    dpi=300,
    bbox_inches="tight",
)
plt.close(fig)

print(f"Saved: {OUTPUT}")
print()
print("Paired 40 ms survival results:")
print(pivot)
print()
print(f"Mean A: {mean_a:.4f}")
print(f"Mean B: {mean_b:.4f}")
print(f"Mean improvement: {(mean_b-mean_a)*100:.2f} percentage points")
