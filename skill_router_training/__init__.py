"""
Skill Router Training — 独立可复用的 Skill 路由训练工具包。

通过适配器模式支持任意 Agent 项目接入。

快速开始：
    from skill_router_training import SkillRouter, DataCollector
    from skill_router_training.adapters.zvagent import ZVAgentCollector

    collector = ZVAgentCollector(agent_root="path/to/ZVagent")
    # ... 使用 core 模块训练模型
"""
