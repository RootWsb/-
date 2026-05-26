"""
DataCollector 抽象基类

每个 Agent 项目实现此接口，即可接入 Skill Router 训练流水线。
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List


class DataCollector(ABC):
    """
    Agent 数据收集器接口。

    每个 Agent 项目需要实现三个方法：
    1. get_skills_catalog() — 返回 skill 目录文本（供 LLM 合成数据用）
    2. get_available_skills() — 返回所有可用 skill 名称列表
    3. collect_query_skills_pairs() — 收集真实 (query, selected_skills) 对
    """

    @abstractmethod
    def get_skills_catalog(self) -> str:
        """
        返回 skill 目录文本，格式为每行一个 "- skill-name: description"。

        用于 synthetic_data_generator 的 prompt，让 LLM 知道有哪些 skill 可选。

        Returns:
            多行文本，每行格式："- skill-name: skill 描述"
        """
        ...

    @abstractmethod
    def get_available_skills(self) -> List[str]:
        """
        返回所有可用 skill 的名称列表。

        Returns:
            ["skill-name-1", "skill-name-2", ...]
        """
        ...

    @abstractmethod
    def collect_query_skills_pairs(self, num_samples: int = 100) -> List[Dict]:
        """
        收集真实 (query, selected_skills) 对。

        该方法应模拟或调用 Agent 的 skill 选择逻辑，
        对一组 query 返回 Agent 实际选择的 skills。

        Args:
            num_samples: 要收集的样本数量

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
        ...

    def get_config(self) -> Dict:
        """
        返回适配器的配置信息（可选覆盖）。

        Returns:
            {"agent_name": "...", "skills_dir": "...", ...}
        """
        return {
            "agent_name": self.__class__.__name__,
        }
