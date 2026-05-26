# SkillRouter Evolution Guide

This project currently has a supervised multi-label SkillRouter plus shadow rollout
infrastructure. The next evolution step is to turn routing decisions into
experience records that can feed review, reward analysis, and later retraining.

## Data Flow

```text
sidecar/plugin audit
  + optional task outcomes
  -> router_experience.jsonl
  -> review queue / high-confidence retraining buffer
  -> next SkillRouter checkpoint
```

## Experience Contract

Each record uses `router_experience.v1` and contains:

- `request_id`, `task_id`, `query_sha256`: privacy-safe joins back to runtime data.
- `available_skills`, `baseline_skills`, `router_selected_skills`: the router state/action.
- `scores`, `threshold`, `top_k`: model output metadata.
- `outcome`: post-task signal such as success, human correction, missing skills, or unnecessary skills.
- `reward`: bounded `[-1, 1]` score computed from the outcome.
- `learning_target_skills`: candidate label for retraining.
- `confidence`: `high`, `medium`, or `low`.
- `memory_refs`: optional IDs from the memory service once that integration exists.
- `user_message_redacted`: optional sanitized text used for incremental training.

Raw user text is intentionally not required in this contract. Training should use
`user_message_redacted` or a memory-derived sanitized summary, not secrets or raw
snapshots.

## Build Experience Records

From sidecar audit only:

```powershell
python skill_router_training\scripts\build_router_experience.py `
  --audit skill_router_training\runtime\router_shadow_audit.jsonl `
  --output skill_router_training\runtime\router_experience.jsonl
```

With outcomes:

```powershell
python skill_router_training\scripts\build_router_experience.py `
  --audit skill_router_training\runtime\router_shadow_audit.jsonl `
  --outcomes skill_router_training\runtime\router_outcomes.jsonl `
  --output skill_router_training\runtime\router_experience.jsonl
```

To build real incremental training rows in one step:

```powershell
python skill_router_training\scripts\build_real_incremental_training_data.py `
  --audit skill_router_training\runtime\router_shadow_audit.jsonl `
  --outcomes skill_router_training\runtime\router_outcomes.jsonl `
  --skill-index skill_router_training\data_prod\skill_index.json `
  --experience-output skill_router_training\runtime\router_experience.jsonl `
  --training-output skill_router_training\runtime\training_data_real_incremental.jsonl
```

Only records with a training target and redacted text become training rows. Use
`--allow-raw-user-message` only after upstream redaction has been reviewed.

Outcome rows can be keyed by `request_id`, `query_sha256`, or `task_id`:

```json
{"request_id":"req-1","status":"success","user_accepted":true}
{"request_id":"req-2","status":"partial","missing_skills":["test-driven-development"]}
{"query_sha256":"...","status":"success","unnecessary_skills":["writing-plans"]}
{"task_id":"task-4","human_corrected_skills":["systematic-debugging","test-driven-development"]}
```

Audit rows should include one of these sanitized text fields if the record will
be used for training: `user_message_redacted`, `redacted_user_message`,
`query_text_redacted`, `redacted_query_text`, or `request_summary`.

## Release Decision

After evaluating a candidate checkpoint, generate a release gate report:

```powershell
python skill_router_training\scripts\make_router_release_decision.py `
  --current skill_router_training\data_prod\ml_prod_holdout_final.jsonl `
  --candidate skill_router_training\data_prod\ml_prod_holdout_candidate.jsonl `
  --candidate-name Candidate `
  --output-md skill_router_training\data_prod\router_release_decision.md
```

The decision can be `ALLOW_SHADOW_OR_CANARY`, `MANUAL_REVIEW`, or
`BLOCK_RELEASE_OR_ROLL_BACK`. Keep the default `--min-rows 50` warning until the
holdout set is expanded beyond the current small smoke-test set.

## Memory Interface

The memory service does not need to own router evolution. It only needs to provide
state references that can be joined into router experience later:

```json
{
  "memory_refs": ["mem-project-123", "similar-task-456"],
  "project_facts": [],
  "user_preferences": [],
  "recent_similar_tasks": []
}
```

For the current router, keep this as metadata. A later model version can include
retrieved memory context in the text input or in a structured feature channel.

## Synthetic Cold Start

Export prompts from real prod `SKILL.md` files:

```cmd
python scripts\export_prod_skill_prompt_pack.py --skill-root ..\artifacts\raw\prod --skill-index data_prod\skill_index.json --output-corpus data_prod\prod_skill_corpus.json --output-prompts data_prod\synthetic_router_prompts.jsonl --num-prompts 10 --records-per-prompt 20
```

Batch-call an OpenAI-compatible external model:

```cmd
python scripts\generate_synthetic_router_records.py --prompts data_prod\synthetic_router_prompts.jsonl --api-base https://YOUR_BASE_URL/v1 --api-key YOUR_KEY --model YOUR_MODEL --output-records data_prod\synthetic_llm_records.jsonl --experience-output data_prod\synthetic_router_experience.jsonl --resume
```

For security, prefer setting the key in an environment variable:

```cmd
set LLM_API_KEY=YOUR_KEY
python scripts\generate_synthetic_router_records.py --prompts data_prod\synthetic_router_prompts.jsonl --api-base https://YOUR_BASE_URL/v1 --model YOUR_MODEL --output-records data_prod\synthetic_llm_records.jsonl --experience-output data_prod\synthetic_router_experience.jsonl --resume
```

Use synthetic data for cold start and regression coverage. Keep it separate from
real online experience, and lower its training weight once real outcomes arrive.
