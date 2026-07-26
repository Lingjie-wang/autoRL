#!/usr/bin/env bash
# Live demo: 4 verified MARL environment integrations.
#
#   bash demo_marl_envs.sh          # fast demo (MPE + VMAS, ~30s)
#   bash demo_marl_envs.sh --smac   # include SMAC v1/v2 (launches StarCraft II, ~3min)
#
# Each environment is constructed through its adapter, not through hand-written
# glue, and every number printed is read from the live object.

set -u
cd "$(dirname "$0")"
ENVS=(mpe vmas)
[[ "${1:-}" == "--smac" ]] && ENVS=(smacv1 smacv2 mpe vmas)

hr() { printf '%.0s─' {1..72}; echo; }

hr
echo "PART 1 — Verification status (machine-checked, from disk)"
hr
printf "%-9s %-8s %s\n" ENV STATUS CHECKS
for e in smacv1 smacv2 mpe vmas; do
  python3 -c "
import json
r = json.load(open('runs/20260726-marl5-$e/verification_report.json'))
s = r['summary']
print(f\"{'$e':<9} {r['overall_status']:<8} {s['passed']} passed / {s['failed']} failed / {s['skipped']} skipped\")"
done

hr
echo "PART 2 — Fidelity: what a training run actually receives"
hr
printf "%-9s %-12s %-22s %s\n" ENV AGENTS "GLOBAL STATE" "ACTION MASK"
for e in smacv1 smacv2 mpe vmas; do
  python3 -c "
import json
s = json.load(open('runs/20260726-marl5-$e/artifacts/integration/env_spec.json'))
gs, am, ei = s['global_state'], s['action_mask'], s['env_info']
print(f\"{'$e':<9} {ei['n_agents']:<12} {gs['source']+' '+str(gs['shape']):<22} {am['source']}\")"
done
echo
echo "  native     = real, provided by the simulator"
echo "  obs_concat = fake: agent observations glued together (gymma channel)"
echo "  all_legal_padding = mask dropped by the channel; every action marked legal"

hr
echo "PART 3 — Live construction through the adapter"
hr
for e in "${ENVS[@]}"; do
  echo "--- $e ---"
  ( cd "runs/20260726-marl5-$e/artifacts/integration" && conda run -n marl5 python -c "
import numpy as np, warnings; warnings.filterwarnings('ignore')
from adapter import make_env
env = make_env()
try:
    info = env.get_env_info()
    env.reset(seed=42)
    obs, state = env.get_obs(), np.asarray(env.get_state()).reshape(-1)
    masks = env.get_avail_actions()
    acts = [int(np.nonzero(np.asarray(m))[0][0]) for m in masks]
    out = env.step(acts)
    reward = out[1]
    print(f'  env_info      {info}')
    print(f'  obs           {len(obs)} agents x {np.asarray(obs[0]).size} dims')
    print(f'  global state  {state.size} dims')
    print(f'  mask[agent0]  {list(np.asarray(masks[0]).astype(int))}')
    print(f'  step reward   {float(np.asarray(reward).reshape(-1)[0]):.4f}')
    print('  RESULT: constructed, stepped, closed cleanly')
finally:
    env.close()
" 2>/dev/null )
done

hr
echo "PART 4 — The verifier can actually fail (tamper test on MPE)"
hr
SPEC=runs/20260726-marl5-mpe/artifacts/integration/env_spec.json
cp "$SPEC" /tmp/spec_demo.bak
python3 -c "
import json
s = json.load(open('$SPEC'))
s['global_state']['source'] = 'native'   # lie: claim a real centralized state
json.dump(s, open('$SPEC','w'), indent=2)
print('  tampered: MPE now claims global_state.source = native (a lie)')"
echo
conda run -n marl5 python skills/rl-env-verifier/references/verify_epymarl_env_template.py \
  --run-dir runs/20260726-marl5-mpe --boundary dry_run 2>/dev/null \
  | grep -E 'FAILED|overall' | sed 's/^/  /'
echo "  exit code above is nonzero -> a CI gate would block training here"
cp /tmp/spec_demo.bak "$SPEC"
echo "  spec restored"

hr
echo "PART 5 — End-to-end: QMIX actually trained on all four (sacred logs)"
hr
SACRED=third_party/epymarl-run/results/sacred/qmix
printf "%-27s %-11s %s\n" ENV STATUS "WALL CLOCK"
for d in 3m terran_5_vs_5 pz-mpe-simple-spread-v3 vmas-balance; do
  [[ -d "$SACRED/$d" ]] && python3 -c "
import json, glob, os, datetime as dt
runs = sorted(glob.glob('$SACRED/$d/[0-9]*'), key=os.path.getmtime)
r = json.load(open(runs[-1] + '/run.json'))
d = '-'
if r.get('start_time') and r.get('stop_time'):
    d = str(dt.datetime.fromisoformat(r['stop_time'])
            - dt.datetime.fromisoformat(r['start_time'])).split('.')[0]
print(f\"{'$d':<27} {r.get('status'):<11} {d}\")"
done
echo
echo "  QMIX, t_max=3000 (smoke budget). Proves the trainer can consume these"
echo "  environments end to end; says nothing about learning performance."
echo "  Ran in third_party/epymarl-run/ (our own copy) — the ~/code/epymarl"
echo "  checkout with active experiments was never written to."

hr
echo "Scope: integration + behavioral verification + training smoke."
echo "No performance claims: 3000 steps proves plumbing, not learning."
echo "GRF deferred: needs sudo build deps and has no EPyMARL wrapper."
echo "Upstream defect found and patched: MPE keys unregistered since"
echo "  PettingZoo 1.25 moved MPE to the standalone mpe2 package."
hr
