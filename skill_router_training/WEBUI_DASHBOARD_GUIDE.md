# SkillRouter WebUI Dashboard

这个 WebUI 直接挂在 SkillRouter sidecar 上，用来集中管理路由策略、接收插件上报事件，并形成实时图表。

## 1. 启动 sidecar 和 WebUI

```powershell
python -m skill_router_training.service.app `
  --checkpoint skill_router_training\checkpoints\skill_router_prod\best `
  --skill-index skill_router_training\data_prod\skill_index.json `
  --embedding-model models `
  --host 127.0.0.1 `
  --port 8780 `
  --dashboard-dir skill_router_training\runtime\dashboard
```

打开：

```text
http://127.0.0.1:8780/ui/
```

## 2. 插件参数

后台插件建议增加或确认这些参数：

```text
report_events = true
dashboard_event_url = http://127.0.0.1:8780/v1/dashboard/events
router_url = http://127.0.0.1:8780/v1/route
```

如果 Agent 和 sidecar 不在同一台机器，把 `127.0.0.1` 换成 sidecar 所在机器的内网 IP。

## 3. 中央策略

WebUI 的运行策略会保存到：

```text
skill_router_training/runtime/dashboard/policy.json
```

字段含义：

- `routing_enabled`：关闭后 sidecar 不再给出 skill 推荐，插件会自然回到旧策略。
- `enforce_parameters`：开启后，以 WebUI 的 `threshold/top_k` 为准，覆盖插件上传的参数。
- `threshold`：推荐阈值。
- `top_k`：最多推荐的 skill 数。

## 4. 事件日志

插件上报的脱敏事件会保存到：

```text
skill_router_training/runtime/dashboard/plugin_events.jsonl
```

事件只保存：

- `request_id`
- `query_sha256` 或插件侧请求标识
- 推荐 skill
- before/after 的 `shadow_comparison`
- 延迟、错误、跳过原因
- active model 路径

不会保存原始用户请求文本。

## 5. 图表含义

- 平均选择数量：开启路由前后的平均 skill 数。
- 请求趋势：每次请求的 before/after 数量变化。
- Skill 变化排行：哪些 skill 经常被新增或移除。
- 延迟：router 和 plugin 两段耗时的 P50/P95。

上线初期建议打开 `report_events` 和 `fail_open`，先让 WebUI 收集真实流量，再决定是否开启 `enforce_parameters` 做中央策略接管。
