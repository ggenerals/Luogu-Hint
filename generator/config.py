"""
配置管理模块

加载和管理项目配置
"""

import os
from pathlib import Path
from typing import Optional
import tomli
from .errors import ConfigurationError


class Config:
    """配置类"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径，默认为 config.toml
        """
        if config_path is None:
            config_path = "config.toml"

        self.config_path = Path(config_path)
        self._config = self._load_config()

        # 应用环境变量覆盖
        self._apply_env_overrides()

    def _load_config(self) -> dict:
        """加载配置文件"""
        if not self.config_path.exists():
            raise ConfigurationError(
                f"配置文件不存在：{self.config_path}\n"
                f"请复制 config.example.toml 到 {self.config_path} 并修改配置"
            )

        with open(self.config_path, "rb") as f:
            return tomli.load(f)

    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        # LLM 配置
        if os.getenv("LLM_PROVIDER"):
            self._config["llm"]["provider"] = os.getenv("LLM_PROVIDER")
        if os.getenv("LLM_MODEL"):
            self._config["llm"]["model"] = os.getenv("LLM_MODEL")
        if os.getenv("LLM_BASE_URL"):
            self._config["llm"]["base_url"] = os.getenv("LLM_BASE_URL")
        if os.getenv("LLM_API_KEY"):
            self._config["llm"]["api_key"] = os.getenv("LLM_API_KEY")

    @property
    def llm_provider(self) -> str:
        return self._config.get("llm", {}).get("provider", "ollama")

    @property
    def llm_model(self) -> str:
        return self._config.get("llm", {}).get("model", "qwen2.5:14b")

    @property
    def llm_base_url(self) -> str:
        return self._config.get("llm", {}).get("base_url", "http://localhost:11434")

    @property
    def llm_api_key(self) -> str:
        return self._config.get("llm", {}).get("api_key", "")

    @property
    def luogu_timeout(self) -> int:
        return self._config.get("luogu", {}).get("timeout", 20)

    @property
    def luogu_max_retries(self) -> int:
        return self._config.get("luogu", {}).get("max_retries", 3)

    @property
    def luogu_max_solutions(self) -> int:
        return self._config.get("luogu", {}).get("max_solutions", 3)

    @property
    def luogu_request_interval(self) -> float:
        return self._config.get("luogu", {}).get("request_interval", 1.5)

    @property
    def generation_hint_count(self) -> int:
        return self._config.get("generation", {}).get("hint_count", 5)

    @property
    def generation_prompt_version(self) -> str:
        return self._config.get("generation", {}).get("prompt_version", "v1")

    @property
    def database_path(self) -> Path:
        db_path = self._config.get("data", {}).get("database", "data/hint.db")
        return Path(db_path)

    @property
    def export_path(self) -> Path:
        export_path = self._config.get("data", {}).get("export", "frontend/data.json")
        return Path(export_path)

    @property
    def cache_dir(self) -> Path:
        cache_dir = self._config.get("data", {}).get("cache_dir", "data/cache")
        return Path(cache_dir)

    @property
    def log_level(self) -> str:
        return self._config.get("logging", {}).get("level", "INFO")

    def ensure_directories(self):
        """确保所有必要的目录存在"""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.export_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


# 全局配置实例（延迟初始化）
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
        _config.ensure_directories()
    return _config


def init_config(config_path: Optional[str] = None) -> Config:
    """初始化全局配置"""
    global _config
    _config = Config(config_path)
    _config.ensure_directories()
    return _config
