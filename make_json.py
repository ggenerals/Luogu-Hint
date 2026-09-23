import os
import json
import re
import time
import requests
from pathlib import Path
from collections import defaultdict

hint_path = "./hints/"
out_dir = "./data/" # 打包后的 JSON 存放目录

Path(out_dir).mkdir(parents=True, exist_ok=True)

def get_content(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        return requests.get(url, headers=headers, timeout=10).text
    except:
        return ""

def get_luogu_meta(pid):
    """从洛谷抓取题目标题和难度（用于 JSON 索引）"""
    url = f"https://www.luogu.com.cn/problem/{pid}"
    html = get_content(url)
    if not html:
        return pid, 0
        
    title_match = re.search(r'<title>(.*?) - 洛谷</title>', html)
    title = title_match.group(1).strip() if title_match else pid
    
    diff_match = re.search(r'"difficulty"\s*:\s*(\d+)', html)
    diff = int(diff_match.group(1)) if diff_match else 0
    
    return title, diff

def parse_hints(file_path):
    """智能解析 txt 文件中的提示，处理换行和转义"""
    hints = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 使用正则精准提取 "提示X：内容"，忽略中间的多余空行
    matches = re.finditer(r'提示(\d)[：:]\s*(.*?)(?=\n*提示\d[：:]|\Z)', content, re.DOTALL)
    
    for m in matches:
        idx = int(m.group(1))
        # 清理文本：去除首尾空白，并将内部换行替换为空格，防止破坏 JSON 结构
        text = m.group(2).strip().replace('\n', ' ').replace('\r', '') 
        if 1 <= idx <= 5:
            hints[f"hint{idx}"] = text
            
    return hints

# 按千位分组字典
groups = defaultdict(list)

files = list(Path(hint_path).glob("P*.txt"))
print(f"🔍 共发现 {len(files)} 个有效的 Hint 文件，开始打包...")

for idx, file in enumerate(files):
    pid = file.stem # 例如 P17467
    
    # 1. 解析本地生成的提示
    hints = parse_hints(file)
    if len(hints) < 5:
        print(f"⚠️ 警告: {pid} 的提示不足 5 条，将尽力保留已有数据。")
        
    # 2. 获取元数据 (标题和难度)
    print(f"[{idx+1}/{len(files)}] 正在获取 {pid} 的元数据...")
    title, diff = get_luogu_meta(pid)
    
    # 3. 组装单道题目的数据字典
    item = {
        "id": pid,
        "title": title,
        "diff": diff
    }
    item.update(hints) # 将 hint1~hint5 合并进去
    
    # 4. 根据题号分组 (例如 P17467 -> 17)
    num_str = pid[1:] 
    if num_str.isdigit():
        group_id = int(num_str) // 1000
        groups[group_id].append(item)
        
    # 防止爬取元数据时被洛谷封 IP
    time.sleep(0.5)

# 写入 JSON 文件
print("\n📦 正在写入 JSON 文件...")
for group_id, items in groups.items():
    out_file = Path(out_dir) / f"{group_id}.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        # ensure_ascii=False 保证中文正常显示
        # separators=(',', ':') 去除多余空格，减小文件体积，加快前端加载速度
        json.dump(items, f, ensure_ascii=False, separators=(',', ':')) 
    print(f"✅ 成功生成 {out_file.name} (包含 {len(items)} 道题)")

print("\n🎉 打包全部完成！请查看 ./data/ 目录。")