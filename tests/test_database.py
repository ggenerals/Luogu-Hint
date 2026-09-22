"""Tests for the database module."""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime
from generator.database import Database
from generator.models import Problem, Solution, Hint


def create_problem(problem_id: str, title: str, difficulty: int = 0) -> Problem:
    """Helper function to create a Problem with proper string timestamps."""
    return Problem(
        id=problem_id,
        title=title,
        difficulty=difficulty,
        statement="Test statement",
        source_url=f"https://www.luogu.com.cn/problem/{problem_id}",
        fetched_at=datetime.now().isoformat()
    )


def create_solution(problem_id: str, index: int = 0) -> Solution:
    """Helper function to create a Solution with proper string timestamps."""
    return Solution(
        id=None,
        problem_id=problem_id,
        title=f"Solution {index}",
        author=f"Author{index}",
        url=f"https://example.com/{index}",
        content=f"Content {index}",
        fetched_at=datetime.now().isoformat()
    )


def create_hint(problem_id: str, level: int, content: str) -> Hint:
    """Helper function to create a Hint with proper string timestamps."""
    return Hint(
        problem_id=problem_id,
        level=level,
        content=content,
        model="test-model",
        prompt_version="v1",
        created_at=datetime.now().isoformat()
    )


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_hint.db"
    db = Database(str(db_path))
    yield db
    # Cleanup
    db_path.unlink(missing_ok=True)


class TestDatabaseInit:
    """Test database initialization."""

    def test_create_tables(self, temp_db):
        """Test that tables are created on init."""
        # Connect to trigger table creation
        temp_db.connect()
        
        conn = sqlite3.connect(str(temp_db.db_path))
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert "problems" in tables
        assert "solutions" in tables
        assert "hints" in tables
        assert "generations" in tables
        
        conn.close()
        temp_db.close()


class TestProblemOperations:
    """Test problem CRUD operations."""

    def test_add_problem(self, temp_db):
        """Test adding a problem."""
        problem = create_problem("P1000", "A+B Problem", 0)
        temp_db.save_problem(problem)
        
        # Verify by querying directly
        conn = temp_db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM problems WHERE id = ?", ("P1000",))
        row = cursor.fetchone()
        temp_db.close()
        
        assert row is not None
        assert row[0] == "P1000"
        assert row[1] == "A+B Problem"

    def test_get_problem(self, temp_db):
        """Test retrieving a problem."""
        problem = create_problem("P1001", "Test Problem", 1)
        temp_db.save_problem(problem)
        retrieved = temp_db.get_problem("P1001")
        
        assert retrieved is not None
        assert retrieved.id == "P1001"
        assert retrieved.title == "Test Problem"
        assert retrieved.difficulty == 1

    def test_get_nonexistent_problem(self, temp_db):
        """Test retrieving a problem that doesn't exist."""
        result = temp_db.get_problem("P9999")
        assert result is None

    def test_update_problem(self, temp_db):
        """Test updating an existing problem."""
        problem1 = create_problem("P1002", "Original Title", 0)
        temp_db.save_problem(problem1)
        
        problem2 = Problem(
            id="P1002",
            title="Updated Title",
            difficulty=2,
            statement="Updated statement",
            source_url="https://www.luogu.com.cn/problem/P1002",
            fetched_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        temp_db.save_problem(problem2)
        retrieved = temp_db.get_problem("P1002")
        
        assert retrieved.title == "Updated Title"
        assert retrieved.difficulty == 2


class TestSolutionOperations:
    """Test solution CRUD operations."""

    def test_add_solution(self, temp_db):
        """Test adding a solution."""
        solution = create_solution("P1000", 0)
        temp_db.save_solution(solution)
        
        # Verify
        solutions = temp_db.get_solutions("P1000")
        assert len(solutions) == 1

    def test_add_multiple_solutions(self, temp_db):
        """Test adding multiple solutions for the same problem."""
        for i in range(3):
            solution = create_solution("P1000", i)
            temp_db.save_solution(solution)
        
        solutions = temp_db.get_solutions("P1000")
        assert len(solutions) == 3


class TestHintOperations:
    """Test hint CRUD operations."""

    def test_add_hint(self, temp_db):
        """Test adding a hint."""
        hint = create_hint("P1000", 1, "First hint")
        temp_db.save_hint(hint)
        
        # Verify
        hints = temp_db.get_hints("P1000")
        assert len(hints) == 1
        assert hints[0].level == 1
        assert hints[0].content == "First hint"

    def test_add_all_hints(self, temp_db):
        """Test adding all 5 hints for a problem."""
        for i in range(1, 6):
            hint = create_hint("P1000", i, f"Hint {i}")
            temp_db.save_hint(hint)
        
        hints = temp_db.get_hints("P1000")
        assert len(hints) == 5
        
        # Verify order
        for i, hint in enumerate(hints, 1):
            assert hint.level == i
            assert hint.content == f"Hint {i}"

    def test_update_hint(self, temp_db):
        """Test updating an existing hint."""
        hint1 = create_hint("P1000", 1, "Original hint")
        temp_db.save_hint(hint1)
        
        hint2 = Hint(
            problem_id="P1000",
            level=1,
            content="Updated hint",
            model="new-model",
            prompt_version="v2",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        temp_db.save_hint(hint2)
        
        hints = temp_db.get_hints("P1000")
        assert len(hints) == 1
        assert hints[0].content == "Updated hint"
        assert hints[0].model == "new-model"

    def test_get_hints_ordered(self, temp_db):
        """Test that hints are returned in order."""
        # Add hints in reverse order
        for i in range(5, 0, -1):
            hint = create_hint("P1000", i, f"Hint {i}")
            temp_db.save_hint(hint)
        
        hints = temp_db.get_hints("P1000")
        
        # Should be ordered by level
        assert len(hints) == 5
        for i, hint in enumerate(hints, 1):
            assert hint.level == i


class TestGenerationRecords:
    """Test generation record operations."""

    def test_add_generation_record(self, temp_db):
        """Test adding a generation record."""
        # This would require implementing add_generation method
        # Placeholder for future implementation
        pass
