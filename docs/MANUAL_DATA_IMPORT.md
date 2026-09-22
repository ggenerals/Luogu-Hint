# 手动添加题目数据指南

由于洛谷使用 Cloudflare 防护，自动获取题目数据可能失败。您可以选择以下方法：

## 方法一：使用原项目数据（推荐）

如果您有原 Hint-Luogu 项目的数据文件：

1. **复制数据文件**
   ```bash
   mkdir -p data/old_data
   cp /path/to/old/project/data.json data/old_data/
   cp /path/to/old/project/dat*.json data/old_data/
   ```

2. **导入数据**
   ```bash
   python scripts/import_manual.py data/old_data/
   ```

3. **导出为新格式**
   ```bash
   hint-luogu export
   ```

## 方法二：手动创建单个题目 JSON

创建 `data/manual/P1000.json`：

```json
{
  "id": "P1000",
  "title": "A+B Problem",
  "difficulty": 1,
  "statement": "题目描述内容...",
  "solutions": [
    {
      "title": "P1000 题解",
      "author": "作者名",
      "content": "题解内容..."
    }
  ]
}
```

然后运行：

```bash
python scripts/import_single.py data/manual/P1000.json
```

## 方法三：在本地环境运行

在您平时浏览洛谷的电脑上（可能有登录状态和 Cookie）：

```bash
# 配置 LLM
export LLM_API_KEY="your-key"
export LLM_BASE_URL="https://..."
export LLM_MODEL="your-model"

# 添加题目
hint-luogu add P1000
```

## 方法四：从洛谷复制题目内容

1. 访问 https://www.luogu.com.cn/problem/P1000
2. 复制题目描述
3. 创建 JSON 文件（参考方法二）

## 导入后生成 Hint

导入题目数据后，使用已配置的 LLM 生成 Hint：

```bash
# 为单个题目生成
hint-luogu generate P1000

# 批量生成
hint-luogu batch P1000 P1001 P1002

# 导出前端数据
hint-luogu export
```

## 注意事项

- 洛谷的反爬虫机制可能导致自动获取失败
- 建议使用已有数据或手动提供数据
- 不要频繁请求洛谷网站
- 遵守洛谷的使用条款和版权要求
