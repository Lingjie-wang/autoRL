#!/usr/bin/env bash
# Live demo: 5 verified single-agent environment integrations.
#
#   bash demo_sa_envs.sh           # verification status + fidelity + live rollouts (~60s)
#   bash demo_sa_envs.sh --train   # also re-run the SB3 training smoke (~2.5min)
#
# Every environment is constructed through its own adapter, not through
# hand-written glue, and every number printed is read from a live object or from
# a machine-generated report on disk.

set -u
cd "$(dirname "$0")"
PY=/home/yewei/miniconda3/envs/sa5/bin/python
ENVS=(lunarlander halfcheetah pong minigrid fetchreach)

hr() { printf '%.0s─' {1..76}; echo; }

hr
echo "PART 1 — Verification status (machine-checked, read from disk)"
hr
printf "%-14s %-8s %s\n" ENV STATUS CHECKS
for e in "${ENVS[@]}"; do
  $PY -c "
import json
r = json.load(open('runs/20260726-sa5-$e/verification_report.json'))
s = r['summary']
print(f\"{'$e':<14} {r['overall_status']:<8} {s['passed']} passed / {s['failed']} failed / {s['skipped']} skipped  (tier: {r['verified_at_boundary']})\")"
done

hr
echo "PART 2 — Interface difficulty: one axis per environment"
hr
printf "%-14s %-9s %-11s %-6s %s\n" ENV MODALITY ACTION GOAL "EPISODE END"
for e in "${ENVS[@]}"; do
  $PY -c "
import json
s = json.load(open('runs/20260726-sa5-$e/artifacts/integration/env_spec.json'))
et = s['episode_termination']
lim = et.get('truncated_at_steps') or et.get('effective_step_limit') or et.get('effective_step_limit_with_frameskip')
src = 'spec' if et.get('truncated_at_steps') else 'internal'
print(f\"{'$e':<14} {s['observation_modality']:<9} {s['action_type']:<11} {str(s['goal_conditioned']):<6} limit={lim} ({src})\")"
done

hr
echo "PART 3 — Fidelity: what a real trainer actually receives"
hr
for e in "${ENVS[@]}"; do
  $PY -c "
import json, textwrap
s = json.load(open('runs/20260726-sa5-$e/artifacts/integration/env_spec.json'))
print(f\"{'$e'}  [channel: {s['training_channel']}]\")
notes = s.get('lossy_notes') or ['(nothing dropped — trainer sees the raw env)']
for n in notes:
    for line in textwrap.wrap(n, 70):
        print('    ' + line)
print()"
done

hr
echo "PART 4 — Live rollouts through each adapter (random policy)"
hr
for e in "${ENVS[@]}"; do
  echo "── $e"
  (cd "runs/20260726-sa5-$e/artifacts/integration" && \
     $PY smoke_rollout.py 2>&1 | grep -vE 'Adroit|^A\.L\.E|^\[Powered')
done

if [[ "${1:-}" == "--train" ]]; then
  hr
  echo "PART 5 — SB3 end-to-end training smoke (interface proof, not learning)"
  hr
  (cd runs/20260726-sa5-setup && $PY train_smoke.py 2>&1 \
     | grep -vE 'Adroit|^A\.L\.E|^\[Powered|UserWarning|warnings.warn|^  ')
else
  hr
  echo "PART 5 — SB3 training smoke (cached result; re-run with --train)"
  hr
  printf "%-14s %-6s %-10s %s\n" ENV ALGO STATUS "TRAINER OBSERVATION SPACE"
  $PY -c "
import json
for r in json.load(open('runs/20260726-sa5-setup/training_smoke_results.json')):
    obs = ' '.join(r['trainer_observation_space'].split())
    print(f\"{r['env']:<14} {r['algo']:<6} {r['status']:<10} {obs[:52]}\")"
fi

hr
echo "Full overview: references/single-agent-environment-catalog.md"
echo "Nothing here claims trainability or performance; every report carries"
echo "performance_claims: none."
hr
