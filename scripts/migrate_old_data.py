#!/usr/bin/env python3
"""
数据迁移脚本

将原项目的 JSON 数据迁移到 SQLite 数据库
"""

import json
import logging
from pathlib import Path
from datetime import datetime

# 添加父目录到路径以便导入 generator 模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.database import Database
from generator.models import Problem, Hint


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def load_old_json(data_dir: Path) -> list[dict]:
    """加载所有旧 JSON 文件"""
    all_problems = []
    
    # 加载 original_data.json
    original_file = data_dir / "original_data.json"
    if original_file.exists():
        with open(original_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"从 original_data.json 加载了 {len(data)} 条记录")
            all_problems.extend(data)
    
    # 加载 dat*.json 文件
    for i in range(1, 20):
        dat_file = data_dir / f"dat{i}.json"
        if dat_file.exists():
            with open(dat_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"从 dat{i}.json 加载了 {len(data)} 条记录")
                all_problems.extend(data)
    
    return all_problems


def convert_to_v2_format(old_problem: dict) -> tuple[Problem, list[Hint]]:
    """将旧格式转换为 V2 格式"""
    problem_id = old_problem.get("id", "")
    title = old_problem.get("title", "")
    difficulty = old_problem.get("diff", 0)
    
    # 创建 Problem 对象
    problem = Problem(
        id=problem_id,
        title=title,
        difficulty=difficulty,
        source_url=f"https://www.luogu.com.cn/problem/{problem_id}",
        fetched_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    
    # 创建 Hint 对象
    hints = []
    for level in range(1, 6):
        hint_key = f"hint{level}"
        content = old_problem.get(hint_key, "")
        
        # 清理提示内容（移除"提示 x："前缀）
        if content.startswith(f"提示{level}："):
            content = content[len(f"提示{level}："):]
        
        hint = Hint(
            problem_id=problem_id,
            level=level,
            content=content.strip(),
            model="qwen2.5:14b",  # 原项目使用的模型
            prompt_version="v1",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        hints.append(hint)
    
    return problem, hints


def migrate_data(
    data_dir: Path,
    db_path: Path,
    dry_run: bool = False
) -> dict:
    """
    迁移数据
    
    Args:
        data_dir: 旧数据目录
        db_path: 数据库路径
        dry_run: 是否只模拟运行
    
    Returns:
        统计信息
    """
    stats = {
        "total": 0,
        "imported": 0,
        "failed": 0,
        "skipped": 0
    }
    
    # 加载旧数据
    logger.info("正在加载旧数据...")
    old_problems = load_old_json(data_dir)
    stats["total"] = len(old_problems)
    logger.info(f"共加载 {stats['total']} 条题目记录")
    
    if dry_run:
        logger.info("[DRY RUN] 不实际写入数据库")
        return stats
    
    # 初始化数据库
    db = Database(db_path)
    
    try:
        # 迁移每条记录
        for i, old_problem in enumerate(old_problems, 1):
            try:
                problem_id = old_problem.get("id", f"unknown_{i}")
                
                # 检查是否已存在
                if db.has_hints(problem_id):
                    logger.debug(f"{problem_id} 已存在，跳过")
                    stats["skipped"] += 1
                    continue
                
                # 转换格式
                problem, hints = convert_to_v2_format(old_problem)
                
                # 保存到数据库
                db.save_problem(problem)
                for hint in hints:
                    db.save_hint(hint)
                
                stats["imported"] += 1
                
                if i % 100 == 0:
                    logger.info(f"已处理 {i}/{stats['total']} 条记录")
                    
            except Exception as e:
                logger.error(f"处理 {old_problem.get('id', 'unknown')} 失败：{e}")
                stats["failed"] += 1
        
        logger.info("=" * 50)
        logger.info("迁移完成！")
        logger.info(f"总记录数：{stats['total']}")
        logger.info(f"成功导入：{stats['imported']}")
        logger.info(f"跳过（已存在）: {stats['skipped']}")
        logger.info(f"失败：{stats['failed']}")
        logger.info("=" * 50)
        
    finally:
        db.close()
    
    return stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="迁移旧项目数据到 SQLite")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="旧数据目录"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/hint.db"),
        help="SQLite 数据库路径"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只模拟运行，不实际写入"
    )
    
    args = parser.parse_args()
    
    # 确保数据目录存在
    args.data_dir.mkdir(parents=True, exist_ok=True)
    args.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    stats = migrate_data(args.data_dir, args.db_path, args.dry_run)
    
    # 验证
    if not args.dry_run:
        db = Database(args.db_path)
        try:
            actual_count = db.get_statistics()["total_problems"]
            logger.info(f"数据库中实际题目数：{actual_count}")
            
            if stats["total"] > 0:
                success_rate = (stats["imported"] + stats["skipped"]) / stats["total"] * 100
                logger.info(f"迁移成功率：{success_rate:.2f}%")
        finally:
            db.close()


if __name__ == "__main__":
    main()
