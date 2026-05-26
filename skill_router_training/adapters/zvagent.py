"""
ZVAgent 适配器

从 ZVAgent 项目收集 skill 选择数据，供 Skill Router 训练使用。

使用方式：
    from adapters.zvagent import ZVAgentCollector
    collector = ZVAgentCollector(agent_root="path/to/ZVagent")
    catalog = collector.get_skills_catalog()
    skills = collector.get_available_skills()
    pairs = collector.collect_query_skills_pairs(num_samples=50)
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from adapters.base import DataCollector
from core.utils import load_jsonl


class ZVAgentCollector(DataCollector):
    """
    ZVAgent 数据收集器。

    自动发现 ZVAgent/skills/ 目录下的 SKILL.md 文件，
    并可启动 ZVAgent 实例收集真实 skill 选择数据。
    """

    def __init__(
        self,
        agent_root: str,
        skills_dir: Optional[str] = None,
    ):
        """
        初始化 ZVAgent 适配器。

        Args:
            agent_root: ZVagent 包根目录（包含 skills/, agent/, config.json 等）
            skills_dir: skills 目录路径（可选，默认为 agent_root/skills/）
        """
        self.agent_root = Path(agent_root)
        self.skills_dir = Path(skills_dir) if skills_dir else self.agent_root / "skills"

    def get_skills_catalog(self) -> str:
        """
        从 ZVAgent/skills/ 目录读取所有 skill 的名称和描述，
        生成 catalog 文本供 LLM 合成数据使用。

        支持 SKILL.md 的 YAML frontmatter 格式：
            ---
            description: 这个 skill 做什么
            ---

        Returns:
            多行文本，每行："- skill-name: description"
        """
        catalog_lines = []

        if not self.skills_dir.exists():
            return ""

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            name = skill_dir.name
            description = ""
            try:
                content = skill_md.read_text(encoding="utf-8")
                lines = content.split("\n")
                in_frontmatter = False
                for line in lines:
                    stripped = line.strip()
                    if stripped == "---":
                        in_frontmatter = not in_frontmatter
                        continue
                    if in_frontmatter and stripped.startswith("description:"):
                        description = stripped[len("description:"):].strip()[:150]
                        break
                    if not in_frontmatter and stripped and not stripped.startswith("#"):
                        description = stripped[:150]
                        break
            except Exception:
                pass

            catalog_lines.append(f"- {name}: {description}")

        return "\n".join(catalog_lines)

    def get_available_skills(self) -> List[str]:
        """
        返回 ZVAgent 中所有可用的 skill 名称。

        Returns:
            ["ai-tech-digest", "arxiv-copilot", ...]
        """
        skills = []
        if not self.skills_dir.exists():
            return skills

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            if (skill_dir / "SKILL.md").exists():
                skills.append(skill_dir.name)

        return skills

    def collect_query_skills_pairs(self, num_samples: int = 100) -> List[Dict]:
        """
        启动 ZVAgent 实例，对 synthetic_data 中的 query 收集 skill 选择结果。

        需要 ZVAgent 的 config.json 已正确配置。

        Args:
            num_samples: 最大收集数量

        Returns:
            [{user_message, selected_skills, available_skills}, ...]
        """
        # 初始化 ZVAgent
        agent = self._initialize_agent()
        available_skills = [e.skill.name for e in agent.skill_manager.list_skills()]

        # 尝试加载 synthetic data 作为 query 来源
        synthetic_path = self.agent_root / "training" / "skill_router" / "synthetic_data.jsonl"
        data = load_jsonl(str(synthetic_path))

        dataset = []
        for i, item in enumerate(data[:num_samples]):
            query = item.get("user_message", "")
            if not query:
                continue

            try:
                selected_skills = agent.skill_manager.select_relevant_skills(query)
                dataset.append({
                    "user_message": query,
                    "selected_skills": selected_skills,
                    "available_skills": available_skills,
                })
            except Exception as e:
                print(f"  X 收集失败: {query[:50]}... - {e}")

        return dataset

    def _initialize_agent(self):
        """
        初始化 ZVAgent 实例（内部方法）。

        Returns:
            Agent 实例
        """
        project_root = self.agent_root

        # config.load_config() reads ./config.json from CWD
        original_cwd = os.getcwd()
        os.chdir(project_root)
        try:
            from config import load_config
            load_config()

            from agent.protocol import Agent
            from agent.tools import ToolManager
            from agent.skills import SkillManager

            tool_manager = ToolManager()
            tools = tool_manager.load_tools()

            skill_manager = SkillManager()

            agent = Agent(
                system_prompt="You are a helpful assistant.",
                tools=tools,
                skill_manager=skill_manager,
                enable_skills=True,
            )

            return agent
        finally:
            os.chdir(original_cwd)

    def get_config(self) -> Dict:
        return {
            "agent_name": "ZVAgent",
            "agent_root": str(self.agent_root),
            "skills_dir": str(self.skills_dir),
            "num_skills": len(self.get_available_skills()),
        }
