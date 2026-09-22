"""
数据库模块

使用 SQLite 存储题目、题解和 Hint 数据
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from .config import Config
from .models import Problem, Solution, Hint, GenerationRecord
from .errors import DatabaseError


class Database:
    """数据库操作类"""

    def __init__(self, db_path: Path):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """连接数据库"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._create_tables()
        return self._conn

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_tables(self):
        """创建数据表"""
        conn = self.connect()
        cursor = conn.cursor()

        # problems 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS problems (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                difficulty INTEGER DEFAULT 0,
                statement TEXT,
                source_url TEXT,
                fetched_at TEXT,
                updated_at TEXT
            )
        """)

        # solutions 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                title TEXT,
                author TEXT,
                url TEXT,
                content TEXT,
                fetched_at TEXT,
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            )
        """)

        # hints 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hints (
                problem_id TEXT NOT NULL,
                level INTEGER NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                prompt_version TEXT,
                created_at TEXT,
                updated_at TEXT,
                PRIMARY KEY(problem_id, level),
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            )
        """)

        # generations 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                provider TEXT,
                model TEXT,
                prompt_version TEXT,
                status TEXT,
                error TEXT,
                created_at TEXT,
                finished_at TEXT,
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            )
        """)

        conn.commit()

    def save_problem(self, problem: Problem) -> bool:
        """保存题目信息"""
        conn = self.connect()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO problems 
                (id, title, difficulty, statement, source_url, fetched_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                problem.id,
                problem.title,
                problem.difficulty,
                problem.statement,
                problem.source_url,
                now,
                now
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseError(f"保存题目失败：{e}")

    def get_problem(self, problem_id: str) -> Optional[Problem]:
        """获取题目信息"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return Problem(
            id=row["id"],
            title=row["title"],
            difficulty=row["difficulty"],
            statement=row["statement"] or "",
            source_url=row["source_url"] or "",
            fetched_at=row["fetched_at"],
            updated_at=row["updated_at"]
        )

    def save_solution(self, solution: Solution) -> bool:
        """保存题解信息"""
        conn = self.connect()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        try:
            cursor.execute("""
                INSERT INTO solutions 
                (problem_id, title, author, url, content, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                solution.problem_id,
                solution.title,
                solution.author,
                solution.url,
                solution.content,
                now
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseError(f"保存题解失败：{e}")

    def get_solutions(self, problem_id: str) -> list[Solution]:
        """获取题目的所有题解"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM solutions WHERE problem_id = ? ORDER BY id",
            (problem_id,)
        )
        rows = cursor.fetchall()

        return [
            Solution(
                id=row["id"],
                problem_id=row["problem_id"],
                title=row["title"] or "",
                author=row["author"] or "",
                url=row["url"] or "",
                content=row["content"] or "",
                fetched_at=row["fetched_at"]
            )
            for row in rows
        ]

    def save_hint(self, hint: Hint) -> bool:
        """保存 Hint"""
        conn = self.connect()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO hints 
                (problem_id, level, content, model, prompt_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                hint.problem_id,
                hint.level,
                hint.content,
                hint.model,
                hint.prompt_version,
                now,
                now
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseError(f"保存 Hint 失败：{e}")

    def get_hints(self, problem_id: str) -> list[Hint]:
        """获取题目的所有 Hint"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM hints WHERE problem_id = ? ORDER BY level",
            (problem_id,)
        )
        rows = cursor.fetchall()

        return [
            Hint(
                problem_id=row["problem_id"],
                level=row["level"],
                content=row["content"],
                model=row["model"],
                prompt_version=row["prompt_version"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]

    def has_hints(self, problem_id: str) -> bool:
        """检查题目是否已有 Hint"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM hints WHERE problem_id = ?",
            (problem_id,)
        )
        count = cursor.fetchone()[0]
        return count > 0

    def save_generation_record(self, record: GenerationRecord) -> bool:
        """保存生成记录"""
        conn = self.connect()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        try:
            cursor.execute("""
                INSERT INTO generations 
                (problem_id, provider, model, prompt_version, status, error, created_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.problem_id,
                record.provider,
                record.model,
                record.prompt_version,
                record.status,
                record.error,
                now,
                record.finished_at or now
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseError(f"保存生成记录失败：{e}")

    def get_all_problems_with_hints(self) -> list[dict]:
        """获取所有带有 Hint 的题目及其 Hint"""
        conn = self.connect()
        cursor = conn.cursor()

        # 获取所有题目
        cursor.execute("SELECT id, title, difficulty FROM problems ORDER BY id")
        problems = cursor.fetchall()

        result = []
        for prob in problems:
            hints = self.get_hints(prob["id"])
            if hints:
                result.append({
                    "id": prob["id"],
                    "title": prob["title"],
                    "difficulty": prob["difficulty"],
                    "hints": [
                        {"level": h.level, "content": h.content}
                        for h in hints
                    ]
                })

        return result

    def export_json(self, export_path: str | Path) -> dict:
        """导出为前端 JSON 格式"""
        from pathlib import Path as PathType
        
        if isinstance(export_path, str):
            export_path = PathType(export_path)
        
        problems = self.get_all_problems_with_hints()

        data = {
            "version": 2,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "problems": problems
        }

        # 确保目录存在
        export_path.parent.mkdir(parents=True, exist_ok=True)

        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return data

    def clear_problem(self, problem_id: str):
        """清除题目的所有数据（用于重新生成）"""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM hints WHERE problem_id = ?", (problem_id,))
            cursor.execute("DELETE FROM solutions WHERE problem_id = ?", (problem_id,))
            cursor.execute("DELETE FROM problems WHERE id = ?", (problem_id,))
            conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"清除题目数据失败：{e}")

    def get_statistics(self) -> dict:
        """获取数据库统计信息"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM problems")
        problem_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT problem_id) FROM hints")
        hint_problem_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM hints")
        hint_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM solutions")
        solution_count = cursor.fetchone()[0]

        return {
            "total_problems": problem_count,
            "problems_with_hints": hint_problem_count,
            "total_hints": hint_count,
            "total_solutions": solution_count
        }
