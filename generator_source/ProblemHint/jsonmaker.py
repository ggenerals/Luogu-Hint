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

hint_path = "E:\\Cpp\\hint\\"

# ans_text=""

def get_statement(pid):
    # print(pid)

    with open(hint_path+pid+".txt", 'r', encoding='utf-8') as file:
        line = file.readlines()[:5]

        url="https://www.luogu.com.cn/problem/" + pid
        html_content = get_content(url)
        # print(html_content)
        print(pid)

        pos = html_content.find("\"difficulty\"")
        diff = int(html_content[pos + 13])

        soup = BeautifulSoup(html_content, "lxml")  # 使用 lxml 解析器
        target_div = soup.find_all("title")[0]
        # print(target_div.text)

        ans='"id":"'+pid+'","title":"'+target_div.text+'","diff":'+str(diff)
        for i in [1,2,3,4,5]:
            res = line[i-1].rstrip()
            res = res.replace('\\', '\\\\')
            res = res.replace('"', '\\"')
            ans+=',"hint'+str(i)+'":"'+res+'"';

        return ans

for i in range(13000,14000):
    file_path = Path(hint_path+"P"+str(i)+".txt")
    if not file_path.exists():continue

    # if ans_text!="": ans_text+=",\n"
    ans='{'+get_statement('P'+str(i))+'},\n';
    with open('out13.txt', 'a', encoding='utf-8') as f:
        f.write(ans)

# ans_text='[\n'+ans_text+'\n]'
#
# with open("out.txt", "w", encoding="utf-8") as f:
#     f.write(ans_text)

# {
#     "id": "P1039",
#     "title": "P1039 [NOIP 2003 提高组] 侦探推理",
#     "diff": 5,
#     "hint1": "题目中每个人要么总说真话，要么总说假话。这意味着每一个证词都应该是真实的或虚假的。",
#     "hint2": "考虑如何通过枚举罪犯的身份和日期来验证每一种可能性是否符合题设条件。",
#     "hint3": "需要分析每一个证词的真实性以确定假设条件下说话人的身份（真实或谎言者）。",
#     "hint4": "对于每个可能的罪犯，计算说谎者的数量，并确保它等于给定值n。如果找到合适的组合，则记录下来。",
#     "hint5": "枚举结束后，根据记录的信息输出结果，注意处理无法唯一确定的情况。"
# }