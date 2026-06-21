#!/usr/bin/env bash
# Run the 10-stage reviewer pipeline on every paper in papers/{accepted,rejected}
# that doesn't yet have a .review.md. All unfinished papers run in parallel.
# After they finish, generate the benchmark summary.
#
# Usage:
#   ./scripts/run_benchmark.sh
#   ./scripts/run_benchmark.sh --effort low      # forward flags to reviewer_agent.py
set -eo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

EXTRA_ARGS=("$@")

run_one() {
  local label="$1" pdf="$2"
  local out_dir="reviews/papers/$label"
  local stem
  stem="$(basename "$pdf" .pdf)"
  mkdir -p "$out_dir/logs"
  if [ ${#EXTRA_ARGS[@]} -gt 0 ]; then
    uv run python reviewer_agent.py "$pdf" --out "$out_dir" "${EXTRA_ARGS[@]}" \
      >"$out_dir/logs/$stem.log" 2>&1
  else
    uv run python reviewer_agent.py "$pdf" --out "$out_dir" \
      >"$out_dir/logs/$stem.log" 2>&1
  fi
}

launched=0
shopt -s nullglob
for label in accepted rejected; do
  for pdf in "papers/$label"/*.pdf; do
    stem="$(basename "$pdf" .pdf)"
    if [ -f "reviews/papers/$label/$stem.review.md" ]; then
      echo "[skip] $label/$stem"
      continue
    fi
    echo "[run ] $label/$stem (log: reviews/papers/$label/logs/$stem.log)"
    (
      if run_one "$label" "$pdf"; then
        echo "[done] $label/$stem"
      else
        echo "[FAIL] $label/$stem (see log)"
      fi
    ) &
    launched=$((launched + 1))
  done
done

if [ "$launched" -gt 0 ]; then
  echo "Launched $launched paper(s) in parallel. Waiting..."
  wait || true
else
  echo "Nothing to run; all reviews exist."
fi

echo
echo "[summary] generating SUMMARY.md / SUMMARY.csv..."
uv run python scripts/summarize_benchmark.py
