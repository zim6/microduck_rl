#!/usr/bin/env bash
set -euo pipefail

MANIFEST="results/checkpoint_manifest.csv"
OUTDIR="results/full_delay_sweep"

LAGS=(0 2 4 6 8)
EVAL_SEEDS=(0 1 2)

mkdir -p "$OUTDIR"

if [[ ! -f "$MANIFEST" ]]; then
    echo "ERROR: manifest not found: $MANIFEST"
    exit 1
fi

total=0
completed=0
skipped=0

while IFS=, read -r method train_seed checkpoint; do
    [[ "$method" == "method" ]] && continue

    if [[ ! -f "$checkpoint" ]]; then
        echo "ERROR: checkpoint missing: $checkpoint"
        exit 1
    fi

    for eval_seed in "${EVAL_SEEDS[@]}"; do
        for lag in "${LAGS[@]}"; do

            delay_ms=$((lag * 5))
            logfile="${OUTDIR}/${method}_train${train_seed}_eval${eval_seed}_lag${lag}.txt"
            donefile="${logfile}.done"

            total=$((total + 1))

            if [[ -f "$donefile" ]]; then
                echo "[SKIP] ${method} train=${train_seed} eval=${eval_seed} lag=${lag}"
                skipped=$((skipped + 1))
                continue
            fi

            echo
            echo "============================================================"
            echo "RUNNING EVAL"
            echo "method=$method"
            echo "train_seed=$train_seed"
            echo "eval_seed=$eval_seed"
            echo "lag=$lag"
            echo "delay_ms=$delay_ms"
            echo "checkpoint=$checkpoint"
            echo "logfile=$logfile"
            echo "============================================================"

            {
                echo "===== FULL DELAY SWEEP ====="
                echo "method=$method"
                echo "train_seed=$train_seed"
                echo "eval_seed=$eval_seed"
                echo "lag=$lag"
                echo "delay_ms=$delay_ms"
                echo "checkpoint=$checkpoint"
                echo "============================"

                uv run python scripts/evaluate_delay_v05.py \
                    --checkpoint "$checkpoint" \
                    --lag "$lag" \
                    --seed "$eval_seed"

            } 2>&1 | tee "$logfile"

            touch "$donefile"
            completed=$((completed + 1))

        done
    done

done < "$MANIFEST"

echo
echo "============================================================"
echo "FULL SWEEP FINISHED"
echo "Total configurations: $total"
echo "Completed this run:    $completed"
echo "Skipped existing:      $skipped"
echo "Output directory:      $OUTDIR"
echo "============================================================"
