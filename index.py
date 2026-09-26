import time
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from openai import OpenAI
import os
import random

# 自动清除可能导致报错的 socks 代理环境变量
for key in ['all_proxy', 'ALL_PROXY', 'http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY']:
    if key in os.environ and 'socks' in os.environ[key].lower():
        del os.environ[key]

import time
import re
# ... 下面接着你原来的 import 语句

# ==================== 配置区 ====================

# client = OpenAI(
#     api_key="ollama",            # Ollama 不需要真实密钥，但OpenAI SDK要求此字段非空，填任意字符串即可
#     base_url="http://localhost:11434/v1"  # Ollama 本地 OpenAI 兼容端点
# )

# MODEL_NAME = "modelscope.cn/Qwen/Qwen3-0.6B-GGUF"

# 选择一个 OpenAI 兼容的 API（任选其一，取消注释）

# 方案1: DeepSeek API（性价比最高）
# 获取 key: https://platform.deepseek.com/api_keys
client = OpenAI(
    api_key="sk-55b86f61c4ff49e1b33e505ec393d79d",
    base_url="https://api.deepseek.com"
)
MODEL_NAME = "deepseek-flash"

# 方案2: SiliconFlow（硅基流动，有免费 Qwen 额度）
# 获取 key: https://cloud.siliconflow.cn/account/ak
# client = OpenAI(
#     api_key="sk-your-siliconflow-key",
#     base_url="https://api.siliconflow.cn/v1"
# )
# MODEL_NAME = "Qwen/Qwen2.5-14B-Instruct"  # 免费

# 方案3: 阿里云百炼（Qwen 官方）
# 获取 key: https://bailian.console.aliyun.com/
# client = OpenAI(
#     api_key="sk-your-dashscope-key",
#     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
# )
# MODEL_NAME = "qwen-plus"

# 方案4: OpenAI
# client = OpenAI(api_key="sk-xxx")
# MODEL_NAME = "gpt-4o-mini"

# 输出路径，改成你想保存的目录
hint_path = "./hints/"
# ================================================

Path(hint_path).mkdir(parents=True, exist_ok=True)

