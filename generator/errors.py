"""
错误定义模块

定义项目中使用的所有自定义异常类
"""


class HintLuoguError(Exception):
    """基础异常类"""
    pass


class ConfigurationError(HintLuoguError):
    """配置错误"""
    pass


class NetworkError(HintLuoguError):
    """网络请求错误"""
    pass


class LuoguParseError(HintLuoguError):
    """洛谷页面解析错误"""
    pass


class LLMError(HintLuoguError):
    """LLM 调用错误"""
    pass


class ValidationError(HintLuoguError):
    """Hint 验证错误"""
    pass


class DatabaseError(HintLuoguError):
    """数据库操作错误"""
    pass


class ExportError(HintLuoguError):
    """JSON 导出错误"""
    pass


class ProblemNotFoundError(HintLuoguError):
    """题目不存在错误"""
    pass
