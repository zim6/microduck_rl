#!/usr/bin/env bash
set -euo pipefail

METHOD="${1:-}"
SEED="${2:-}"

if [[ "$METHOD" != "A" && "$METHOD" != "B" ]]; then
    echo "Usage: $0 {A|B} SEED"
    echo "  A = no-delay training (0-0 physics steps)"
    echo "  B = randomized-delay training (3-6 physics steps)"
    exit 1
fi

if [[ -z "$SEED" ]]; then
    echo "Error: training seed required."
    echo "Example: $0 A 43"
    exit 1
fi

if [[ "$METHOD" == "A" ]]; then
    DELAY_MIN=0
    DELAY_MAX=0
    DESCRIPTION="no-delay"
else
    DELAY_MIN=3
    DELAY_MAX=6
    DESCRIPTION="randomized-delay"
fi

COMMIT=$(git rev-parse HEAD)

echo "=================================================="
echo " Microduck latency robustness training"
echo "=================================================="
echo "Method:        $METHOD ($DESCRIPTION)"
echo "Training seed: $SEED"
echo "Delay:         $DELAY_MIN-$DELAY_MAX physics steps"
echo "Delay ms:      $((DELAY_MIN * 5))-$((DELAY_MAX * 5)) ms"
echo "Environments:  512"
echo "Iterations:    5000"
echo "Git commit:    $COMMIT"
echo "=================================================="

WANDB_MODE=offline uv run train Mjlab-Velocity-Flat-MicroDuck \
    --env.scene.num-envs 512 \
    --agent.seed "$SEED" \
    --agent.max-iterations 5000 \
    --agent.save-interval 250 \
    --env.scene.entities.robot.articulation.actuators.0.delay-min-lag "$DELAY_MIN" \
    --env.scene.entities.robot.articulation.actuators.0.delay-max-lag "$DELAY_MAX"
