"""
命令行接口模块

提供 hint-luogu CLI 命令
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from .config import init_config, get_config, ConfigurationError
from .database import Database
from .generator import HintGenerator, add_problem, regenerate_problem, export_data
from .errors import HintLuoguError


def setup_logging(level: str = "INFO"):
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def cmd_add(args):
    """添加题目"""
    async def run():
        generator = HintGenerator()
        try:
            success = await generator.add_problem(args.problem_id, force=args.force)
            if success:
                print(f"✓ {args.problem_id} 添加成功")
                return 0
            else:
                print(f"✗ {args.problem_id} 添加失败或已存在")
                return 1
        finally:
            await generator.close()

    return asyncio.run(run())


def cmd_regenerate(args):
    """重新生成"""
    async def run():
        generator = HintGenerator()
        try:
            success = await generator.regenerate(args.problem_id)
            if success:
                print(f"✓ {args.problem_id} 重新生成成功")
                return 0
            else:
                print(f"✗ {args.problem_id} 重新生成失败")
                return 1
        finally:
            await generator.close()

    return asyncio.run(run())


def cmd_export(args):
    """导出 JSON"""
    async def run():
        generator = HintGenerator()
        try:
            data = await generator.export()
            count = len(data.get("problems", []))
            print(f"✓ 已导出 {count} 道题目到 {get_config().export_path}")
            return 0
        finally:
            await generator.close()

    return asyncio.run(run())


def cmd_status(args):
    """查看状态"""
    generator = HintGenerator()
    try:
        stats = generator.get_statistics()
        print(f"\n数据库统计:")
        print(f"  总题目数：{stats['total_problems']}")
        print(f"  有 Hint 的题目：{stats['problems_with_hints']}")
        print(f"  总 Hint 数：{stats['total_hints']}")
        print(f"  总题解数：{stats['total_solutions']}")

        if args.problem_id:
            db = generator.db
            problem = db.get_problem(args.problem_id)
            if problem:
                print(f"\n{args.problem_id}:")
                print(f"  标题：{problem.title}")
                print(f"  难度：{problem.difficulty}")
                hints = db.get_hints(args.problem_id)
                if hints:
                    print(f"  Hint 数量：{len(hints)}")
                else:
                    print(f"  Hint 数量：0 (尚未生成)")
            else:
                print(f"\n{args.problem_id} 不在数据库中")

        return 0
    finally:
        generator.close()


def cmd_batch(args):
    """批量处理"""
    async def run():
        generator = HintGenerator()
        try:
            success_count = 0
            fail_count = 0

            for problem_id in args.problem_ids:
                success = await generator.add_problem(problem_id, force=args.force)
                if success:
                    print(f"✓ {problem_id}")
                    success_count += 1
                else:
                    print(f"✗ {problem_id}")
                    fail_count += 1

            print(f"\n完成：成功 {success_count}, 失败 {fail_count}")
            return 0 if fail_count == 0 else 1
        finally:
            await generator.close()

    return asyncio.run(run())


def cmd_init(args):
    """初始化配置"""
    config_path = Path("config.toml")
    if config_path.exists():
        print(f"配置文件已存在：{config_path}")
        return 0

    example_path = Path("config.example.toml")
    if not example_path.exists():
        print("错误：找不到 config.example.toml")
        return 1

    with open(example_path, "r", encoding="utf-8") as f:
        content = f.read()

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✓ 已创建配置文件：{config_path}")
    print("请编辑配置文件后使用")
    return 0


def cmd_migrate(args):
    """迁移旧数据"""
    from scripts.migrate_old_data import migrate

    success = migrate(args.source_dir, args.keep_original)
    return 0 if success else 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        prog="hint-luogu",
        description="洛谷题目 Hint 生成器"
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # add 命令
    add_parser = subparsers.add_parser("add", help="添加新题目")
    add_parser.add_argument("problem_id", help="题目 ID，如 P1000")
    add_parser.add_argument("--force", "-f", action="store_true", help="强制重新生成")
    add_parser.set_defaults(func=cmd_add)

    # regenerate 命令
    regen_parser = subparsers.add_parser("regenerate", help="重新生成题目 Hint")
    regen_parser.add_argument("problem_id", help="题目 ID")
    regen_parser.set_defaults(func=cmd_regenerate)

    # export 命令
    export_parser = subparsers.add_parser("export", help="导出 JSON")
    export_parser.set_defaults(func=cmd_export)

    # status 命令
    status_parser = subparsers.add_parser("status", help="查看状态")
    status_parser.add_argument("problem_id", nargs="?", help="可选：题目 ID")
    status_parser.set_defaults(func=cmd_status)

    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量添加题目")
    batch_parser.add_argument("problem_ids", nargs="+", help="题目 ID 列表")
    batch_parser.add_argument("--force", "-f", action="store_true", help="强制重新生成")
    batch_parser.set_defaults(func=cmd_batch)

    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化配置")
    init_parser.set_defaults(func=cmd_init)

    # migrate 命令
    migrate_parser = subparsers.add_parser("migrate", help="迁移旧项目数据")
    migrate_parser.add_argument("--source-dir", default="data", help="原数据目录")
    migrate_parser.add_argument("--keep-original", action="store_true", help="保留原始文件")
    migrate_parser.set_defaults(func=cmd_migrate)

    # 全局参数
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # 设置日志
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)

    # 初始化配置
    try:
        if args.config:
            init_config(args.config)
        else:
            init_config()
    except ConfigurationError as e:
        print(f"配置错误：{e}", file=sys.stderr)
        return 1

    # 执行命令
    try:
        return args.func(args)
    except HintLuoguError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消")
        return 130


if __name__ == "__main__":
    sys.exit(main())
