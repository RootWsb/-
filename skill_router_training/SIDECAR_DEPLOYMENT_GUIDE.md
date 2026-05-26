# SkillRouter Sidecar Deployment Guide

本文档描述如何将已训练的生产分类头以旁路服务接入 Agent 助手。当前服务只负责推荐
skills，不直接修改 Agent 的执行链路，因此可以先观察效果，再逐步切换。

## 1. Service Contract

服务入口：

```text
POST /v1/route
GET  /healthz
GET  /v1/skills
```

请求示例：

```json
{
  "request_id": "session-123-turn-4",
  "user_message": "请帮我实现 NocoBase 导入插件并验证权限配置",
  "available_skills": [
    "nocobase-plugin-development",
    "nocobase-acl-manage",
    "test-driven-development",
    "writing-plans"
  ],
  "baseline_skills": [
    "nocobase-plugin-development",
    "writing-plans"
  ]
}
```

响应示例：

```json
{
  "request_id": "session-123-turn-4",
  "selected_skills": [
    {"skill_name": "nocobase-plugin-development", "score": 0.9721},
    {"skill_name": "test-driven-development", "score": 0.8942}
  ],
  "selected_skill_names": [
    "nocobase-plugin-development",
    "test-driven-development"
  ],
  "threshold": 0.5,
  "top_k": 8,
  "mode": "recommendation",
  "available_skill_count": 4,
  "unknown_available_skills": [],
  "shadow_comparison": {
    "baseline_skills": ["nocobase-plugin-development", "writing-plans"],
    "retained_skills": ["nocobase-plugin-development"],
    "suggested_additions": ["test-driven-development"],
    "suggested_removals": ["writing-plans"]
  },
  "latency_ms": 18.2
}
```

`available_skills` 必须由调用方按当前 Agent 实际挂载能力传入。路由服务会在该集合内
重排和截断，避免给某个 Agent 推荐它无法执行的 skill。没有在当前 35 类模型中训练过
的新 skill 会出现在 `unknown_available_skills`，用于触发后续补标和重训。

## 2. Start Locally

从工作区根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-training.txt
python -m skill_router_training.service.app `
  --host 127.0.0.1 `
  --port 8780 `
  --audit-log skill_router_training\runtime\router_shadow_audit.jsonl
```

服务默认使用：

```text
checkpoint: skill_router_training/checkpoints/skill_router_prod/best
skill index: skill_router_training/data_prod/skill_index.json
embedding model: models/
threshold: 0.5
top_k: 8
```

默认仅从本地加载模型，不进行在线下载。GPU 部署时增加：

```powershell
--device cuda
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8780/healthz
```

## 3. Shadow Integration

第一阶段不要改变现有 skill 选择结果。可以通过两种方式旁路调用：

- 直接在 Agent 路由点调用 `POST /v1/route`。
- 安装 `skill-router-plugin/`，让插件以 `http` 模式调用本服务；这条路径更适合不改
  Agent 代码的试点。

直接调用示例：

```python
payload = {
    "request_id": turn_id,
    "user_message": user_message,
    "available_skills": mounted_skill_names,
    "baseline_skills": existing_selected_skills,
}
recommendation = post("http://127.0.0.1:8780/v1/route", json=payload, timeout=0.3)

# Shadow mode: only record recommendation and comparison metrics.
# The existing selected skills continue to drive the Agent prompt.
```

建议采集的旁路指标：

- 路由成功率、超时率、P50/P95 延迟。
- `suggested_additions` / `suggested_removals` 分布。
- 当前路由与 ML 路由的 skill 数量、token 消耗差异。
- 人工审核样本上的 precision、recall、遗漏关键 skill 比例。
- `unknown_available_skills` 数量，用于发现技能目录漂移。

审计日志默认不记录用户原文，仅记录 SHA-256、选择结果、差异和延迟。如需调试原文，
应走公司已有脱敏与权限控制流程，不要直接扩大日志字段。

## 4. Cutover Strategy

建议按以下顺序切流：

1. `shadow`：只记录推荐结果，积累真实流量人工复核集。
2. `canary`：选择低风险 Agent 或少量流量应用 ML 结果；服务失败、超时或返回空集合时回退旧路由。
3. `active`：扩大应用范围，继续保留旧路由作为故障回退。

进入 canary 前建议完成：

- 至少补充一批真实流量人工金标 holdout，而不是仅依赖现有 10 条 holdout。
- 为关键安全/运维类 skills 设定强制保留或人工策略层。
- 对服务设置本机或集群内部访问边界，不直接暴露公网。
- 固定模型版本、skill index 版本、阈值与回滚方式。

## 5. Compatibility Note

当前 checkpoint 是基于 [core/model.py](./core/model.py) 现有 embedding pooling 行为训练的。
直接上线该权重时必须保持该行为不变。若后续改用 attention-mask pooling、重设标签规则
或新增 skills，应重新训练分类头并重新做 holdout 验证后再发布。

## 6. Plugin Model Updates

插件模式下，`skill-router-plugin/runtime/models/current` 是默认模型指针目录。每次重训后
发布一个完整模型包，并通过以下任一方式生效：

- 替换 `runtime/models/current`。
- 修改插件配置 `active_model` 指向新目录。
- 保持插件不变，仅更新 `router_url` 指向已经加载新模型的 sidecar。

每个模型包必须保持 `classifier.pt`、`config.json`、`skill_index.json` 一致；如果 skill
顺序发生变化，只替换权重文件是不够的，必须同步替换 skill index。
