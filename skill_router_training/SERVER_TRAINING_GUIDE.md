# Server Training Guide

This guide assumes VS Code Remote SSH is already connected to the GPU server.

## 1. Open a Server Folder

In the remote VS Code window:

1. Click `File -> Open Folder`.
2. Choose or create a workspace folder, for example:

```bash
mkdir -p ~/UguardAgentRL
cd ~/UguardAgentRL
```

If VS Code asks whether to trust the folder, choose trust only if this is your company server/workspace.

## 2. Upload Project Files

Upload at least these paths from your local project:

```text
skill_router_training/
requirements-training.txt
```

The `测试/` folder is not needed for training if the extracted JSONL files already exist under
`skill_router_training/data/`.

Recommended ways:

- In VS Code Remote Explorer, drag local files/folders into the remote folder.
- Or use local PowerShell:

```powershell
scp -r skill_router_training requirements-training.txt uguard-gpu:~/UguardAgentRL/
```

Replace `uguard-gpu` with the SSH host alias from your VS Code SSH config if needed.

## 3. Check GPU and Python

Run these commands in the VS Code remote terminal:

```bash
cd ~/UguardAgentRL
nvidia-smi
python3 --version
```

If `python3` is unavailable, try:

```bash
python --version
```

## 4. Create Environment

Using venv:

```bash
cd ~/UguardAgentRL
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-training.txt
```

If the server uses Conda:

```bash
conda create -n skill-router python=3.10 -y
conda activate skill-router
pip install -r requirements-training.txt
```

## 5. Verify CUDA in PyTorch

```bash
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("cuda version:", torch.version.cuda)
print("device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")
PY
```

If `cuda available` is `False`, stop and ask the server admin which CUDA/PyTorch environment should be used.

## 6. Train First-Layer Router

```bash
cd ~/UguardAgentRL
source .venv/bin/activate
python skill_router_training/core/train.py \
  --data skill_router_training/data/training_data_tianleixia_first_layer.jsonl \
  --output skill_router_training/checkpoints/skill_router_tianleixia_first_layer \
  --epochs 10 \
  --batch-size 16 \
  --lr 0.0001 \
  --device cuda
```

First run may download `Qwen/Qwen3-Embedding-0.6B` from Hugging Face. If the server cannot access Hugging Face,
download the model on a machine with access and upload it, then adjust `embedding_model` in the saved config or code.

## 7. Evaluate Holdout

```bash
python skill_router_training/scripts/evaluate_ml.py \
  --checkpoint skill_router_training/checkpoints/skill_router_tianleixia_first_layer/best \
  --input skill_router_training/data/tianleixia_gold_holdout.jsonl \
  --output skill_router_training/data/ml_tianleixia_gold_holdout_retrained.jsonl \
  --threshold 0.5 \
  --top-k 5

python skill_router_training/scripts/apply_first_layer_policy.py \
  --input skill_router_training/data/ml_tianleixia_gold_holdout_retrained.jsonl \
  --output skill_router_training/data/ml_tianleixia_gold_holdout_retrained_policy.jsonl

python skill_router_training/scripts/compare_router_outputs.py \
  --run Retrained_ML=skill_router_training/data/ml_tianleixia_gold_holdout_retrained.jsonl \
  --run Retrained_ML_policy=skill_router_training/data/ml_tianleixia_gold_holdout_retrained_policy.jsonl \
  --output-md skill_router_training/data/tianleixia_holdout_retrained_comparison.md \
  --output-csv skill_router_training/data/tianleixia_holdout_retrained_comparison.csv
```

## 8. Bring Results Back

Download these paths:

```text
skill_router_training/checkpoints/skill_router_tianleixia_first_layer/
skill_router_training/data/ml_tianleixia_gold_holdout_retrained.jsonl
skill_router_training/data/ml_tianleixia_gold_holdout_retrained_policy.jsonl
skill_router_training/data/tianleixia_holdout_retrained_comparison.md
skill_router_training/data/tianleixia_holdout_retrained_comparison.csv
```

Example from local PowerShell:

```powershell
scp -r uguard-gpu:~/UguardAgentRL/skill_router_training/checkpoints/skill_router_tianleixia_first_layer skill_router_training/checkpoints/
scp uguard-gpu:~/UguardAgentRL/skill_router_training/data/tianleixia_holdout_retrained_comparison.* skill_router_training/data/
```
