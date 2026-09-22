"""
洛谷数据获取模块

负责从洛谷网站获取题目信息和题解
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from .config import Config, get_config
from .models import Problem, Solution
from .errors import NetworkError, LuoguParseError, ProblemNotFoundError


class LuoguFetcher:
    """洛谷数据获取器"""

    BASE_URL = "https://www.luogu.com.cn"

    def __init__(self, config: Optional[Config] = None):
        """
        初始化获取器

        Args:
            config: 配置对象
        """
        self.config = config or get_config()
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.luogu_timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _rate_limit(self):
        """请求限速"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.luogu_request_interval:
            await asyncio.sleep(self.config.luogu_request_interval - elapsed)
        self._last_request_time = time.time()

    async def _get(self, url: str) -> str:
        """发送 GET 请求"""
        client = await self._get_client()

        for attempt in range(self.config.luogu_max_retries):
            try:
                await self._rate_limit()
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as e:
                if attempt == self.config.luogu_max_retries - 1:
                    raise NetworkError(f"请求失败：{url}, 错误：{e}")
                await asyncio.sleep(2 ** attempt)

        raise NetworkError(f"请求失败：{url}")

    def _parse_difficulty(self, html: str) -> int:
        """解析题目难度"""
        pos = html.find('"difficulty"')
        if pos == -1:
            return 0

        try:
            # 查找 difficulty 后面的数字
            diff_str = html[pos:pos + 30]
            import re
            match = re.search(r'"difficulty":\s*(\d+)', diff_str)
            if match:
                diff = int(match.group(1))
                if 0 <= diff <= 7:
                    return diff
            return 0
        except (ValueError, IndexError):
            return 0

    def _extract_text(self, html: str) -> str:
        """从 HTML 提取纯文本"""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")

        # 清理空白行
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    async def fetch_problem(self, problem_id: str) -> Problem:
        """
        获取题目信息

        Args:
            problem_id: 题目 ID，如 "P1000"

        Returns:
            Problem 对象
        """
        url = f"{self.BASE_URL}/problem/{problem_id}"
        html = await self._get(url)

        # 检查权限
        if "权限不足" in html or "登录" in html:
            raise ProblemNotFoundError(f"无法访问题目 {problem_id}，可能需要登录")

        # 解析难度
        difficulty = self._parse_difficulty(html)

        # 解析题目内容
        soup = BeautifulSoup(html, "html.parser")
        app_div = soup.find("div", id="app")

        if not app_div:
            raise LuoguParseError(f"无法解析题目页面：{problem_id}")

        # 提取标题
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else problem_id

        # 清理题面文本
        statement = self._extract_text(str(app_div))
        statement = statement.replace("请不要禁用脚本，否则网页无法正常加载", "")

        return Problem(
            id=problem_id,
            title=title,
            difficulty=difficulty,
            statement=statement,
            source_url=url,
            fetched_at=datetime.utcnow().isoformat()
        )

    async def _remove_code_blocks(self, html: str) -> str:
        """删除多行代码块"""
        import re
        pattern = re.compile(
            r'(<code[^>]*>.*?</code>)',
            re.DOTALL | re.IGNORECASE
        )

        def is_multiline(match):
            return '\n' in match.group(1)

        return pattern.sub(
            lambda m: '' if is_multiline(m) else m.group(),
            html
        )

    async def fetch_solution(self, url: str) -> Optional[Solution]:
        """
        获取单篇题解

        Args:
            url: 题解 URL

        Returns:
            Solution 对象或 None
        """
        try:
            html = await self._get(url)
            html_no_code = await self._remove_code_blocks(html)

            soup = BeautifulSoup(html_no_code, "html.parser")
            app_div = soup.find("div", id="app")

            if not app_div:
                return None

            content = self._extract_text(str(app_div))
            content = content.replace("请不要禁用脚本，否则网页无法正常加载", "")

            # 提取标题和作者
            title_tag = soup.find("title")
            title = title_tag.get_text().strip() if title_tag else ""

            return Solution(
                problem_id="",  # 稍后设置
                title=title,
                author="",
                url=url,
                content=content,
                fetched_at=datetime.utcnow().isoformat()
            )
        except Exception as e:
            return None

    async def fetch_solutions(self, problem_id: str, max_count: Optional[int] = None) -> list[Solution]:
        """
        获取题目的题解列表

        Args:
            problem_id: 题目 ID
            max_count: 最大获取数量

        Returns:
            Solution 列表
        """
        if max_count is None:
            max_count = self.config.luogu_max_solutions

        url = f"{self.BASE_URL}/article?category=2&keyword={problem_id}&page=1"
        html = await self._get(url)

        soup = BeautifulSoup(html, "html.parser")
        app_div = soup.find("div", id="app")

        if not app_div:
            return []

        # 查找题解列表
        ul_elements = soup.find_all("ul")
        if not ul_elements:
            return []

        soup = BeautifulSoup(str(ul_elements[0]), "lxml")
        li_elements = soup.find_all("li")

        solutions = []
        for li in li_elements:
            if len(solutions) >= max_count:
                break

            soup_li = BeautifulSoup(str(li), "lxml")
            link = soup_li.find("a", class_="menu-item")

            if not link:
                continue

            title = link.get_text().strip()

            # 过滤不包含题号的题解
            if problem_id not in title or f"S{problem_id}" in title:
                continue

            href = link.get("href", "")
            if not href.startswith("http"):
                href = f"{self.BASE_URL}{href}"

            # 提取作者和时间
            small_tag = soup_li.find("small")
            author = ""
            date = ""
            if small_tag:
                text = small_tag.get_text()
                if "@" in text:
                    parts = text.split("@")
                    author = parts[0].strip()
                    date = parts[1].strip() if len(parts) > 1 else ""

            # 获取题解内容
            solution = await self.fetch_solution(href)
            if solution:
                solution.problem_id = problem_id
                solution.author = author
                solutions.append(solution)

        return solutions

    async def fetch_cache_key(self, key: str) -> Optional[str]:
        """从缓存获取数据"""
        cache_file = self.config.cache_dir / f"{key}.html"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()
        return None

    async def save_cache(self, key: str, content: str):
        """保存数据到缓存"""
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.config.cache_dir / f"{key}.html"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(content)


async def fetch_problem_data(problem_id: str) -> tuple[Problem, list[Solution]]:
    """
    获取题目完整数据

    Args:
        problem_id: 题目 ID

    Returns:
        (Problem, [Solution]) 元组
    """
    config = get_config()
    fetcher = LuoguFetcher(config)

    try:
        problem = await fetcher.fetch_problem(problem_id)
        solutions = await fetcher.fetch_solutions(problem_id)

        return problem, solutions
    finally:
        await fetcher.close()
