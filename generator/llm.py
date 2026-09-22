"""
LLM Provider 模块

支持多种 LLM 后端：Ollama, OpenAI-compatible 等
"""

import json
from abc import ABC, abstractmethod
from typing import Optional
import httpx

from .config import Config, get_config
from .errors import LLMError


class LLMProvider(ABC):
    """LLM Provider 抽象基类"""

    @abstractmethod
    async def generate(self, prompt: str, model: str) -> str:
        """
        生成文本

        Args:
            prompt: 输入提示词
            model: 模型名称

        Returns:
            生成的文本
        """
        pass


class OllamaProvider(LLMProvider):
    """Ollama LLM Provider"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate(self, prompt: str, model: str) -> str:
        """使用 Ollama 生成文本"""
        client = await self._get_client()
        url = f"{self.base_url}/api/generate"

        try:
            response = await client.post(
                url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama 请求失败：{e}")
        except json.JSONDecodeError as e:
            raise LLMError(f"Ollama 响应解析失败：{e}")


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible LLM Provider"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=120.0,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate(self, prompt: str, model: str) -> str:
        """使用 OpenAI-compatible API 生成文本"""
        client = await self._get_client()
        url = f"{self.base_url}/chat/completions"

        try:
            response = await client.post(
                url,
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            raise LLMError(f"OpenAI API 请求失败：{e}")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise LLMError(f"OpenAI API 响应解析失败：{e}")


def create_provider(config: Optional[Config] = None) -> LLMProvider:
    """
    根据配置创建 LLM Provider

    Args:
        config: 配置对象

    Returns:
        LLMProvider 实例
    """
    if config is None:
        config = get_config()

    provider_type = config.llm_provider.lower()

    if provider_type == "ollama":
        return OllamaProvider(config.llm_base_url)
    elif provider_type in ("openai", "openai-compatible"):
        if not config.llm_api_key:
            raise LLMError("OpenAI Provider 需要设置 API Key")
        return OpenAIProvider(config.llm_base_url, config.llm_api_key)
    else:
        raise LLMError(f"不支持的 LLM Provider: {provider_type}")
