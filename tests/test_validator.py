"""Tests for the validator module."""

import pytest
from datetime import datetime
from generator.models import Hint
from generator.validator import validate_hints, validate_hint_content


def create_hint(problem_id: str, level: int, content: str) -> Hint:
    """Helper function to create a Hint with proper string timestamps."""
    return Hint(
        problem_id=problem_id,
        level=level,
        content=content,
        model="test",
        prompt_version="v1",
        created_at=datetime.now().isoformat()
    )


class TestValidateHints:
    """Test cases for validate_hints function."""

    def test_valid_hints(self):
        """Test with 5 valid hints."""
        hints = [create_hint("P1000", i, f"Hint content {i}") for i in range(1, 6)]
        assert validate_hints(hints) is True

    def test_wrong_count_4_hints(self):
        """Test with only 4 hints (should fail)."""
        hints = [create_hint("P1000", i, f"Hint content {i}") for i in range(1, 5)]
        assert validate_hints(hints) is False

    def test_wrong_count_6_hints(self):
        """Test with 6 hints (should fail)."""
        hints = [create_hint("P1000", i, f"Hint content {i}") for i in range(1, 7)]
        assert validate_hints(hints) is False

    def test_empty_content(self):
        """Test with empty content in first hint."""
        hints = [create_hint("P1000", 1, "")] + \
                [create_hint("P1000", i, f"Hint content {i}") for i in range(2, 6)]
        assert validate_hints(hints) is False

    def test_whitespace_only_content(self):
        """Test with whitespace-only content."""
        hints = [create_hint("P1000", 1, "   ")] + \
                [create_hint("P1000", i, f"Hint content {i}") for i in range(2, 6)]
        assert validate_hints(hints) is False

    def test_too_long_content(self):
        """Test with content exceeding length limit."""
        long_content = "x" * 600  # Exceeds 500 char limit
        hints = [create_hint("P1000", 1, long_content)] + \
                [create_hint("P1000", i, f"Hint content {i}") for i in range(2, 6)]
        assert validate_hints(hints) is False

    def test_wrong_level_sequence(self):
        """Test with incorrect level sequence."""
        hints = [create_hint("P1000", 2, "Hint content 1")] + \
                [create_hint("P1000", i, f"Hint content {i}") for i in range(2, 6)]
        assert validate_hints(hints) is False

    def test_empty_list(self):
        """Test with empty hint list."""
        assert validate_hints([]) is False

    def test_none_content(self):
        """Test with None content (if allowed by dataclass)."""
        try:
            hints = [create_hint("P1000", 1, None)] + \
                    [create_hint("P1000", i, f"Hint content {i}") for i in range(2, 6)]
            assert validate_hints(hints) is False
        except (TypeError, AttributeError, ValueError):
            # If None is not allowed by dataclass, that's also fine
            pass


class TestValidateHintContent:
    """Test cases for validate_hint_content function."""

    def test_valid_content(self):
        """Test with valid content."""
        assert validate_hint_content("This is a valid hint") is True

    def test_empty_string(self):
        """Test with empty string."""
        assert validate_hint_content("") is False

    def test_whitespace_only(self):
        """Test with whitespace only."""
        assert validate_hint_content("   ") is False

    def test_newlines_only(self):
        """Test with newlines only."""
        assert validate_hint_content("\n\n\n") is False

    def test_too_long(self):
        """Test with content exceeding limit."""
        assert validate_hint_content("x" * 600) is False

    def test_exactly_at_limit(self):
        """Test with content at exactly the limit."""
        assert validate_hint_content("x" * 500) is True

    def test_chinese_content(self):
        """Test with Chinese characters."""
        assert validate_hint_content("这是一个有效的提示") is True

    def test_mixed_content(self):
        """Test with mixed languages and symbols."""
        content = "Hint: 考虑使用动态规划 O(n²)"
        assert validate_hint_content(content) is True
