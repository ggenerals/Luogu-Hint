"""
数据模型模块

使用 Pydantic 定义核心数据结构
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Problem(BaseModel):
    """题目模型"""
    id: str  # e.g., "P1000"
    title: str
    difficulty: int = 0  # 0-7, 0 means unknown
    statement: str = ""
    source_url: str = ""
    fetched_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class Solution(BaseModel):
    """题解模型"""
    id: Optional[int] = None
    problem_id: str
    title: str = ""
    author: str = ""
    url: str = ""
    content: str = ""
    fetched_at: Optional[str] = None

    class Config:
        from_attributes = True


class Hint(BaseModel):
    """Hint 模型"""
    problem_id: str
    level: int  # 1-5
    content: str
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class GenerationRecord(BaseModel):
    """生成记录模型"""
    id: Optional[int] = None
    problem_id: str
    provider: str
    model: str
    prompt_version: str
    status: str  # "success", "failed"
    error: Optional[str] = None
    created_at: Optional[str] = None
    finished_at: Optional[str] = None

    class Config:
        from_attributes = True


class HintOutput(BaseModel):
    """LLM 输出的 Hint 格式"""
    hints: list[dict[str, int | str]]

    class Config:
        from_attributes = True
