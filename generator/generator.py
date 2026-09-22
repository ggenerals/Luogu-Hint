"""
Hint 生成器模块

核心 Hint 生成逻辑
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from .config import Config, get_config
from .database import Database
from .luogu import LuoguFetcher, fetch_problem_data
from .llm import LLMProvider, create_provider
from .prompt import PromptManager, get_prompt_manager
from .validator import HintValidator, get_validator
from .models import Problem, Solution, Hint, GenerationRecord
from .errors import LLMError, ValidationError


logger = logging.getLogger(__name__)


class HintGenerator:
    """Hint 生成器"""

    def __init__(self, config: Optional[Config] = None):
        """
        初始化生成器

        Args:
            config: 配置对象
        """
        self.config = config or get_config()
        self.db = Database(self.config.database_path)
        self.prompt_manager = get_prompt_manager()
        self.validator = get_validator()
        self.llm_provider: Optional[LLMProvider] = None

    async def _get_llm_provider(self) -> LLMProvider:
        """获取 LLM Provider"""
        if self.llm_provider is None:
            self.llm_provider = create_provider(self.config)
        return self.llm_provider

    async def close(self):
        """关闭资源"""
        if self.llm_provider:
            await self.llm_provider.close()
        self.db.close()

    async def generate_hints(
        self,
        problem: Problem,
        solutions: list[Solution]
    ) -> list[Hint]:
        """
        生成 Hint

        Args:
            problem: 题目信息
            solutions: 题解列表

        Returns:
            Hint 列表
        """
        # 构建 Prompt - 传递字典格式
        solution_dicts = [{"content": s.content} for s in solutions]
        prompt = self.prompt_manager.build_prompt(
            title=problem.title,
            statement=problem.statement,
            solutions=solution_dicts
        )

        logger.info(f"正在为 {problem.id} 生成 Hint...")

        # 调用 LLM
        provider = await self._get_llm_provider()
        response = await provider.generate(
            prompt=prompt,
            model=self.config.llm_model
        )

        # 验证输出
        hints = self.validator.validate(response)

        # 设置元数据
        for hint in hints:
            hint.problem_id = problem.id
            hint.model = self.config.llm_model
            hint.prompt_version = self.config.generation_prompt_version

        return hints

    async def add_problem(self, problem_id: str, force: bool = False) -> bool:
        """
        添加新题目并生成 Hint

        Args:
            problem_id: 题目 ID
            force: 是否强制重新生成

        Returns:
            是否成功
        """
        # 检查是否已存在
        if not force and self.db.has_hints(problem_id):
            logger.warning(f"{problem_id} 已有 Hint，跳过。使用 --force 强制重新生成")
            return False

        # 清除旧数据（如果需要）
        if force:
            self.db.clear_problem(problem_id)

        try:
            # 获取题目和题解
            fetcher = LuoguFetcher(self.config)
            try:
                problem = await fetcher.fetch_problem(problem_id)
                solutions = await fetcher.fetch_solutions(problem_id)
            finally:
                await fetcher.close()

            if not solutions:
                logger.error(f"{problem_id} 没有获取到题解，跳过")
                self._record_generation(
                    problem_id, "failed", "No solutions found"
                )
                return False

            logger.info(f"获取到 {len(solutions)} 篇题解")

            # 保存到数据库
            self.db.save_problem(problem)
            for sol in solutions:
                sol.problem_id = problem_id
                self.db.save_solution(sol)

            # 生成 Hint
            hints = await self.generate_hints(problem, solutions)

            # 保存 Hint
            for hint in hints:
                self.db.save_hint(hint)

            logger.info(f"{problem_id} Hint 生成成功")
            self._record_generation(problem_id, "success")

            return True

        except Exception as e:
            logger.error(f"{problem_id} 处理失败：{e}")
            self._record_generation(problem_id, "failed", str(e))
            return False

    def _record_generation(
        self,
        problem_id: str,
        status: str,
        error: Optional[str] = None
    ):
        """记录生成历史"""
        record = GenerationRecord(
            problem_id=problem_id,
            provider=self.config.llm_provider,
            model=self.config.llm_model,
            prompt_version=self.config.generation_prompt_version,
            status=status,
            error=error
        )
        self.db.save_generation_record(record)

    async def regenerate(self, problem_id: str) -> bool:
        """
        重新生成题目的 Hint

        Args:
            problem_id: 题目 ID

        Returns:
            是否成功
        """
        return await self.add_problem(problem_id, force=True)

    async def export(self) -> dict:
        """
        导出 JSON

        Returns:
            导出的数据
        """
        return self.db.export_json(self.config.export_path)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return self.db.get_statistics()


async def add_problem(problem_id: str, force: bool = False) -> bool:
    """便捷函数：添加题目"""
    generator = HintGenerator()
    try:
        return await generator.add_problem(problem_id, force)
    finally:
        await generator.close()


async def regenerate_problem(problem_id: str) -> bool:
    """便捷函数：重新生成"""
    generator = HintGenerator()
    try:
        return await generator.regenerate(problem_id)
    finally:
        await generator.close()


async def export_data() -> dict:
    """便捷函数：导出数据"""
    generator = HintGenerator()
    try:
        return await generator.export()
    finally:
        await generator.close()
