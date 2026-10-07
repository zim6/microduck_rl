import argparse
from dataclasses import asdict

import torch

import mjlab_microduck  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls


TASK_ID = "Mjlab-Velocity-Flat-MicroDuck"

NUM_ENVS = 4
parser = argparse.ArgumentParser()
parser.add_argument(
    "--checkpoint",
    type=str,
    required=True,
    help="Path to the RSL-RL checkpoint to evaluate.",
)
parser.add_argument(
    "--lag",
    type=int,
    default=4,
    help="Fixed actuator delay in physics steps (1 step = 5 ms).",
)
parser.add_argument(
    "--seed",
    type=int,
    default=0,
    help="Evaluation random seed.",
)
args = parser.parse_args()
CHECKPOINT = args.checkpoint

FIXED_LAG = args.lag
EVAL_SEED = args.seed          # physics steps
ROLLOUT_STEPS = 5000
DEVICE = "cuda:0"


def main():
    # ---------------------------------------------------------
    # 1. Load official play configuration.
    # ---------------------------------------------------------
    env_cfg = load_env_cfg(TASK_ID, play=True)
    agent_cfg = load_rl_cfg(TASK_ID)

    env_cfg.scene.num_envs = NUM_ENVS
    env_cfg.seed = EVAL_SEED

    print(f"[EVAL] evaluation seed = {EVAL_SEED}")

    # ---------------------------------------------------------
    # Fixed velocity command for controlled evaluation.
    #
    # command = [vx, vy, wz]
    #         = [0.3 m/s, 0.0 m/s, 0.0 rad/s]
    #
    # Use degenerate sampling ranges so every command resample
    # produces exactly the same target.
    # ---------------------------------------------------------
    TARGET_VX = 0.3
    TARGET_VY = 0.0
    TARGET_WZ = 0.0

    twist_cfg = env_cfg.commands["twist"]

    twist_cfg.ranges.lin_vel_x = (TARGET_VX, TARGET_VX)
    twist_cfg.ranges.lin_vel_y = (TARGET_VY, TARGET_VY)
    twist_cfg.ranges.ang_vel_z = (TARGET_WZ, TARGET_WZ)

    # Disable special command buckets that could overwrite the
    # fixed command during resampling.
    twist_cfg.rel_standing_envs = 0.0
    twist_cfg.rel_heading_envs = 0.0

    if hasattr(twist_cfg, "rel_turn_in_place_envs"):
        twist_cfg.rel_turn_in_place_envs = 0.0

    print(
        f"[EVAL] fixed command = "
        f"vx={TARGET_VX:.3f} m/s, "
        f"vy={TARGET_VY:.3f} m/s, "
        f"wz={TARGET_WZ:.3f} rad/s"
    )

    # ---------------------------------------------------------
    # 2. Force constant actuator latency BEFORE env creation.
    #    Physics dt = 0.005 s:
    #       lag 4 = 20 ms actuator command latency.
    # ---------------------------------------------------------
    robot_cfg = env_cfg.scene.entities["robot"]

    for actuator_cfg in robot_cfg.articulation.actuators:
        actuator_cfg.delay_min_lag = FIXED_LAG
        actuator_cfg.delay_max_lag = FIXED_LAG

    # ---------------------------------------------------------
    # 3. Disable external push disturbance.
    # ---------------------------------------------------------
    if "push_robot" in env_cfg.events:
        del env_cfg.events["push_robot"]

    print(
        f"[EVAL] fixed actuator lag = {FIXED_LAG} physics steps "
        f"({FIXED_LAG * 5} ms)"
    )

    # ---------------------------------------------------------
    # 4. Create headless environment.
    # ---------------------------------------------------------
    env = ManagerBasedRlEnv(
        cfg=env_cfg,
        device=DEVICE,
        render_mode=None,
    )

    # Runtime verification.
    robot = env.scene["robot"]

    print("\n[EVAL] Runtime actuator configuration:")
    for i, actuator in enumerate(robot.actuators):
        print(
            f"  actuator[{i}] "
            f"min={actuator.cfg.delay_min_lag} "
            f"max={actuator.cfg.delay_max_lag} "
            f"has_delay={actuator.has_delay}"
        )

    # ---------------------------------------------------------
    # 5. Same RSL-RL wrapper / checkpoint loader as play.
    # ---------------------------------------------------------
    env = RslRlVecEnvWrapper(
        env,
        clip_actions=agent_cfg.clip_actions,
    )

    runner_cls = load_runner_cls(TASK_ID) or MjlabOnPolicyRunner

    runner = runner_cls(
        env,
        asdict(agent_cfg),
        device=DEVICE,
    )

    runner.load(
        CHECKPOINT,
        load_cfg={"actor": True},
        strict=True,
        map_location=DEVICE,
    )

    policy = runner.get_inference_policy(device=DEVICE)

    # ---------------------------------------------------------
    # 6. Survival evaluation.
    # ---------------------------------------------------------
    obs = env.get_observations()

    completed_episodes = 0
    timeout_episodes = 0
    failure_episodes = 0

    episode_steps = torch.zeros(
        NUM_ENVS,
        dtype=torch.long,
        device=DEVICE,
    )

    completed_survival_times = []
    failure_times = []

    # Tracking-error accumulators.
    # These use the same body-frame physical state as the official
    # velocity tracking rewards.
    sum_sq_vx = 0.0
    sum_sq_vy = 0.0
    sum_sq_xy = 0.0
    sum_sq_wz = 0.0

    sum_actual_vx = 0.0
    sum_actual_vy = 0.0
    sum_actual_wz = 0.0

    tracking_samples = 0

    print("\n[EVAL] Starting tracking evaluation...")

    with torch.inference_mode():
        for step in range(ROLLOUT_STEPS):
            actions = policy(obs)

            if not bool(torch.isfinite(actions).all()):
                raise RuntimeError(
                    f"Non-finite policy action detected at step {step}"
                )

            obs, rewards, dones, extras = env.step(actions)

            dones = dones.bool()
            time_outs = extras["time_outs"].bool()

            # -------------------------------------------------
            # Physical velocity tracking.
            #
            # Match the official reward implementation:
            #   root_link_lin_vel_b
            #   root_link_ang_vel_b
            #
            # Command and actual velocity are therefore expressed
            # in the robot body frame.
            # -------------------------------------------------
            base_robot = env.unwrapped.scene["robot"]

            actual_lin = base_robot.data.root_link_lin_vel_b
            actual_ang = base_robot.data.root_link_ang_vel_b

            command = env.unwrapped.command_manager.get_command("twist")

            vx_error = command[:, 0] - actual_lin[:, 0]
            vy_error = command[:, 1] - actual_lin[:, 1]
            wz_error = command[:, 2] - actual_ang[:, 2]

            sum_sq_vx += torch.sum(vx_error.square()).item()
            sum_sq_vy += torch.sum(vy_error.square()).item()

            sum_sq_xy += torch.sum(
                vx_error.square() + vy_error.square()
            ).item()

            sum_sq_wz += torch.sum(wz_error.square()).item()

            sum_actual_vx += torch.sum(actual_lin[:, 0]).item()
            sum_actual_vy += torch.sum(actual_lin[:, 1]).item()
            sum_actual_wz += torch.sum(actual_ang[:, 2]).item()

            tracking_samples += NUM_ENVS

            # One control step = 0.02 s.
            episode_steps += 1

            if dones.any():
                done_ids = torch.nonzero(
                    dones,
                    as_tuple=False,
                ).squeeze(-1)

                for env_id in done_ids.tolist():
                    duration = (
                        episode_steps[env_id].item() * 0.02
                    )

                    completed_episodes += 1
                    completed_survival_times.append(duration)

                    if bool(time_outs[env_id]):
                        timeout_episodes += 1
                    else:
                        failure_episodes += 1
                        failure_times.append(duration)

                    # Wrapper automatically resets this environment.
                    episode_steps[env_id] = 0

            if step % 500 == 0:
                print(
                    f"[EVAL] step={step:4d} "
                    f"completed={completed_episodes} "
                    f"timeouts={timeout_episodes} "
                    f"failures={failure_episodes}"
                )

    # ---------------------------------------------------------
    # 7. Report.
    # ---------------------------------------------------------
    print("\n[EVAL] Survival evaluation results")
    print("----------------------------------")
    print(
        f"Fixed lag:             "
        f"{FIXED_LAG} physics steps ({FIXED_LAG * 5} ms)"
    )
    print(f"Parallel envs:          {NUM_ENVS}")
    print(f"Evaluation steps:       {ROLLOUT_STEPS}")
    print(f"Completed episodes:     {completed_episodes}")
    print(f"Timeout/survived:       {timeout_episodes}")
    print(f"Failure episodes:       {failure_episodes}")

    if completed_episodes > 0:
        survival_ratio = timeout_episodes / completed_episodes

        mean_survival = (
            sum(completed_survival_times)
            / len(completed_survival_times)
        )

        print(f"Survival ratio:         {survival_ratio:.4f}")
        print(f"Mean survival time:     {mean_survival:.3f} s")
    else:
        print("Survival ratio:         N/A")
        print("Mean survival time:     N/A")

    if failure_times:
        mean_failure_time = sum(failure_times) / len(failure_times)
        print(f"Mean failure time:      {mean_failure_time:.3f} s")
    else:
        print("Mean failure time:      N/A")

    # Episodes still alive when the evaluation window ends.
    active_times = episode_steps.float() * 0.02

    print(
        f"Active episodes at end: "
        f"{int((episode_steps > 0).sum().item())}"
    )

    if (episode_steps > 0).any():
        print(
            f"Mean current age:       "
            f"{active_times[episode_steps > 0].mean().item():.3f} s"
        )

    # ---------------------------------------------------------
    # Tracking report.
    # ---------------------------------------------------------
    if tracking_samples > 0:
        vx_rmse = (sum_sq_vx / tracking_samples) ** 0.5
        vy_rmse = (sum_sq_vy / tracking_samples) ** 0.5
        xy_rmse = (sum_sq_xy / tracking_samples) ** 0.5
        yaw_rmse = (sum_sq_wz / tracking_samples) ** 0.5

        mean_vx = sum_actual_vx / tracking_samples
        mean_vy = sum_actual_vy / tracking_samples
        mean_wz = sum_actual_wz / tracking_samples

        print("\n[EVAL] Velocity tracking results")
        print("----------------------------------")
        print(
            f"Command:               "
            f"vx={TARGET_VX:.3f} m/s, "
            f"vy={TARGET_VY:.3f} m/s, "
            f"wz={TARGET_WZ:.3f} rad/s"
        )
        print(f"Tracking samples:       {tracking_samples}")
        print(f"Linear XY RMSE:         {xy_rmse:.4f} m/s")
        print(f"Forward vx RMSE:        {vx_rmse:.4f} m/s")
        print(f"Lateral vy RMSE:        {vy_rmse:.4f} m/s")
        print(f"Yaw-rate RMSE:          {yaw_rmse:.4f} rad/s")
        print(f"Mean actual vx:         {mean_vx:.4f} m/s")
        print(f"Mean actual vy:         {mean_vy:.4f} m/s")
        print(f"Mean actual wz:         {mean_wz:.4f} rad/s")

    print(
        "\n[EVAL] Tracking evaluation completed successfully."
    )

    env.close()


if __name__ == "__main__":
    main()
