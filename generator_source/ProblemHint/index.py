import time
from random import shuffle
from datetime import datetime
import requests,re,lxml
from bs4 import BeautifulSoup
from ollama import Client
from pathlib import Path

def remove_html_tags(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()

def remove_empty_lines(text):
    """去除完全空白行（快速简洁方案）"""
    return '\n'.join(line for line in text.splitlines() if line.strip())

def get_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    return response.text

def remove_space(text):
    return '\n'.join(line.strip() for line in text.splitlines())

def get_statement(pid):
    url="https://www.luogu.com.cn/problem/" + pid
    html_content = get_content(url)
    # print(html_content)

    pos = html_content.find("\"difficulty\"")
    # for i in range(pos,pos+20):
    #     print(html_content[i])
    # print(html_content[pos + 13])
    try:
        diff = int(html_content[pos + 13])
        if not (0 <= diff <= 7): return 0
        if not (diff == 0 or diff >= 5): return -2
    except Exception as e:
        print("\n尝试获取 " + pid)
        print("[error] 权限不足")
        return -2

    soup = BeautifulSoup(html_content, "html.parser")
    target_div = soup.find("div", id="app")  # 通过 id 定位

    if not target_div: return 0

    full_html = str(target_div)          # 获取完整 HTML（含子标签）
    # text_content = target_div.get_text()  # 获取纯文本内容

    statement=remove_html_tags(full_html).replace("请不要禁用脚本，否则网页无法正常加载","")
    statement='\n'.join(line.strip() for line in statement.splitlines())
    statement=remove_empty_lines(statement)

    return statement
    # print(statement)

def remove_multiline_code_blocks(html):
    """
    删除 HTML 中所有多行的 <code>...</code> 代码块
    保留单行代码块和内容中无换行符的代码块
    """
    pattern = re.compile(
        r'(<code[^>]*>.*?</code>)',  # 匹配完整的 <code> 标签
        re.DOTALL | re.IGNORECASE  # 跨行匹配 + 忽略大小写
    )

    def is_multiline(match):
        """检查匹配到的代码块是否包含换行符"""
        return '\n' in match.group(1)

    # 替换所有含换行符的代码块为空字符串
    return pattern.sub(
        lambda m: '' if is_multiline(m) else m.group(),
        html
    )

def get_solution(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    html_content = response.text  # 获取HTML源码
    # print(html_content)  # 打印前500字符验证

    soup = BeautifulSoup(html_content, "html.parser")
    target_div = soup.find("div", id="app")  # 通过 id 定位

    if not target_div: return 0

    full_html = str(target_div)  # 获取完整 HTML（含子标签）
    full_html=remove_multiline_code_blocks(full_html)
    # text_content = target_div.get_text()  # 获取纯文本内容

    statement = remove_html_tags(full_html).replace("请不要禁用脚本，否则网页无法正常加载", "")
    statement = '\n'.join(line.strip() for line in statement.splitlines())
    statement = remove_empty_lines(statement)

    return statement

class Solution:
    def __init__(self,path,title,writer,time):
        self.path=path
        self.title=title
        self.writer=writer
        self.time=time
        self.content=get_solution(path)

    def write(self):
        print(self.title+" by "+self.writer+" "+self.time)

def get_solution_list(pid):
    url="https://www.luogu.com.cn/article?category=2&keyword="+pid+"&page=1"
    html_content = get_content(url)
    # print(html_content)

    soup = BeautifulSoup(html_content, "html.parser")
    target_div = soup.find("div", id="app")  # 通过 id 定位
    if not target_div: return 0

    soup = BeautifulSoup(str(target_div), "lxml")  # 使用 lxml 解析器
    target_div = soup.find_all("ul")[0]

    # 提取所有 <li> 标签
    soup = BeautifulSoup(str(target_div), "lxml")
    li_elements = soup.find_all("li")
    ans=[]
    for li in li_elements:
        soup1 = BeautifulSoup(str(li), "lxml")
        target_link = soup1.find('a')  # 类名为 menu-item
        title = target_link.get_text()
        if not (pid in title) or (("S"+pid) in title):
            continue
        if target_link:
            href = "https://www.luogu.com.cn"+target_link['href']
        else:
            href = ""
        target_link = soup1.find('small')
        text=target_link.get_text()
        writer=remove_space(text.split('@')[0])
        date=remove_space(text.split('@')[1])
        ans.append(Solution(href,title,writer,date))
        # print(title+": "+href+" "+writer+" "+date)
        if len(ans)>=3: break

    if len(ans)==0: return -1

    return ans

def get_ask_text(pid):
    statement=get_statement(pid)
    if statement==0:
        print("\n尝试获取 " + pid)
        return 0
    if statement==-2: return -2
    print("\n尝试获取 "+pid)
    sol_list=get_solution_list(pid)
    if sol_list==0: return 0
    if sol_list==-1: return -1
    # for t in sol_list:
    #     t.write()

    text='''
这是一道信息学竞赛中题目以及其题解：

---------- 题目内容开始 ----------

'''+statement+'''

---------- 题面内容结束 ----------
'''
    i=0
    for t in sol_list:
        i+=1
        text+='\n---------- 第 '+str(i)+' 篇题解开始 ----------\n\n'
        text+=t.content+'\n\n'
        text+='---------- 第 '+str(i)+' 篇题解结束 ----------\n'
    text+='''
现在请你根据上述内容，将题解内容概括成 5 个思维难度层层递进的步骤，然后整理成提示，以引导做题人一步步想到题目正确的解法。

要求：
1. 提示的程度从浅到深。
2. 提示的内容不能过度简单或平凡，例如题意的复述无需写在提示内。可以是题目中的某个关键性质或是需要使用某算法的思路等。
3. 前三条提示思路，后两条直接给出正解做法。
4. 提示可以较为详细，字数控制在 50 字内即可。
5. 关键要求：输出格式必须满足一行一个提示，格式为 “提示xxx：xxx”，每个提示只占单独一行，两两提示间由一个空行隔开。不需要多余的内容。
'''
    print("已找到 "+str(len(sol_list))+" 篇题解   提示词共 "+str(len(text))+" 字符")
    return text




# 指定 Ollama 服务地址和端口
client = Client(host='http://localhost:11434')
hint_path = "E:\\Cpp\\hint\\"

def get_hint(pid):
    file_path = Path(hint_path+".d."+pid+".txt")
    if file_path.exists():
        return
    file_path = Path(hint_path+".e."+pid+".txt")
    if file_path.exists():
        return
    file_path = Path(hint_path+pid+".txt")
    if file_path.exists():
        return

    start = time.time()

    text=get_ask_text(pid)
    if text==0:
        print("[error] 获取失败！爬取页面失败")
        return
    elif text==-1:
        print("[error] 获取失败！题解数量不足")
        with open(hint_path+".e."+pid+".txt", "w", encoding="utf-8") as f:
            f.write("")
        return
    elif text==-2:
        with open(hint_path+".d."+pid+".txt", "w", encoding="utf-8") as f:
            f.write("")
        return


    # 调用模型示例
    # deepseek-coder:6.7b
    response = client.generate(
        model="qwen2.5:14b",
        prompt=text,
    )

    text=response['response']
    text=remove_space(text)
    text=remove_empty_lines(text)
    ans=""
    tot=0
    for s in text.splitlines():
        ans+=s+"\n"
        tot+=1

    if tot<5:
        print("[error] 获取失败！输出格式错误")

    end = time.time()  # 记录结束时间
    elapsed = end - start
    print(f"获取成功！耗时: {elapsed:.4f} 秒")

    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    with open(hint_path+pid+".txt", "w", encoding="utf-8") as f:
        f.write(ans)
    # print(ans)
    # print(response['response'])

x=[]
for i in range(1000,13778):
    x.append(i)
# shuffle(x)

for i in x:
    get_hint("P"+str(i))