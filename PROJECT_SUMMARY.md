# Microduck Actuator-Delay Robustness

## Research Question

**Does training with randomized actuator command latency improve the robustness of a learned locomotion policy to unseen fixed execution delays?**

This project investigates actuator-latency robustness in PPO locomotion for the Microduck biped robot using the MuJoCo Warp-based `microduck_rl` environment.

## Method

Two PPO training conditions were compared under the same flat-terrain velocity task and training budget:

- **No-delay training (A):** fixed actuator command delay of 0 ms.
- **Randomized-delay training (B):** actuator delay randomized between 15–30 ms during training.

Each condition was trained with **3 independent training seeds** using:

- 512 parallel environments
- 5,000 PPO iterations
- 61.44 million environment transitions per trained policy

Policies were then evaluated under fixed actuator delays of:

**0, 10, 20, 30, and 40 ms**

For every trained policy and delay condition, results were averaged across three evaluation seeds, producing **90 evaluation runs** in total.

## Key Result

Actuator-delay randomization substantially improved survival robustness as execution latency increased.

At the **out-of-training-range fixed delay of 40 ms**:

| Training condition | Mean survival |
|---|---:|
| No-delay | 45.4% |
| Randomized 15–30 ms delay | 94.5% |

This corresponds to an absolute improvement of **+49.2 percentage points**.

The survival advantage was observed for **all three independently trained seeds**, with paired improvements of approximately:

**+55.4, +30.3, and +61.8 percentage points.**

![Survival robustness](results/final_survival_vs_latency.png)

## Interpretation

The results support the hypothesis that actuator-delay randomization during training can improve robustness to execution latency in this controlled Microduck locomotion setting.

The effect is particularly visible outside the randomized training range: the no-delay policies degrade sharply at 40 ms, while randomized-delay policies retain high survival.

However, the improvement is not uniform across every metric. Randomized-delay policies showed better linear velocity tracking across the tested delays, while yaw-rate tracking exhibited a trade-off: no-delay policies performed better under nominal latency, and the 40 ms yaw-rate result varied substantially across training seeds.

This suggests that delay randomization may change the learned control strategy or gait rather than simply making an otherwise identical policy more robust. This interpretation remains a hypothesis and requires further analysis.

## My Contribution

I designed and executed the robustness study on top of the open-source Microduck RL codebase, including:

- reproducing and validating the GPU locomotion training pipeline;
- identifying the simulator's actuator-delay semantics;
- defining controlled no-delay and randomized-delay PPO conditions;
- building an independent fixed-delay evaluation pipeline;
- training six policies across two conditions and three independent seeds;
- running and aggregating 90 evaluation trials;
- analyzing survival and velocity-tracking robustness;
- packaging the experiment, analysis scripts, figures, and reproducibility instructions.

## Limitations

The current evidence is limited to:

- three independent training runs per condition;
- one robot morphology;
- one flat-terrain velocity task;
- a fixed evaluation command;
- simulation-only evaluation;
- actuator command latency rather than observation latency;
- delays up to 40 ms.

The results therefore support a controlled empirical finding for this setup rather than a general claim about delay randomization in robotic locomotion.

## Next Research Question

The most important follow-up is to determine **why** delay-randomized policies survive substantially longer under high latency.

A useful next-stage study would compare gait and control behavior between the two training conditions using quantities such as joint trajectories, action smoothness, contact timing, body stability, and recovery behavior.

This could test whether actuator-delay randomization induces a qualitatively different locomotion strategy that trades nominal tracking performance for increased closed-loop stability.

---

**Full experiment and reproducibility details:** [README_DELAY_ROBUSTNESS.md](README_DELAY_ROBUSTNESS.md)
