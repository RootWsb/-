# Tianleixia Skill Router Training Package

This repository contains the minimal files needed to train and evaluate the Tianleixia first-layer SkillRouter on a GPU server.

Start here:

```bash
cd ~
git clone https://github.com/RootWsb/-.git UguardAgentRL
cd UguardAgentRL
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-training.txt
```

Then train:

```bash
python skill_router_training/core/train.py \
  --data skill_router_training/data/training_data_tianleixia_first_layer.jsonl \
  --output skill_router_training/checkpoints/skill_router_tianleixia_first_layer \
  --epochs 10 \
  --batch-size 16 \
  --lr 0.0001 \
  --device cuda
```

See `skill_router_training/SERVER_TRAINING_GUIDE.md` for the full workflow.
