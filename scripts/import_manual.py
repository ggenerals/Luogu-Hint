#!/usr/bin/env python3
"""
手动导入题目数据工具

使用方法：
1. 从原项目复制 data.json 和 dat*.json 文件到 data/old_data/ 目录
2. 运行：hint-luogu import-old data/old_data/
3. 或使用 Python 直接运行：python scripts/import_manual.py data/old_data/

也可以手动创建单个题目的 JSON 文件：
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


def load_old_json_files(data_dir: str) -> list[dict]:
    """加载原项目的 JSON 文件"""
    data_path = Path(data_dir)
    problems = []
    
    # 加载 data.json
    main_json = data_path / "data.json"
    if main_json.exists():
        with open(main_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                problems.extend(data)
            elif isinstance(data, dict) and "problems" in data:
                problems.extend(data["problems"])
    
    # 加载 dat*.json
    for json_file in sorted(data_path.glob("dat*.json")):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                problems.extend(data)
            elif isinstance(data, dict) and "problems" in data:
                problems.extend(data["problems"])
    
    return problems


def convert_old_format(old_data: dict) -> tuple[Problem, list[Solution]]:
    """将原项目格式转换为新格式"""
    problem_id = old_data.get("id", "")
    
    # 构建题目对象
    problem = Problem(
        id=problem_id,
        title=old_data.get("title", problem_id),
        difficulty=old_data.get("difficulty", 0),
        statement=old_data.get("statement", ""),
        source_url=f"https://www.luogu.com.cn/problem/{problem_id}",
        fetched_at=datetime.utcnow().isoformat()
    )
    
    # 构建题解对象
    solutions = []
    
    # 旧格式可能有 hint1-5 和 solution 字段
    if "solution" in old_data and old_data["solution"]:
        solutions.append(Solution(
            problem_id=problem_id,
            title=old_data.get("title", ""),
            author="",
            url="",
            content=old_data["solution"],
            fetched_at=datetime.utcnow().isoformat()
        ))
    
    # 如果有 hints 数组（新格式）
    if "hints" in old_data:
        # 这是已经生成过 Hint 的数据，不需要导入题解
        pass
    
    return problem, solutions


async def import_problems(data_dir: str):
    """导入题目数据"""
    config = get_config()
    db = Database(config.database)
    
    try:
        # 初始化数据库
        db.initialize()
        
        # 加载旧数据
        print(f"正在加载 {data_dir} 中的 JSON 文件...")
        old_problems = load_old_json_files(data_dir)
        print(f"找到 {len(old_problems)} 个题目")
        
        imported = 0
        failed = 0
        
        for old_data in old_problems:
            try:
                problem, solutions = convert_old_format(old_data)
                
                # 保存题目
                db.save_problem(problem)
                
                # 保存题解
                for solution in solutions:
                    db.save_solution(solution)
                
                imported += 1
                if imported % 10 == 0:
                    print(f"已导入 {imported} 个题目...")
                    
            except Exception as e:
                print(f"导入失败 {old_data.get('id', 'UNKNOWN')}: {e}")
                failed += 1
        
        print(f"\n导入完成!")
        print(f"成功：{imported}")
        print(f"失败：{failed}")
        
        # 导出为新格式
        print("\n正在导出为新格式 JSON...")
        from generator.exporter import export_to_json
        export_to_json(config.database, config.export_path)
        print(f"已导出到 {config.export_path}")
        
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/import_manual.py <数据目录>")
        print("\n示例:")
        print("  python scripts/import_manual.py data/old_data/")
        print("\n该目录应包含原项目的 data.json 和 dat*.json 文件")
        sys.exit(1)
    
    data_dir = sys.argv[1]
    
    if not Path(data_dir).exists():
        print(f"错误：目录不存在：{data_dir}")
        sys.exit(1)
    
    asyncio.run(import_problems(data_dir))


if __name__ == "__main__":
    main()
