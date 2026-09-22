"""
洛谷数据获取模块

负责从洛谷网站获取题目信息和题解
参考原项目：https://github.com/GCSG01/Hint-Luogu/blob/main/index.py

注意：洛谷使用 Cloudflare 防护，需要使用 Playwright 进行浏览器自动化
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import re
from playwright.async_api import async_playwright, Page, Browser
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
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._last_request_time: float = 0

    async def _get_browser(self) -> Browser:
        """获取浏览器实例"""
        if self._browser is None:
            playwright = await async_playwright().start()
            # 添加 --no-sandbox 和 --disable-setuid-sandbox 以在容器/服务器环境中运行
            self._browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
        return self._browser

    async def _get_page(self) -> Page:
        """获取页面对象"""
        if self._page is None:
            browser = await self._get_browser()
            self._page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        return self._page

    async def close(self):
        """关闭浏览器"""
        if self._page:
            await self._page.close()
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None

    async def _rate_limit(self):
        """请求限速"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.luogu_request_interval:
            await asyncio.sleep(self.config.luogu_request_interval - elapsed)
        self._last_request_time = time.time()

    async def _get(self, url: str) -> str:
        """发送 GET 请求（使用浏览器）"""
        page = await self._get_page()

        for attempt in range(self.config.luogu_max_retries):
            try:
                await self._rate_limit()
                
                # 访问页面并等待基本加载
                await page.goto(url, wait_until="commit", timeout=self.config.luogu_timeout * 1000)
                
                # 额外等待以确保动态内容加载完成
                await page.wait_for_timeout(5000)
                
                return await page.content()
            except Exception as e:
                if attempt == self.config.luogu_max_retries - 1:
                    raise NetworkError(f"请求失败：{url}, 错误：{e}")
                await asyncio.sleep(2 ** attempt)

        raise NetworkError(f"请求失败：{url}")

    @staticmethod
    def _remove_html_tags(html: str) -> str:
        """移除 HTML 标签提取纯文本"""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n")

    @staticmethod
    def _remove_empty_lines(text: str) -> str:
        """去除完全空白行"""
        return '\n'.join(line for line in text.splitlines() if line.strip())

    @staticmethod
    def _remove_space(text: str) -> str:
        """去除每行首尾空格"""
        return '\n'.join(line.strip() for line in text.splitlines())

    @staticmethod
    def _remove_multiline_code_blocks(html: str) -> str:
        """
        删除 HTML 中所有多行的 <code>...</code> 代码块
        保留单行代码块和内容中无换行符的代码块
        """
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

    def _parse_difficulty(self, html: str) -> int:
        """
        解析题目难度
        参考原项目逻辑
        """
        pos = html.find('"difficulty"')
        if pos == -1:
            return 0

        try:
            # 原项目：diff = int(html_content[pos + 13])
            diff_str = html[pos:pos + 30]
            match = re.search(r'"difficulty":\s*(\d+)', diff_str)
            if match:
                diff = int(match.group(1))
                if 0 <= diff <= 7:
                    return diff
            return 0
        except (ValueError, IndexError):
            return 0

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

        # 检查权限（参考原项目）
        if "权限不足" in html or "登录" in html:
            raise ProblemNotFoundError(f"无法访问题目 {problem_id}，可能需要登录")

        # 解析难度
        difficulty = self._parse_difficulty(html)

        # 解析题目内容（参考原项目）
        soup = BeautifulSoup(html, "html.parser")
        app_div = soup.find("div", id="app")

        if not app_div:
            raise LuoguParseError(f"无法解析题目页面：{problem_id}")

        # 提取标题
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else problem_id

        # 清理题面文本（参考原项目）
        full_html = str(app_div)
        statement = self._remove_html_tags(full_html)
        statement = statement.replace("请不要禁用脚本，否则网页无法正常加载", "")
        statement = self._remove_space(statement)
        statement = self._remove_empty_lines(statement)

        return Problem(
            id=problem_id,
            title=title,
            difficulty=difficulty,
            statement=statement,
            source_url=url,
            fetched_at=datetime.utcnow().isoformat()
        )

    async def _fetch_solution_content(self, url: str) -> Optional[str]:
        """
        获取单篇题解内容

        Args:
            url: 题解 URL

        Returns:
            题解内容或 None
        """
        try:
            html = await self._get(url)
            
            # 删除多行代码块（参考原项目）
            html_no_code = self._remove_multiline_code_blocks(html)

            soup = BeautifulSoup(html_no_code, "html.parser")
            app_div = soup.find("div", id="app")

            if not app_div:
                return None

            content = self._remove_html_tags(str(app_div))
            content = content.replace("请不要禁用脚本，否则网页无法正常加载", "")
            content = self._remove_space(content)
            content = self._remove_empty_lines(content)

            return content
        except Exception:
            return None

    async def fetch_solutions(self, problem_id: str, max_count: Optional[int] = None) -> List[Solution]:
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

        # 查找题解列表（参考原项目）
        ul_elements = soup.find_all("ul")
        if not ul_elements:
            return []

        # 使用 lxml 解析器（需要安装 lxml）
        try:
            soup = BeautifulSoup(str(ul_elements[0]), "lxml")
        except Exception:
            soup = BeautifulSoup(str(ul_elements[0]), "html.parser")
        
        li_elements = soup.find_all("li")

        solutions = []
        for li in li_elements:
            if len(solutions) >= max_count:
                break

            try:
                soup_li = BeautifulSoup(str(li), "lxml" if 'lxml' in str(type(soup)) else "html.parser")
                link = soup_li.find("a", class_="menu-item")

                if not link:
                    continue

                title = link.get_text().strip()

                # 过滤不包含题号的题解（参考原项目）
                if problem_id not in title or f"S{problem_id}" in title:
                    continue

                href = link.get("href", "")
                if not href.startswith("http"):
                    href = f"{self.BASE_URL}{href}"

                # 提取作者和时间（参考原项目）
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
                content = await self._fetch_solution_content(href)
                if content:
                    solutions.append(Solution(
                        problem_id=problem_id,
                        title=title,
                        author=author,
                        url=href,
                        content=content,
                        fetched_at=datetime.utcnow().isoformat()
                    ))
            except Exception:
                continue

        return solutions


async def fetch_problem_data(problem_id: str) -> tuple[Problem, List[Solution]]:
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
