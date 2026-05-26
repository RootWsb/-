# Project Structure

This workspace contains both historical experiments and the current prod SkillRouter artifacts.

## Current Prod Router

Use these paths for the production-skill experiment:

```text
skill_router_training/data_prod/
skill_router_training/checkpoints/skill_router_prod/
models/
```

Key files:

```text
skill_router_training/data_prod/training_data.jsonl
skill_router_training/data_prod/holdout.jsonl
skill_router_training/data_prod/skill_index.json
skill_router_training/data_prod/skill_catalog.json
skill_router_training/data_prod/ml_prod_holdout_final.jsonl
skill_router_training/data_prod/legacy_prod_holdout.jsonl
skill_router_training/data_prod/prod_legacy_vs_ml_report.md
skill_router_training/checkpoints/skill_router_prod/best/classifier.pt
skill_router_training/checkpoints/skill_router_prod/best/config.json
models/model.safetensors
```

Recommended prod inference parameters:

```text
threshold = 0.5
top_k = 8
```

## Code

```text
skill_router_training/core/model.py
skill_router_training/core/train.py
skill_router_training/core/visualize.py
skill_router_training/scripts/evaluate_ml.py
skill_router_training/scripts/simulate_legacy.py
skill_router_training/scripts/compare_router_outputs.py
skill_router_training/scripts/build_prod_training_set.py
skill_router_training/service/app.py
skill-router-plugin/runtime/plugin.py
```

## Active Metadata

```text
skill_router_training/data/prod_skill_catalog.json
skill_router_training/data/prod_skill_index.json
skill_router_training/data/prod_skill_comparison.md
```

The older abstract skill catalog is still kept here:

```text
skill_router_training/data/skill_catalog.json
skill_router_training/data/skill_index.json
```

## Archived Material

The `artifacts/` directory is an archive. It is not needed for normal prod inference.

```text
artifacts/raw/
artifacts/plots/
artifacts/old_skill_experiments/
artifacts/github_upload_worktree/
```

Contents:

- `artifacts/raw/测试`: original Tianleixia logs.
- `artifacts/raw/prod`: original prod team skill packages.
- `artifacts/old_skill_experiments/data`: old abstract-skill JSONL outputs and intermediate reports.
- `artifacts/plots`: older generated plot folders.
- `artifacts/github_upload_worktree`: temporary GitHub upload clone.

## Regenerate Prod Legacy vs ML Plots

On the GPU server or locally with dependencies installed:

```bash
python skill_router_training/core/visualize.py \
  --output-dir skill_router_training/plots_prod_legacy_vs_ml_en \
  --legacy-data skill_router_training/data_prod/legacy_prod_holdout.jsonl \
  --ml-data skill_router_training/data_prod/ml_prod_holdout_final.jsonl \
  --training-stats skill_router_training/checkpoints/skill_router_prod/training_stats.json
```

## Prod Inference Command

```bash
python skill_router_training/scripts/evaluate_ml.py \
  --checkpoint skill_router_training/checkpoints/skill_router_prod/best \
  --skill-index skill_router_training/data_prod/skill_index.json \
  --input skill_router_training/data_prod/holdout.jsonl \
  --output skill_router_training/data_prod/ml_prod_holdout_final.jsonl \
  --threshold 0.5 \
  --top-k 8 \
  --embedding-model models \
  --local-files-only
```

## Sidecar Router Service

To expose the trained prod classifier as a shadow-friendly internal HTTP service:

```bash
python -m skill_router_training.service.app \
  --host 127.0.0.1 \
  --port 8780 \
  --audit-log skill_router_training/runtime/router_shadow_audit.jsonl
```

The route endpoint is `POST /v1/route`. Pass the current Agent's mounted skills in
`available_skills`, and pass the existing router output in `baseline_skills` during
shadow rollout. See `skill_router_training/SIDECAR_DEPLOYMENT_GUIDE.md`.

## Plugin Wrapper

`skill-router-plugin/` packages the router integration using the same console/runtime
layout as `evolution-plugin/`.

```text
skill-router-plugin/plugin.toml
skill-router-plugin/console/plugin.py
skill-router-plugin/runtime/plugin.py
skill-router-plugin/runtime/models/current/
```

The plugin can run in `http` mode against the sidecar or `advisory` mode for a
no-risk install. Future model updates should replace `runtime/models/current` or
point the plugin config `active_model` / sidecar deployment at a new model bundle;
plugin code should remain unchanged.
