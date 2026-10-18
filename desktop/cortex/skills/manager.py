"""
Cortex OpenClaw-Style Modular Skill System Manager
Parses SKILL.md specifications in cortex/skills/*/SKILL.md,
extracting metadata, required tools, triggers, and execution prompts.
"""

import os
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class Skill:
    id: str
    name: str
    description: str
    tools: List[str]
    instructions: str
    filepath: str


class SkillManager:
    def __init__(self, skills_dir: Optional[str] = None):
        self.skills_dir = skills_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")
        self.skills: Dict[str, Skill] = {}
        self.reload_skills()

    def reload_skills(self):
        self.skills.clear()
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir, exist_ok=True)
            return

        for entry in os.listdir(self.skills_dir):
            skill_folder = os.path.join(self.skills_dir, entry)
            skill_md = os.path.join(skill_folder, "SKILL.md")
            if os.path.isdir(skill_folder) and os.path.exists(skill_md):
                skill = self._parse_skill_md(entry, skill_md)
                if skill:
                    self.skills[skill.id] = skill

    def _parse_skill_md(self, skill_id: str, filepath: str) -> Optional[Skill]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse frontmatter if present
            name = skill_id
            description = ""
            tools: List[str] = []
            instructions = content

            frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if frontmatter_match:
                fm_text, instructions = frontmatter_match.groups()
                for line in fm_text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip().lower()
                        v = v.strip().strip('"\'')
                        if k == "name":
                            name = v
                        elif k == "description":
                            description = v
                        elif k == "tools":
                            tools = [t.strip() for t in v.split(",") if t.strip()]

            if not description:
                # First non-empty line after headers
                lines = [l.strip() for l in instructions.splitlines() if l.strip() and not l.startswith("#")]
                description = lines[0] if lines else f"Skill {name}"

            return Skill(
                id=skill_id,
                name=name,
                description=description,
                tools=tools,
                instructions=instructions.strip(),
                filepath=filepath
            )
        except Exception as e:
            print(f"[SkillManager] Failed to parse skill {filepath}: {e}")
            return None

    def get_skill_catalog_prompt(self) -> str:
        """Constructs concise prompt section listing all available skills."""
        if not self.skills:
            return ""

        lines = ["[MODULAR SKILLS INVENTORY]"]
        for sid, s in self.skills.items():
            tool_str = f" (Tools: {', '.join(s.tools)})" if s.tools else ""
            lines.append(f"- {s.name} (`{sid}`): {s.description}{tool_str}")
        lines.append("")
        return "\n".join(lines)

    def get_skill_instructions(self, skill_id: str) -> Optional[str]:
        skill = self.skills.get(skill_id)
        return skill.instructions if skill else None
