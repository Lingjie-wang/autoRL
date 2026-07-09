# Dependency And Download Boundary

Use this guide before running any command that changes dependencies, downloads files, or clones repositories.

## Execution Boundary

`generate_only`:

- Do not install, clone, download, or run training.
- Write planned commands only.
- Generate code/configs only when allowed target paths are clear.

`dry_run`:

- May inspect installed packages and run import/config/env-construction checks.
- May run a one-step rollout only when dependencies are already available and the environment has no external side effects.
- Do not install, clone, download large assets, or run training unless separately approved.

`runtime_allowed`:

- May run bounded smoke training only after dependencies are satisfied.
- Still requires explicit approval for dependency installation, cloning, large downloads, remote compute, or full experiments.

## Approval Required

Always require explicit approval before:

- `git clone`
- `pip install`, `conda install`, package-manager writes
- downloading large models, datasets, paper corpora, simulator assets, or game binaries
- using remote GPUs/cloud spend
- full training runs
- writing outside the workspace or approved target paths
- copying third-party source into project-owned code

## Dependency Plan Contents

Write `dependency_plan.md` before any approval-required action.

Required sections:

- current environment summary: Python, package manager, GPU availability if relevant
- selected framework and reason
- commands proposed
- target install/clone paths
- version pins or commit pins when known
- expected disk/network/runtime cost
- license and maintenance risk
- rollback or cleanup notes
- approval status: `not_required`, `pending`, `approved`, or `blocked`

## Clone Policy

When cloning is approved:

- clone into `third_party/<repo-slug>` unless the user specified another path
- record repository URL, branch/tag, and commit SHA
- do not edit third-party code unless the task explicitly requires it
- prefer wrappers, config files, or small patches in project-owned files

## Install Policy

When installation is approved:

- prefer the existing project package manager
- avoid global installs
- record commands and outputs in `install_log.md`
- run the smallest import/version check after install
- do not upgrade unrelated packages unless required and approved

## Failure Handling

If dependency setup fails:

- stop before broad retries
- record exact command and error
- identify whether the blocker is network, permissions, version conflict, missing system package, GPU/CUDA, simulator license, or unsupported platform
- propose the smallest next action
