# Hint-Luogu 开发文档

> 本文档用于指导 Hint-Luogu 项目的接管、重构、开发、部署与长期维护。

## 目录

1. [项目架构](#1-项目架构)
2. [核心模块](#2-核心模块)
3. [数据模型](#3-数据模型)
4. [开发环境](#4-开发环境)
5. [CLI 命令实现](#5-cli-命令实现)
6. [添加新题目流程](#6-添加新题目流程)
7. [测试指南](#7-测试指南)
8. [故障排查](#8-故障排查)

---

## 1. 项目架构

### 1.1 整体架构

```
┌───────────────────────────────┐
│           Frontend            │
│         GitHub Pages          │
└───────────────┬───────────────┘
                │
                │ JSON
                ▼
┌───────────────────────────────┐
│          Data Layer           │
│       SQLite / JSON           │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│        Generation Layer       │
│       Hint Generator          │
└───────────────┬───────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
┌──────────────┐  ┌───────────────┐
│  Luogu Fetch │  │ LLM Provider  │
└──────────────┘  └───────────────┘
```

### 1.2 目录结构

```
hint-luogu/
├── frontend/              # 静态前端
│   ├── index.html
│   ├── script.js
│   ├── style.css
│   └── data.json         # 自动生成
├── generator/             # 核心代码
│   ├── __init__.py
│   ├── cli.py            # CLI 入口
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库操作
│   ├── models.py         # 数据模型
│   ├── fetcher.py        # HTTP 请求封装
│   ├── luogu.py          # 洛谷专用获取器
│   ├── llm.py            # LLM Provider 抽象
│   ├── prompt.py         # Prompt 管理
│   ├── generator.py      # Hint 生成逻辑
│   ├── validator.py      # Hint 验证器
│   ├── exporter.py       # JSON 导出器
│   └── errors.py         # 自定义异常
├── data/                  # 数据目录
│   ├── hint.db           # SQLite 数据库
│   └── cache/            # HTTP 缓存
├── prompts/               # Prompt 模板
│   └── hint_v1.txt
├── tests/                 # 测试文件
├── docs/                  # 文档
├── config.example.toml    # 配置示例
├── pyproject.toml         # 项目配置
└── README.md
```

---

## 2. 核心模块

### 2.1 配置管理 (`config.py`)

```python
from pathlib import Path
import tomli

class Config:
    def __init__(self, config_path: str = "config.toml"):
        self.config_path = Path(config_path)
        self._load_config()
    
    def _load_config(self):
        with open(self.config_path, "rb") as f:
            config = tomli.load(f)
        
        self.llm_provider = config["llm"]["provider"]
        self.llm_model = config["llm"]["model"]
        self.llm_base_url = config["llm"]["base_url"]
        
        self.luogu_timeout = config["luogu"]["timeout"]
        self.luogu_max_retries = config["luogu"]["max_retries"]
        self.luogu_max_solutions = config["luogu"]["max_solutions"]
        self.luogu_request_interval = config["luogu"]["request_interval"]
        
        self.hint_count = config["generation"]["hint_count"]
        self.prompt_version = config["generation"]["prompt_version"]
        
        self.database_path = Path(config["data"]["database"])
        self.export_path = Path(config["data"]["export"])
```

### 2.2 数据模型 (`models.py`)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Problem:
    id: str
    title: str
    difficulty: int
    statement: str
    source_url: str
    fetched_at: datetime
    updated_at: Optional[datetime] = None

@dataclass
class Solution:
    id: Optional[int]
    problem_id: str
    title: str
    author: str
    url: str
    content: str
    fetched_at: datetime

@dataclass
class Hint:
    problem_id: str
    level: int
    content: str
    model: str
    prompt_version: str
    created_at: datetime
    updated_at: Optional[datetime] = None
```

### 2.3 数据库操作 (`database.py`)

```python
import sqlite3
from pathlib import Path

class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS problems (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    difficulty INTEGER,
                    statement TEXT,
                    source_url TEXT,
                    fetched_at TEXT,
                    updated_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL,
                    title TEXT,
                    author TEXT,
                    url TEXT,
                    content TEXT,
                    fetched_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS hints (
                    problem_id TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    model TEXT,
                    prompt_version TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    PRIMARY KEY(problem_id, level)
                );
                
                CREATE TABLE IF NOT EXISTS generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    prompt_version TEXT,
                    status TEXT,
                    error TEXT,
                    created_at TEXT,
                    finished_at TEXT
                );
            """)
    
    def add_problem(self, problem: Problem):
        """添加或更新题目"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO problems 
                (id, title, difficulty, statement, source_url, fetched_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                problem.id, problem.title, problem.difficulty,
                problem.statement, problem.source_url,
                problem.fetched_at.isoformat(),
                problem.updated_at.isoformat() if problem.updated_at else None
            ))
    
    def add_solution(self, solution: Solution):
        """添加题解"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO solutions 
                (problem_id, title, author, url, content, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                solution.problem_id, solution.title, solution.author,
                solution.url, solution.content, solution.fetched_at.isoformat()
            ))
    
    def add_hint(self, hint: Hint):
        """添加 Hint"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO hints 
                (problem_id, level, content, model, prompt_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                hint.problem_id, hint.level, hint.content,
                hint.model, hint.prompt_version,
                hint.created_at.isoformat(),
                hint.updated_at.isoformat() if hint.updated_at else None
            ))
    
    def get_problem(self, problem_id: str) -> Optional[Problem]:
        """获取题目"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM problems WHERE id = ?", 
                (problem_id,)
            ).fetchone()
            
            if not row:
                return None
            
            return Problem(
                id=row["id"],
                title=row["title"],
                difficulty=row["difficulty"],
                statement=row["statement"],
                source_url=row["source_url"],
                fetched_at=datetime.fromisoformat(row["fetched_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
            )
    
    def get_hints(self, problem_id: str) -> list[Hint]:
        """获取题目的所有 Hint"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM hints WHERE problem_id = ? ORDER BY level",
                (problem_id,)
            ).fetchall()
            
            return [
                Hint(
                    problem_id=row["problem_id"],
                    level=row["level"],
                    content=row["content"],
                    model=row["model"],
                    prompt_version=row["prompt_version"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
                )
                for row in rows
            ]
```

### 2.4 洛谷获取器 (`luogu.py`)

```python
import httpx
from bs4 import BeautifulSoup
from .models import Problem, Solution
from .errors import LuoguFetchError

class LuoguFetcher:
    def __init__(self, timeout: int = 20, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "Hint-Luogu/2.0"}
        )
    
    def fetch_problem(self, problem_id: str) -> Problem:
        """获取题目信息"""
        url = f"https://www.luogu.com.cn/problem/{problem_id}"
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # 解析题目信息
                title = self._extract_title(soup)
                difficulty = self._extract_difficulty(soup)
                statement = self._extract_statement(soup)
                
                return Problem(
                    id=problem_id,
                    title=title,
                    difficulty=difficulty,
                    statement=statement,
                    source_url=url,
                    fetched_at=datetime.now()
                )
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise LuoguFetchError(f"Failed to fetch {problem_id}: {e}")
                time.sleep(2 ** attempt)  # 指数退避
    
    def fetch_solutions(self, problem_id: str, max_count: int = 3) -> list[Solution]:
        """获取题解"""
        url = f"https://www.luogu.com.cn/problem/{problem_id}/solution"
        
        solutions = []
        # 实现题解获取逻辑
        # ...
        
        return solutions[:max_count]
```

### 2.5 LLM Provider (`llm.py`)

```python
from abc import ABC, abstractmethod
import ollama

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, model: str) -> str:
        pass

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.client = ollama.Client(host=base_url)
    
    def generate(self, prompt: str, model: str) -> str:
        response = self.client.generate(model=model, prompt=prompt)
        return response["response"]

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    def generate(self, prompt: str, model: str) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

def create_provider(provider_type: str, config: dict) -> LLMProvider:
    """工厂函数：创建 Provider"""
    if provider_type == "ollama":
        return OllamaProvider(config.get("base_url"))
    elif provider_type == "openai":
        return OpenAIProvider(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
    else:
        raise ValueError(f"Unknown provider: {provider_type}")
```

### 2.6 Hint 生成器 (`generator.py`)

```python
from .models import Problem, Solution, Hint
from .llm import LLMProvider
from .prompt import load_prompt
from .validator import validate_hints

class HintGenerator:
    def __init__(
        self,
        llm_provider: LLMProvider,
        model: str,
        prompt_version: str
    ):
        self.llm = llm_provider
        self.model = model
        self.prompt_version = prompt_version
    
    def generate(self, problem: Problem, solutions: list[Solution]) -> list[Hint]:
        """生成 Hint"""
        # 构建 Prompt
        prompt = load_prompt(self.prompt_version).format(
            title=problem.title,
            statement=problem.statement,
            solutions="\n\n".join([s.content for s in solutions])
        )
        
        # 调用 LLM
        raw_output = self.llm.generate(prompt, self.model)
        
        # 解析输出
        hints = self._parse_output(raw_output, problem.id)
        
        # 验证
        if not validate_hints(hints):
            raise ValidationError("Generated hints failed validation")
        
        return hints
    
    def _parse_output(self, output: str, problem_id: str) -> list[Hint]:
        """解析 LLM 输出为 Hint 列表"""
        # 实现解析逻辑
        # 期望格式：JSON 或特定文本格式
        pass
```

### 2.7 验证器 (`validator.py`)

```python
from .models import Hint

def validate_hints(hints: list[Hint]) -> bool:
    """验证 Hint 列表"""
    # 检查数量
    if len(hints) != 5:
        return False
    
    # 检查每个 Hint
    for i, hint in enumerate(hints, 1):
        if hint.level != i:
            return False
        if not hint.content or hint.content.strip() == "":
            return False
        if len(hint.content) > 500:  # 长度限制
            return False
    
    return True
```

### 2.8 导出器 (`exporter.py`)

```python
import json
from datetime import datetime
from .database import Database

class Exporter:
    def __init__(self, db: Database, export_path: str):
        self.db = db
        self.export_path = Path(export_path)
    
    def export(self):
        """导出所有数据到 JSON"""
        # 获取所有题目
        problems = self.db.get_all_problems()
        
        data = {
            "version": 2,
            "generated_at": datetime.now().isoformat(),
            "problems": []
        }
        
        for problem in problems:
            hints = self.db.get_hints(problem.id)
            
            if hints:
                data["problems"].append({
                    "id": problem.id,
                    "title": problem.title,
                    "difficulty": problem.difficulty,
                    "hints": [
                        {
                            "level": h.level,
                            "content": h.content
                        }
                        for h in hints
                    ]
                })
        
        # 写入文件
        self.export_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.export_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## 3. 数据模型

### 3.1 数据库 Schema

```sql
-- 题目表
CREATE TABLE problems (
    id TEXT PRIMARY KEY,           -- P1000
    title TEXT NOT NULL,           -- A+B Problem
    difficulty INTEGER,            -- 难度等级
    statement TEXT,                -- 题目描述
    source_url TEXT,               -- 原始链接
    fetched_at TEXT,               -- 获取时间
    updated_at TEXT                -- 更新时间
);

-- 题解表
CREATE TABLE solutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id TEXT NOT NULL,      -- 关联题目
    title TEXT,                    -- 题解标题
    author TEXT,                   -- 作者
    url TEXT,                      -- 题解链接
    content TEXT,                  -- 题解内容
    fetched_at TEXT                -- 获取时间
);

-- Hint 表
CREATE TABLE hints (
    problem_id TEXT NOT NULL,      -- 关联题目
    level INTEGER NOT NULL,        -- 1-5
    content TEXT NOT NULL,         -- Hint 内容
    model TEXT,                    -- 使用的模型
    prompt_version TEXT,           -- Prompt 版本
    created_at TEXT,               -- 创建时间
    updated_at TEXT,               -- 更新时间
    PRIMARY KEY(problem_id, level)
);

-- 生成记录表
CREATE TABLE generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id TEXT NOT NULL,
    provider TEXT,                 -- LLM Provider
    model TEXT,                    -- 模型名称
    prompt_version TEXT,
    status TEXT,                   -- success/failed
    error TEXT,                    -- 错误信息
    created_at TEXT,
    finished_at TEXT
);
```

### 3.2 JSON 导出格式

```json
{
  "version": 2,
  "generated_at": "2026-09-21T12:00:00Z",
  "problems": [
    {
      "id": "P1000",
      "title": "A+B Problem",
      "difficulty": 0,
      "hints": [
        {"level": 1, "content": "..."},
        {"level": 2, "content": "..."},
        {"level": 3, "content": "..."},
        {"level": 4, "content": "..."},
        {"level": 5, "content": "..."}
      ]
    }
  ]
}
```

---

## 4. 开发环境

### 4.1 环境搭建

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -e .

# 安装开发依赖
pip install pytest pytest-mock ruff mypy
```

### 4.2 配置文件

```bash
cp config.example.toml config.toml
```

编辑 `config.toml`：

```toml
[llm]
provider = "ollama"
model = "qwen2.5:14b"
base_url = "http://localhost:11434"

[luogu]
timeout = 20
max_retries = 3
max_solutions = 3
request_interval = 1.5

[generation]
hint_count = 5
prompt_version = "v1"

[data]
database = "data/hint.db"
export = "frontend/data.json"

[logging]
level = "INFO"
```

### 4.3 初始化

```bash
hint-luogu init
```

---

## 5. CLI 命令实现

### 5.1 CLI 入口 (`cli.py`)

```python
import click
from .config import Config
from .database import Database
from .luogu import LuoguFetcher
from .llm import create_provider
from .generator import HintGenerator
from .exporter import Exporter
from .validator import validate_hints

@click.group()
def cli():
    """Hint-Luogu: 洛谷题目 Hint 生成器"""
    pass

@cli.command()
def init():
    """初始化数据库和配置"""
    config = Config()
    db = Database(config.database_path)
    click.echo("✓ Database initialized")
    click.echo("✓ Ready to use")

@cli.command()
@click.argument("problem_id")
def add(problem_id: str):
    """添加新题目"""
    config = Config()
    db = Database(config.database_path)
    
    # 检查是否已存在
    if db.get_problem(problem_id):
        click.echo(f"⚠ {problem_id} already exists. Use 'regenerate' to regenerate.")
        return
    
    # 获取题目
    fetcher = LuoguFetcher(config.luogu_timeout, config.luogu_max_retries)
    problem = fetcher.fetch_problem(problem_id)
    db.add_problem(problem)
    click.echo(f"✓ Problem fetched: {problem_id} - {problem.title}")
    
    # 获取题解
    solutions = fetcher.fetch_solutions(problem_id, config.luogu_max_solutions)
    for sol in solutions:
        db.add_solution(sol)
    click.echo(f"✓ Solutions fetched: {len(solutions)}")
    
    # 生成 Hint
    provider = create_provider(config.llm_provider, {
        "base_url": config.llm_base_url
    })
    generator = HintGenerator(provider, config.llm_model, config.prompt_version)
    hints = generator.generate(problem, solutions)
    
    # 保存
    for hint in hints:
        db.add_hint(hint)
    click.echo("✓ Hint generated and saved")
    
    # 导出
    exporter = Exporter(db, config.export_path)
    exporter.export()
    click.echo("✓ Exported to frontend/data.json")
    
    click.echo(f"\n{problem_id} added successfully.")

@cli.command()
@click.argument("problem_id")
def regenerate(problem_id: str):
    """重新生成 Hint"""
    # 实现重新生成逻辑
    pass

@cli.command()
@click.argument("problem_ids", nargs=-1)
def batch(problem_ids: tuple[str]):
    """批量处理题目"""
    success_count = 0
    failed_count = 0
    
    for pid in problem_ids:
        try:
            # 调用 add 逻辑
            success_count += 1
            click.echo(f"✓ {pid}")
        except Exception as e:
            failed_count += 1
            click.echo(f"✗ {pid}: {e}")
    
    click.echo(f"\nSuccess: {success_count}, Failed: {failed_count}")

@cli.command()
def export():
    """导出前端数据"""
    config = Config()
    db = Database(config.database_path)
    exporter = Exporter(db, config.export_path)
    exporter.export()
    click.echo(f"✓ Exported to {config.export_path}")

@cli.command()
@click.argument("problem_id")
def status(problem_id: str):
    """查看题目状态"""
    config = Config()
    db = Database(config.database_path)
    
    problem = db.get_problem(problem_id)
    if not problem:
        click.echo(f"✗ {problem_id} not found")
        return
    
    hints = db.get_hints(problem_id)
    
    click.echo(f"Problem: {problem.title}")
    click.echo(f"Difficulty: {problem.difficulty}")
    click.echo(f"Hints: {len(hints)}/5")
    click.echo(f"Last updated: {problem.updated_at or problem.fetched_at}")

if __name__ == "__main__":
    cli()
```

---

## 6. 添加新题目流程

### 完整流程图

```
hint-luogu add P3372
        ↓
1. 规范化题号 (P3372)
        ↓
2. 检查数据库是否存在
        ↓
   存在 → 提示使用 regenerate
        ↓
   不存在
        ↓
3. 获取题目信息 (LuoguFetcher)
   - 题目标题
   - 难度
   - 题目描述
   - 输入输出格式
   - 样例
        ↓
4. 获取题解 (最多 3 篇)
        ↓
5. 构建 Prompt
   - 加载 prompt_v1.txt
   - 填充题目信息
        ↓
6. 调用 LLM
   - Ollama / OpenAI
        ↓
7. 解析输出
   - 提取 5 个 Hint
        ↓
8. 验证
   - 数量 = 5
   - 内容非空
   - 长度合理
        ↓
   失败 → 重新生成或报错
        ↓
   成功
        ↓
9. 保存到数据库
        ↓
10. 导出 JSON
        ↓
✓ 完成
```

### 代码示例

```python
# 完整添加流程
from generator.config import Config
from generator.database import Database
from generator.luogu import LuoguFetcher
from generator.llm import create_provider
from generator.generator import HintGenerator
from generator.exporter import Exporter

def add_problem(problem_id: str):
    config = Config()
    db = Database(config.database_path)
    
    # 1. 检查存在性
    if db.get_problem(problem_id):
        print(f"{problem_id} already exists")
        return
    
    # 2. 获取题目
    fetcher = LuoguFetcher()
    problem = fetcher.fetch_problem(problem_id)
    db.add_problem(problem)
    
    # 3. 获取题解
    solutions = fetcher.fetch_solutions(problem_id)
    for sol in solutions:
        db.add_solution(sol)
    
    # 4. 生成 Hint
    provider = create_provider(config.llm_provider, {...})
    generator = HintGenerator(provider, config.llm_model, config.prompt_version)
    hints = generator.generate(problem, solutions)
    
    # 5. 保存
    for hint in hints:
        db.add_hint(hint)
    
    # 6. 导出
    exporter = Exporter(db, config.export_path)
    exporter.export()
    
    print(f"{problem_id} added successfully")
```

---

## 7. 测试指南

### 7.1 单元测试

```python
# tests/test_validator.py
from generator.models import Hint
from generator.validator import validate_hints
from datetime import datetime

def test_valid_hints():
    hints = [
        Hint(problem_id="P1000", level=i, content=f"Hint {i}", 
             model="test", prompt_version="v1", created_at=datetime.now())
        for i in range(1, 6)
    ]
    assert validate_hints(hints) is True

def test_wrong_count():
    hints = [
        Hint(problem_id="P1000", level=i, content=f"Hint {i}",
             model="test", prompt_version="v1", created_at=datetime.now())
        for i in range(1, 4)  # 只有 3 个
    ]
    assert validate_hints(hints) is False

def test_empty_content():
    hints = [
        Hint(problem_id="P1000", level=1, content="",
             model="test", prompt_version="v1", created_at=datetime.now())
    ] + [
        Hint(problem_id="P1000", level=i, content=f"Hint {i}",
             model="test", prompt_version="v1", created_at=datetime.now())
        for i in range(2, 6)
    ]
    assert validate_hints(hints) is False
```

### 7.2 Mock LLM

```python
# tests/test_generator.py
from unittest.mock import Mock
from generator.generator import HintGenerator

class MockLLMProvider:
    def generate(self, prompt: str, model: str) -> str:
        return '''
        {
          "hints": [
            {"level": 1, "content": "思考方向..."},
            {"level": 2, "content": "关键观察..."},
            {"level": 3, "content": "算法方向..."},
            {"level": 4, "content": "核心算法..."},
            {"level": 5, "content": "接近完整解..."}
          ]
        }
        '''

def test_generator_with_mock():
    provider = MockLLMProvider()
    generator = HintGenerator(provider, "test-model", "v1")
    
    # 创建测试数据
    problem = Problem(...)
    solutions = [...]
    
    hints = generator.generate(problem, solutions)
    assert len(hints) == 5
```

### 7.3 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_validator.py

# 带覆盖率
pytest --cov=generator

# 详细输出
pytest -v
```

---

## 8. 故障排查

### 8.1 Ollama 无法连接

```bash
# 检查 Ollama 服务
curl http://localhost:11434

# 检查模型
ollama list

# 拉取模型
ollama pull qwen2.5:14b
```

### 8.2 洛谷获取失败

可能原因：
- 网络问题
- 页面结构变化
- 请求频率过高

解决方案：
```bash
# 增加超时时间
# 修改 config.toml
[luogu]
timeout = 30
max_retries = 5

# 降低请求频率
request_interval = 2.0
```

### 8.3 LLM 输出格式错误

检查：
- Prompt 模板是否正确
- 模型是否支持指令遵循
- temperature 参数是否过高

解决：
```toml
[generation]
# 尝试更换模型
model = "qwen2.5:32b"
```

### 8.4 数据库锁定

```bash
# 关闭所有使用该数据库的进程
# 或删除锁文件
rm data/hint.db-shm data/hint.db-wal
```

### 8.5 JSON 导出为空

检查：
```bash
# 查看数据库中是否有数据
hint-luogu list

# 检查导出路径
cat frontend/data.json
```

---

## 附录

### A. 设计原则

1. **数据与代码分离**：代码 ≠ 数据
2. **LLM 与业务逻辑分离**：Generator 不关心具体模型
3. **网络层与生成层分离**：Fetcher → Problem/Solution → Generator
4. **数据库是真实数据源**：SQLite → JSON → Frontend
5. **所有 LLM 输出必须验证**：LLM → Validator → Database
6. **失败必须可恢复**：单题失败不影响批处理
7. **支持重新生成**：任何 Hint 都可 regenerate
8. **模型可替换**：不依赖单一厂商

### B. Commit 规范

```
feat: add Ollama provider
fix: handle Luogu problem parsing failure
refactor: separate data exporter
docs: update README
test: add validator tests
chore: update dependencies
```

### C. 常用命令速查

```bash
# 初始化
hint-luogu init

# 添加题目
hint-luogu add P3372

# 重新生成
hint-luogu regenerate P3372

# 批量处理
hint-luogu batch P1000 P1001 P1002

# 导出
hint-luogu export

# 查看状态
hint-luogu status P3372

# 列出所有
hint-luogu list

# 测试
pytest

# 代码检查
ruff check .

# 格式化
ruff format .
```
