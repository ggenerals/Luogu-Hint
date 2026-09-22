#!/usr/bin/env python3
"""
导入单个手动创建的题目 JSON 文件

使用方法：
python scripts/import_single.py data/manual/P1000.json
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.database import Database
from generator.models import Problem, Solution
from generator.config import get_config


def load_single_json(json_path: str) -> dict:
    """加载单个题目的 JSON 文件"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def convert_to_models(data: dict) -> tuple[Problem, list[Solution]]:
    """将 JSON 数据转换为模型对象"""
    problem_id = data.get("id", "")
    
    if not problem_id:
        raise ValueError("JSON 文件必须包含 'id' 字段")
    
    # 构建题目对象
    problem = Problem(
        id=problem_id,
        title=data.get("title", problem_id),
        difficulty=data.get("difficulty", 0),
        statement=data.get("statement", ""),
        source_url=data.get("source_url", f"https://www.luogu.com.cn/problem/{problem_id}"),
        fetched_at=data.get("fetched_at", datetime.utcnow().isoformat())
    )
    
    # 构建题解对象
    solutions = []
    
    if "solutions" in data and isinstance(data["solutions"], list):
        for sol_data in data["solutions"]:
            solutions.append(Solution(
                problem_id=problem_id,
                title=sol_data.get("title", ""),
                author=sol_data.get("author", ""),
                url=sol_data.get("url", ""),
                content=sol_data.get("content", ""),
                fetched_at=sol_data.get("fetched_at", datetime.utcnow().isoformat())
            ))
    
    # 如果已经有 hints，也保存
    if "hints" in data and isinstance(data["hints"], list):
        # 这表示已经是完整数据，可以直接导出
        print(f"注意：{problem_id} 已包含 Hint 数据")
    
    return problem, solutions


async def import_single_problem(json_path: str):
    """导入单个题目"""
    config = get_config()
    db = Database(config.database)
    
    try:
        # 初始化数据库
        db.initialize()
        
        # 加载 JSON
        print(f"正在加载 {json_path}...")
        data = load_single_json(json_path)
        
        # 转换并保存
        problem, solutions = convert_to_models(data)
        
        db.save_problem(problem)
        print(f"✓ 题目 {problem.id} 已保存")
        
        for solution in solutions:
            db.save_solution(solution)
            print(f"✓ 题解已保存")
        
        # 导出
        print("\n正在导出 JSON...")
        from generator.exporter import export_to_json
        export_to_json(config.database, config.export_path)
        print(f"✓ 已导出到 {config.export_path}")
        
        print(f"\n{problem.id} 导入成功!")
        
    except Exception as e:
        print(f"✗ 导入失败：{e}")
        raise
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/import_single.py <JSON 文件路径>")
        print("\n示例:")
        print("  python scripts/import_single.py data/manual/P1000.json")
        print("\nJSON 文件格式:")
        print("""
{
  "id": "P1000",
  "title": "A+B Problem",
  "difficulty": 1,
  "statement": "题目描述...",
  "solutions": [
    {
      "title": "题解标题",
      "author": "作者",
      "content": "题解内容..."
    }
  ]
}
        """)
        sys.exit(1)
    
    json_path = sys.argv[1]
    
    if not Path(json_path).exists():
        print(f"错误：文件不存在：{json_path}")
        sys.exit(1)
    
    asyncio.run(import_single_problem(json_path))


if __name__ == "__main__":
    main()
