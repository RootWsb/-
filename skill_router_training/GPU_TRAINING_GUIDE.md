# GPU Training Guide

This guide trains an experimental SkillRouter checkpoint from the mixed real plus
synthetic dataset. Do not overwrite the current production checkpoint until the
new checkpoint passes holdout evaluation.

## Data

Recommended training file:

```text
skill_router_training/data_prod/training_data_mixed_1000.jsonl
```

It contains:

- 619 real prod rows with `sample_weight=1.0`
- 961 synthetic router-evolution rows with lower `sample_weight`

The training script supports `sample_weight` and applies it to the BCE loss.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-training.txt
```

If CUDA fails with a message like `The NVIDIA driver on your system is too old`
and the reported driver API version is `12040`, keep the server driver as-is and
install the CUDA 12.4 PyTorch wheel:

```bash
python -m pip uninstall -y torch torchvision torchaudio
python -m pip install -r requirements-torch-cu124.txt
python -m pip install -r requirements-training.txt
```

Then verify CUDA before training:

```bash
python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

If the server cannot access Hugging Face, download the embedding model from
ModelScope first:

```bash
python skill_router_training/scripts/download_modelscope_embedding.py \
  --model-id Qwen/Qwen3-Embedding-0.6B \
  --output-dir models/Qwen3-Embedding-0.6B
```

## Train

If the GPU server can download Hugging Face models:

```bash
python skill_router_training/core/train.py \
  --data skill_router_training/data_prod/training_data_mixed_1000.jsonl \
  --output skill_router_training/checkpoints/skill_router_prod_synth_1000 \
  --epochs 50 \
  --batch-size 50 \
  --lr 0.0001 \
  --device cuda \
  --embedding-model Qwen/Qwen3-Embedding-0.6B
```

If the embedding model is already copied to a local `models/` directory:

```bash
python skill_router_training/core/train.py \
  --data skill_router_training/data_prod/training_data_mixed_1000.jsonl \
  --output skill_router_training/checkpoints/skill_router_prod_synth_1000 \
  --epochs 50 \
  --batch-size 50 \
  --lr 0.0001 \
  --device cuda \
  --embedding-model models/Qwen3-Embedding-0.6B \
  --local-files-only
```

If GPU memory is tight, reduce `--batch-size` to `32`.

## Evaluate

```bash
python skill_router_training/scripts/evaluate_ml.py \
  --checkpoint skill_router_training/checkpoints/skill_router_prod_synth_1000/best \
  --skill-index skill_router_training/data_prod/skill_index.json \
  --input skill_router_training/data_prod/holdout.jsonl \
  --output skill_router_training/data_prod/ml_prod_holdout_synth_1000.jsonl \
  --threshold 0.5 \
  --top-k 8 \
  --embedding-model models/Qwen3-Embedding-0.6B \
  --local-files-only
```

Compare against the current production result before publishing:

```bash
python skill_router_training/scripts/compare_router_outputs.py \
  --run Legacy=skill_router_training/data_prod/legacy_prod_holdout.jsonl \
  --run CurrentML=skill_router_training/data_prod/ml_prod_holdout_final.jsonl \
  --run Synth1000=skill_router_training/data_prod/ml_prod_holdout_synth_1000.jsonl \
  --output-md skill_router_training/data_prod/prod_synth_1000_report.md \
  --output-csv skill_router_training/data_prod/prod_synth_1000_report.csv
```
