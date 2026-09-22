"""
Hint 验证模块

验证 LLM 生成的 Hint 是否符合要求
"""

import json
from typing import Optional, Any
from .models import Hint
from .errors import ValidationError


class HintValidator:
    """Hint 验证器"""

    MAX_HINT_LENGTH = 200  # 单条 Hint 最大长度
    MIN_HINT_COUNT = 5     # 最少 Hint 数量
    MAX_HINT_COUNT = 5     # 最多 Hint 数量

    def validate_json(self, text: str) -> Optional[dict]:
        """
        验证并解析 JSON 输出

        Args:
            text: LLM 输出的文本

        Returns:
            解析后的字典，如果验证失败返回 None
        """
        try:
            # 尝试直接解析
            data = json.loads(text)
            return self._validate_structure(data)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 部分
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._validate_structure(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # 尝试从代码块中提取
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_block_match:
            try:
                data = json.loads(code_block_match.group(1))
                return self._validate_structure(data)
            except (json.JSONDecodeError, ValueError):
                pass

        return None

    def _validate_structure(self, data: dict) -> Optional[dict]:
        """验证 JSON 结构"""
        if not isinstance(data, dict):
            return None

        if "hints" not in data:
            return None

        hints = data["hints"]
        if not isinstance(hints, list):
            return None

        if len(hints) < self.MIN_HINT_COUNT or len(hints) > self.MAX_HINT_COUNT:
            return None

        # 验证每个 Hint
        validated_hints = []
        for i, hint in enumerate(hints):
            validated_hint = self._validate_single_hint(hint, i + 1)
            if validated_hint is None:
                return None
            validated_hints.append(validated_hint)

        return {"hints": validated_hints}

    def _validate_single_hint(self, hint: Any, expected_level: int) -> Optional[dict]:
        """验证单个 Hint"""
        if not isinstance(hint, dict):
            return None

        # 检查 level
        level = hint.get("level")
        if level is None:
            # 如果没有 level 字段，使用位置
            level = expected_level

        if not isinstance(level, int) or level < 1 or level > 5:
            return None

        # 检查 content
        content = hint.get("content", "")
        if not isinstance(content, str):
            return None

        content = content.strip()
        if not content:
            return None

        if len(content) > self.MAX_HINT_LENGTH:
            # 超长警告但不失败
            content = content[:self.MAX_HINT_LENGTH] + "..."

        return {"level": level, "content": content}

    def parse_line_format(self, text: str) -> Optional[dict]:
        """
        解析旧版行格式输出

        格式：提示 xxx：xxx

        Args:
            text: LLM 输出的文本

        Returns:
            解析后的字典，如果验证失败返回 None
        """
        import re

        hints = []
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 匹配 "提示 x：内容" 或 "提示 x: 内容"
            match = re.match(r'提示\s*(\d+)\s*[:：]\s*(.+)', line)
            if match:
                level = int(match.group(1))
                content = match.group(2).strip()
                if content and 1 <= level <= 5:
                    hints.append({"level": level, "content": content})

        if len(hints) == 5:
            # 确保 level 是 1-5
            levels = {h["level"] for h in hints}
            if levels == {1, 2, 3, 4, 5}:
                return {"hints": sorted(hints, key=lambda x: x["level"])}

        return None

    def validate(self, text: str) -> list[Hint]:
        """
        完整验证流程

        Args:
            text: LLM 输出的文本

        Returns:
            Hint 列表

        Raises:
            ValidationError: 验证失败时抛出
        """
        # 尝试 JSON 格式
        result = self.validate_json(text)
        if result:
            return [
                Hint(
                    problem_id="",  # 稍后设置
                    level=h["level"],
                    content=h["content"]
                )
                for h in result["hints"]
            ]

        # 尝试行格式
        result = self.parse_line_format(text)
        if result:
            return [
                Hint(
                    problem_id="",
                    level=h["level"],
                    content=h["content"]
                )
                for h in result["hints"]
            ]

        raise ValidationError(f"Hint 格式验证失败，输出内容：{text[:200]}...")


# 全局实例
_validator: Optional[HintValidator] = None


def get_validator() -> HintValidator:
    """获取全局验证器实例"""
    global _validator
    if _validator is None:
        _validator = HintValidator()
    return _validator
