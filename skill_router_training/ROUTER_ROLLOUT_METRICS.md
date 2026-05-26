# SkillRouter Rollout Metrics

开启路由前后建议看两类指标：

1. 运行效果：平均选择 skill 数、每次新增/移除的 skill、失败率、延迟。
2. 质量效果：如果有人工标签，计算 precision、recall、F1、selection score、token waste。

## 1. 离线 Holdout 对比

仓库已有一组 legacy 和 ML 结果，可以直接生成示例图表：

```powershell
python skill_router_training\scripts\compare_before_after.py `
  --before skill_router_training\data_prod\legacy_prod_holdout.jsonl `
  --after skill_router_training\data_prod\ml_prod_holdout_final.jsonl `
  --output-dir artifacts\router_rollout_report_demo
```

输出：

```text
artifacts/router_rollout_report_demo/
  1_avg_selected_count.png
  2_selected_count_distribution.png
  3_selected_count_delta.png
  4_top_skill_changes.png
  5_quality_metrics.png
  6_score_waste.png
  paired_rows.csv
  summary.md
```

## 2. 真实流量对比

上线前先记录旧路由结果为 JSONL：

```json
{"request_id":"req-1","user_message":"...","selected_skills":["skill-a","skill-b"]}
```

开启 SkillRouter 插件/Sidecar 后，收集 after JSONL。可以使用：

- Sidecar audit：`skill_router_training/runtime/router_shadow_audit.jsonl`
- 插件 audit：各插件 work dir 下的 `router_audit.jsonl`
- 你自己从后台导出的路由结果 JSONL

然后运行：

```powershell
python skill_router_training\scripts\compare_before_after.py `
  --before before_router.jsonl `
  --after after_router.jsonl `
  --output-dir artifacts\router_rollout_report_real
```

如果 after 文件里包含 `shadow_comparison.baseline_skills`，也可以只传 after：

```powershell
python skill_router_training\scripts\compare_before_after.py `
  --after skill_router_training\runtime\router_shadow_audit.jsonl `
  --output-dir artifacts\router_rollout_report_shadow
```

## 3. 看图时怎么判断

- `1_avg_selected_count.png`：开启后平均 skill 数应明显下降。
- `3_selected_count_delta.png`：大多数样本应落在负数，表示减少了挂载 skill。
- `4_top_skill_changes.png`：看哪些 skill 被频繁新增/移除，用来发现策略偏差。
- `5_quality_metrics.png`：有人工标签时看 precision/recall/F1 是否提升。
- `6_score_waste.png`：有 `selection_score/token_waste_ratio` 时，score 应上升，waste 应下降。

上线阶段建议同时关注失败率和 P95 延迟。路由失败时插件应保持 `fail_open=true`，继续使用旧策略。
