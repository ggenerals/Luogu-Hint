"""
Prompt 管理模块

加载和管理用于生成 Hint 的 Prompt 模板
"""

from pathlib import Path
from typing import Optional


class PromptManager:
    """Prompt 管理器"""

    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        初始化 Prompt 管理器

        Args:
            prompts_dir: Prompt 文件目录
        """
        if prompts_dir is None:
            prompts_dir = Path("prompts")
        self.prompts_dir = prompts_dir
        self._cache: dict[str, str] = {}

    def _get_prompt_path(self, version: str) -> Path:
        """获取 Prompt 文件路径"""
        return self.prompts_dir / f"hint_{version}.txt"

    def load_prompt(self, version: str = "v1") -> str:
        """
        加载指定版本的 Prompt

        Args:
            version: Prompt 版本

        Returns:
            Prompt 文本
        """
        if version in self._cache:
            return self._cache[version]

        prompt_path = self._get_prompt_path(version)

        if not prompt_path.exists():
            # 如果文件不存在，使用默认 Prompt
            prompt = self._get_default_prompt()
        else:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt = f.read()

        self._cache[version] = prompt
        return prompt

    def _get_default_prompt(self) -> str:
        """获取默认 Prompt"""
        return """你是一位经验丰富的信息学竞赛教练。请根据以下题目和题解内容，生成 5 个逐级递进的提示（Hint），帮助学生独立思考并解决这道题目。

## 题目信息

{title}

## 题目描述

{statement}

## 题解参考

{solutions}

## 要求

请生成 5 个思维难度层层递进的提示：

1. **Level 1** - 只提供思考方向，不得直接给出算法或具体做法。字数控制在 50 字以内。
2. **Level 2** - 指出关键观察点或重要性质。字数控制在 50 字以内。
3. **Level 3** - 给出算法方向或解题思路。字数控制在 50 字以内。
4. **Level 4** - 提供核心算法、状态定义或关键转移。字数控制在 50 字以内。
5. **Level 5** - 接近完整解法，但保留少量细节让学生思考。字数控制在 50 字以内。

## 注意事项

- 提示必须基于题目内容，不得编造题目条件、样例或限制。
- 提示应该循序渐进，每一级都比前一级提供更具体的信息。
- 不要过度简化或复述题意，重点是引导学生思考。
- 如果题解有错误，不要无条件照抄。

## 输出格式

请严格按照以下 JSON 格式输出（不要包含其他内容）：

```json
{{
  "hints": [
    {{"level": 1, "content": "提示内容 1"}},
    {{"level": 2, "content": "提示内容 2"}},
    {{"level": 3, "content": "提示内容 3"}},
    {{"level": 4, "content": "提示内容 4"}},
    {{"level": 5, "content": "提示内容 5"}}
  ]
}}
```"""

    def build_prompt(
        self,
        title: str,
        statement: str,
        solutions: list[str],
        version: str = "v1"
    ) -> str:
        """
        构建完整的 Prompt

        Args:
            title: 题目标题
            statement: 题目描述
            solutions: 题解列表
            version: Prompt 版本

        Returns:
            完整的 Prompt 文本
        """
        template = self.load_prompt(version)

        solutions_text = ""
        for i, sol in enumerate(solutions, 1):
            solutions_text += f"\n### 题解 {i}\n\n{sol}\n\n"

        return template.format(
            title=title,
            statement=statement,
            solutions=solutions_text
        )


# 全局实例
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """获取全局 Prompt 管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
