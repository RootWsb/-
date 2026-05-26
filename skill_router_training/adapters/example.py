"""
其他 Agent 适配器模板

复制此文件并实现三个核心方法，即可接入 Skill Router 训练流水线。
"""

from typing import Dict, List

from adapters.base import DataCollector


class ExampleCollector(DataCollector):
    """
    示例适配器 — 展示如何为你的 Agent 实现 DataCollector 接口。

    使用方式：
        collector = ExampleCollector()
        catalog = collector.get_skills_catalog()
        skills = collector.get_available_skills()
        pairs = collector.collect_query_skills_pairs(num_samples=50)
    """

    def __init__(self, skills_dir: str = ""):
        """
        Args:
            skills_dir: 你的 Agent 的 skill 目录路径
        """
        self.skills_dir = skills_dir

    def get_skills_catalog(self) -> str:
        """
        返回 skill 目录文本，每行格式："- skill-name: description"

        根据你的 Agent 的 skill 描述格式实现。
        例如你的 skill 用 JSON/YAML/Markdown 描述，解析后返回即可。
        """
        # TODO: 读取你的 skill 目录并生成 catalog
        # 示例（假设你的 skill 在 skills_dir 下，每个子目录有一个 manifest.json）：
        #
        # import json
        # catalog_lines = []
        # for skill_dir in Path(self.skills_dir).iterdir():
        #     if not skill_dir.is_dir():
        #         continue
        #     manifest = skill_dir / "manifest.json"
        #     if manifest.exists():
        #         with open(manifest) as f:
        #             info = json.load(f)
        #         catalog_lines.append(f"- {info['name']}: {info['description']}")
        # return "\n".join(catalog_lines)
        raise NotImplementedError("请实现 get_skills_catalog()")

    def get_available_skills(self) -> List[str]:
        """
        返回所有可用 skill 的名称列表。
        """
        # TODO: 返回你的 Agent 支持的所有 skill 名称
        # 示例：
        # return [d.name for d in Path(self.skills_dir).iterdir() if d.is_dir()]
        raise NotImplementedError("请实现 get_available_skills()")

    def collect_query_skills_pairs(self, num_samples: int = 100) -> List[Dict]:
        """
        收集真实 (query, selected_skills) 对。

        你应该：
        1. 准备一组代表性的用户 query（可以从 synthetic data 或真实日志中获取）
        2. 调用你的 Agent 的 skill 选择逻辑
        3. 记录每个 query 选择了哪些 skill

        Returns:
            [
                {
                    "user_message": "用户问题文本",
                    "selected_skills": ["skill-a", "skill-b"],
                    "available_skills": ["skill-a", "skill-b", ...],
                },
                ...
            ]
        """
        # TODO: 实现你的 Agent 的数据收集逻辑
        #
        # 伪代码：
        # queries = load_queries(...)  # 从文件或 API 获取 query 列表
        # available = self.get_available_skills()
        # results = []
        # for query in queries[:num_samples]:
        #     selected = your_agent.select_skills(query)
        #     results.append({
        #         "user_message": query,
        #         "selected_skills": selected,
        #         "available_skills": available,
        #     })
        # return results
        raise NotImplementedError("请实现 collect_query_skills_pairs()")

    def get_config(self) -> Dict:
        return {
            "agent_name": "ExampleAgent",
            "skills_dir": self.skills_dir,
        }
