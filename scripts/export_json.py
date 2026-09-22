#!/usr/bin/env python3
"""
JSON 导出脚本

从 SQLite 数据库导出前端所需的 JSON 文件
"""

import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.database import Database
from generator.config import get_config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def export_json(db_path: Path, output_path: Path) -> dict:
    """
    导出 JSON
    
    Args:
        db_path: 数据库路径
        output_path: 输出文件路径
    
    Returns:
        导出的数据
    """
    db = Database(db_path)
    
    try:
        data = db.export_json(str(output_path))
        
        problem_count = len(data.get("problems", []))
        logger.info(f"成功导出 {problem_count} 道题目到 {output_path}")
        
        return data
        
    finally:
        db.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="从 SQLite 导出 JSON")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/hint.db"),
        help="SQLite 数据库路径"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("frontend/data.json"),
        help="输出 JSON 文件路径"
    )
    
    args = parser.parse_args()
    
    # 确保输出目录存在
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    config = get_config()
    db_path = args.db_path if args.db_path.exists() else config.database_path
    output_path = args.output
    
    export_json(Path(db_path), Path(output_path))


if __name__ == "__main__":
    main()