def remove_html_tags(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()

def remove_empty_lines(text):
    return '\n'.join(line for line in text.splitlines() if line.strip())

def get_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # 【优化1】加入 timeout=15，如果15秒没响应就报错跳过，防止无限卡死
    # 【优化2】打印当前正在请求的网址，让你知道程序没死
    print(f"  -> 正在请求: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # 检查是否返回了 404/500 等错误码
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"  [!] 网络请求失败: {e}")
        return "" # 返回空字符串，后续逻辑会处理失败情况

def remove_space(text):
    return '\n'.join(line.strip() for line in text.splitlines())

def get_statement(pid):
    url = f"https://www.luogu.com.cn/problem/{pid}"
    html_content = get_content(url)
    
    if not html_content:
        return 0 # 网络请求失败
        
    # 【优化1】使用正则表达式提取难度，无视 JSON 格式的空格或微调
    match = re.search(r'"difficulty"\s*:\s*(\d+)', html_content)
    
    if not match:
        print(f"[{pid}] ⚠️ 无法在网页中找到 difficulty 字段，可能洛谷更新了网页结构或被反爬拦截。")
        return -2
        
    diff = int(match.group(1))
    print(f"[{pid}] 📊 获取到难度值: {diff}")
    
    # 【优化2】只保留蓝题及以上 (5:蓝, 6:紫, 7:黑)
    # 注意：如果洛谷新版难度体系整体偏移了（比如蓝题变成了6），请修改这里的 < 5
    if diff < 5: 
        return -2 # 难度不够，标记为 .d. 并跳过
        
    soup = BeautifulSoup(html_content, "html.parser")
    target_div = soup.find("div", id="app")
    if not target_div: return 0
    
    statement = remove_html_tags(str(target_div)).replace("请不要禁用脚本，否则网页无法正常加载", "")
    return remove_empty_lines(remove_space(statement))

def remove_multiline_code_blocks(html):
    pattern = re.compile(r'(<code[^>]*>.*?</code>)', re.DOTALL | re.IGNORECASE)
    return pattern.sub(
        lambda m: '' if '\n' in m.group(1) else m.group(),
        html
    )

def get_solution(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    target_div = soup.find("div", id="app")
    if not target_div: return ""
    
    full_html = remove_multiline_code_blocks(str(target_div))
    statement = remove_html_tags(full_html).replace("请不要禁用脚本，否则网页无法正常加载", "")
    return remove_empty_lines(remove_space(statement))

class Solution:
    def __init__(self, path, title, writer, time_str):
        self.path = path
        self.title = title
        self.writer = writer
        self.time = time_str
        self.content = get_solution(path)

def get_solution_list(pid):
    url = f"https://www.luogu.com.cn/article?category=2&keyword={pid}&page=1"
    html_content = get_content(url)
    soup = BeautifulSoup(html_content, "html.parser")
    target_div = soup.find("div", id="app")
    if not target_div: return -1
    
    soup = BeautifulSoup(str(target_div), "lxml")
    try:
        target_div = soup.find_all("ul")[0]
    except IndexError:
        return -1
    
    soup = BeautifulSoup(str(target_div), "lxml")
    ans = []
    for li in soup.find_all("li"):
        soup1 = BeautifulSoup(str(li), "lxml")
        target_link = soup1.find('a')
        if not target_link: continue
        title = target_link.get_text()
        if not (pid in title) or (("S" + pid) in title):
            continue
        
        href = "https://www.luogu.com.cn" + target_link['href']
        target_link2 = soup1.find('small')
        if not target_link2: continue
        text = target_link2.get_text()
        writer = remove_space(text.split('@')[0])
        date = remove_space(text.split('@')[1])
        ans.append(Solution(href, title, writer, date))
        if len(ans) >= 3: break
    
    return ans if ans else -1

def get_ask_text(pid):
    statement = get_statement(pid)
    if statement == 0 or statement == -2: return statement
    print(f"\n尝试获取 {pid}")
    
    sol_list = get_solution_list(pid)
    if sol_list == -1: return -1
    
    text = '''这是一道信息学竞赛中题目以及其题解：

---------- 题目内容开始 ----------
''' + statement + '''
---------- 题面内容结束 ----------
'''
    i = 0
    for t in sol_list:
        i += 1
        text += f'\n---------- 第 {i} 篇题解开始 ----------\n\n'
        text += t.content + '\n\n'
        text += f'---------- 第 {i} 篇题解结束 ----------\n'
    
    text += '''
现在请你根据上述内容，将题解内容概括成 5 个思维难度层层递进的步骤，然后整理成提示，以引导做题人一步步想到题目正确的解法。

要求：
1. 提示的程度从浅到深。
2. 提示的内容不能过度简单或平凡，例如题意的复述无需写在提示内。可以是题目中的某个关键性质或是需要使用某算法的思路等。
3. 前三条提示思路，后两条直接给出正解做法。
4. 提示可以较为详细，字数控制在 50 字内即可。
5. 关键要求：输出格式必须满足一行一个提示，格式为 "提示xxx：xxx"，每个提示只占单独一行，两两提示间由一个空行隔开。不需要多余的内容。
'''
    print(f"已找到 {len(sol_list)} 篇题解 提示词共 {len(text)} 字符")
    return text

def get_hint(pid):
    print(f"[{pid}] 开始检查历史文件...")
    for prefix in [".d.", ".e.", ""]:
        file_path = Path(hint_path + prefix + pid + ".txt")
        if file_path.exists():
            print(f"[{pid}] 发现已存在的文件 {file_path.name}，跳过生成。")
            return
            
    print(f"[{pid}] 正在获取题目信息...")
    text = get_ask_text(pid)
    
    if text == 0:
        print(f"[{pid}] ❌ 失败：爬取页面失败或题目不存在。")
        return
    elif text == -1:
        print(f"[{pid}] ❌ 失败：没有找到足够的题解。")
        Path(hint_path + ".e." + pid + ".txt").touch()
        return
    elif text == -2:
        print(f"[{pid}] ⚠️ 跳过：题目难度不符合要求（非蓝题及以上）或权限不足。")
        Path(hint_path + ".d." + pid + ".txt").touch()
        return
    
    print(f"[{pid}] 🚀 题目和题解获取成功！正在调用 AI 生成提示...")
    
    # 【修复】重新定义 start_time
    start_time = time.time() 
    
    try:
        # 【优化】将 max_tokens 提高到 4096，防止 AI 输出到一半被截断
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "你是一个信息学竞赛题解专家。请务必严格输出 5 条提示，不要遗漏第 5 条！"}, 
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=4096 
        )
        generated_text = response.choices[0].message.content
    except Exception as e:
        print(f"[{pid}] ❌ API 调用发生异常: {e}")
        return

    if not generated_text:
        print(f"[{pid}] ❌ AI 返回了空内容。")
        return

    # 【优化】智能解析 AI 输出，提取所有以“提示”开头的行
    lines = [line.strip() for line in generated_text.splitlines() if line.strip()]
    hint_lines = [line for line in lines if line.startswith("提示")]
    
    if len(hint_lines) < 5:
        print(f"[{pid}] ⚠️ 警告：AI 输出的提示不足 5 条（实际 {len(hint_lines)} 条）。")
        if len(hint_lines) == 0:
            print(f"[{pid}] 🔍 AI 原始返回内容前 200 字:\n{generated_text[:200]}")
            return # 如果一条提示都没识别出来，直接放弃保存

    # 用双换行符连接，完美契合原作者 jsonmaker.py 的读取逻辑
    ans = "\n\n".join(hint_lines)
    
    # 【修复】正确计算耗时
    elapsed = time.time() - start_time
    print(f"[{pid}] ✅ 获取成功！耗时: {elapsed:.2f} 秒")
    
    with open(hint_path + pid + ".txt", "w", encoding="utf-8") as f:
        f.write(ans + "\n")
    print(f"[{pid}] 💾 已成功保存到 {hint_path + pid + ".txt"}")

# ============ 批量生成 ============
if __name__ == "__main__":
    for i in range(1080, 1082): 
        pid = "P" + str(i)
        print(f"\n========== 开始处理 {pid} ==========")
        get_hint(pid)
        print(f"========== {pid} 处理结束 ==========\n")
        
        # 防止被洛谷封 IP
        time.sleep(random.uniform(3, 6))