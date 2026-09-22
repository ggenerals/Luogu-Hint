# Hint-Luogu V2

> 为洛谷题目生成五级渐进式提示（Hint）的可持续维护系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

## 📖 项目介绍

Hint-Luogu 是一个面向洛谷用户的题目 Hint 生成与展示系统。当你卡在某个算法题时，本系统可以提供 5 个逐级递进的提示，帮助你独立思考解决问题，而不是直接给出答案。

### ✨ 核心特性

- **五级渐进式 Hint**：从思考方向到核心算法，逐步引导
- **可持续维护**：不依赖特定设备、模型或绝对路径
- **模型无关**：支持 Ollama、OpenAI-compatible 等多种 LLM Provider
- **自动化流程**：一键获取题目、题解、生成 Hint、验证并导出
- **数据驱动**：SQLite 数据库作为唯一真实数据源
- **静态部署**：前端完全静态化，可通过 GitHub Pages 部署

### 🎯 使用场景

```bash
# 添加新题目的 Hint
hint-luogu add P3372

# 批量添加
hint-luogu batch P1000 P1001 P1002

# 重新生成已有题目的 Hint（更新模型/Prompt 后）
hint-luogu regenerate P3372

# 查看题目状态
hint-luogu status P3372

# 导出前端数据
hint-luogu export
```

## 🚀 Quick Start

### 前置要求

- Python 3.11+
- Ollama（或其他 OpenAI-compatible API）
- Git

### 1. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/hint-luogu.git
cd hint-luogu
```

### 2. 创建虚拟环境

```bash
# Linux/macOS
python -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -e .
```

### 4. 配置 LLM

#### 方式 A：使用 Ollama（推荐本地开发）

```bash
# 安装 Ollama: https://ollama.ai
ollama pull qwen2.5:14b

# 复制配置文件
cp config.example.toml config.toml
```

编辑 `config.toml`：

```toml
[llm]
provider = "ollama"
model = "qwen2.5:14b"
base_url = "http://localhost:11434"
```

#### 方式 B：使用 OpenAI-compatible API

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="https://api.example.com/v1"
export LLM_MODEL="your-model-name"
```

### 5. 初始化数据库

```bash
hint-luogu init
```

### 6. 添加第一道题目

```bash
hint-luogu add P1000
```

成功输出示例：

```
✓ Problem fetched: P1000 - A+B Problem
✓ Solutions fetched: 3
✓ Hint generated
✓ Hint validated
✓ Saved to database
✓ Exported to frontend/data.json

P1000 added successfully.
```

### 7. 启动前端预览

```bash
# 在浏览器中打开 frontend/index.html
# 或使用 Python 内置服务器
cd frontend
python -m http.server 8000
```

访问 `http://localhost:8000` 查看效果。

## 📁 项目结构

```
hint-luogu/
├── frontend/           # 静态前端文件
│   ├── index.html
│   ├── script.js
│   ├── style.css
│   └── data.json      # 自动生成的数据文件
├── generator/          # 核心生成器代码
│   ├── cli.py         # 命令行接口
│   ├── fetcher.py     # 洛谷数据获取
│   ├── llm.py         # LLM Provider 抽象
│   ├── generator.py   # Hint 生成逻辑
│   ├── validator.py   # Hint 验证器
│   └── exporter.py    # JSON 导出器
├── data/              # 数据目录
│   ├── hint.db        # SQLite 数据库
│   └── cache/         # HTTP 缓存
├── prompts/           # Prompt 模板
├── config.example.toml # 配置示例
└── pyproject.toml     # 项目配置
```

## 🔧 常用命令

| 命令 | 说明 |
|------|------|
| `hint-luogu init` | 初始化数据库和配置 |
| `hint-luogu add <P号>` | 添加新题目 |
| `hint-luogu regenerate <P号>` | 重新生成 Hint |
| `hint-luogu fetch <P号>` | 仅获取题目和题解 |
| `hint-luogu generate <P号>` | 仅生成 Hint（需已获取题目） |
| `hint-luogu validate <P号>` | 验证已有 Hint |
| `hint-luogu export` | 导出前端 JSON |
| `hint-luogu status <P号>` | 查看题目状态 |
| `hint-luogu batch <P号列表>` | 批量处理 |
| `hint-luogu list` | 列出所有题目 |

## ⚙️ 配置说明

完整配置项见 `config.example.toml`：

```toml
[llm]
provider = "ollama"
model = "qwen2.5:14b"
base_url = "http://localhost:11434"

[luogu]
timeout = 20
max_retries = 3
max_solutions = 3
request_interval = 1.5  # 请求间隔（秒）

[generation]
hint_count = 5
prompt_version = "v1"

[data]
database = "data/hint.db"
export = "frontend/data.json"

[logging]
level = "INFO"
```

## 🧪 测试

```bash
# 运行单元测试
pytest

# 带覆盖率
pytest --cov=generator

# 代码检查
ruff check .

# 格式化
ruff format .
```

## 🌐 部署到 GitHub Pages

项目包含 GitHub Actions 工作流，自动部署：

1. 推送代码到 `main` 分支
2. Actions 自动运行测试、导出数据
3. 部署到 GitHub Pages

确保在仓库设置中启用 GitHub Pages：
- Source: GitHub Actions

## 📝 开发指南

详细开发文档请参阅 [DEVELOPMENT.md](docs/DEVELOPMENT.md)

### 快速开始开发

```bash
# 1. 阅读文档
cat docs/DEVELOPMENT.md

# 2. 运行测试
pytest

# 3. 测试添加题目
hint-luogu add P1001

# 4. 检查数据库
hint-luogu status P1001
```

## ⚠️ 注意事项

- **洛谷用户协议**：本项目对洛谷的请求已限速（默认 1.5 秒/请求），请勿擅自调高频率，否则造成的后果请自行承担
- **版权尊重**：前端仅展示 Hint，题解内容仅供 LLM 生成 Hint 时使用，不直接展示
- **API Key 安全**：切勿将 API Key 提交到 Git，使用环境变量或本地配置文件
- **数据备份**：定期备份 `data/hint.db` 数据库文件

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- 原项目作者：[UniGravityqwq](https://github.com/UniGravityqwq)
- 洛谷：提供题目和题解平台
- Ollama：本地 LLM 运行框架
