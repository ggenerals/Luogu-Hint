// Hint-Luogu 前端脚本

let allProblems = [];
let filteredProblems = [];

// 难度文本映射
const difficultyText = {
    0: '未评定',
    1: '入门',
    2: '普及-',
    3: '普及/提高-',
    4: '提高+/省选-',
    5: '省选/NOI-',
    6: 'NOI/NOI+',
    7: 'NOI+'
};

// 加载数据
async function loadData() {
    try {
        const response = await fetch('data.json');
        const data = await response.json();
        
        allProblems = data.problems || [];
        updateStats(data);
        displayResults(allProblems);
        
        console.log(`成功加载 ${allProblems.length} 道题目`);
    } catch (error) {
        console.error('加载数据失败:', error);
        document.getElementById('results').innerHTML = `
            <div class="no-results">
                <p>数据加载失败，请确保 data.json 文件存在</p>
            </div>
        `;
    }
}

// 更新统计信息
function updateStats(data) {
    const statsDiv = document.getElementById('stats');
    const problemCount = data.problems ? data.problems.length : 0;
    const version = data.version || 1;
    const generatedAt = data.generated_at ? new Date(data.generated_at).toLocaleDateString('zh-CN') : '未知';
    
    statsDiv.innerHTML = `
        共收录 <strong>${problemCount}</strong> 道题目 | 
        数据版本：v${version} | 
        最后更新：${generatedAt}
    `;
}

// 显示结果
function displayResults(problems) {
    const resultsDiv = document.getElementById('results');
    
    if (problems.length === 0) {
        resultsDiv.innerHTML = `
            <div class="no-results">
                <p>没有找到匹配的题目</p>
            </div>
        `;
        return;
    }
    
    // 限制显示数量（默认显示前 50 个）
    const displayLimit = 50;
    const displayedProblems = problems.slice(0, displayLimit);
    
    let html = '';
    for (const problem of displayedProblems) {
        html += createProblemCard(problem);
    }
    
    if (problems.length > displayLimit) {
        html += `
            <div class="no-results">
                <p>还有 ${problems.length - displayLimit} 道题目，请缩小搜索范围</p>
            </div>
        `;
    }
    
    resultsDiv.innerHTML = html;
    
    // 绑定提示展开/折叠事件
    bindHintToggleEvents();
}

// 创建题目卡片
function createProblemCard(problem) {
    const difficultyClass = `difficulty-${problem.difficulty || 0}`;
    const difficultyLabel = difficultyText[problem.difficulty] || '未评定';
    
    let hintsHtml = '';
    if (problem.hints && problem.hints.length > 0) {
        for (const hint of problem.hints) {
            hintsHtml += `
                <li class="hint-item">
                    <div class="hint-level">💡 提示 ${hint.level}</div>
                    <div class="hint-content">${escapeHtml(hint.content)}</div>
                </li>
            `;
        }
    } else {
        hintsHtml = '<li class="hint-item"><div class="hint-content">暂无提示</div></li>';
    }
    
    return `
        <div class="problem-card" data-id="${problem.id}">
            <div class="problem-header">
                <div>
                    <span class="problem-title">${escapeHtml(problem.title)}</span>
                    <span class="difficulty ${difficultyClass}">${difficultyLabel}</span>
                </div>
                <span class="problem-id">${problem.id}</span>
            </div>
            <div class="hints-section">
                <button class="hint-toggle">查看提示</button>
                <ul class="hints-list">
                    ${hintsHtml}
                </ul>
            </div>
        </div>
    `;
}

// 转义 HTML 防止 XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 绑定提示展开/折叠事件
function bindHintToggleEvents() {
    const toggles = document.querySelectorAll('.hint-toggle');
    toggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const hintsList = toggle.nextElementSibling;
            const isShown = hintsList.classList.contains('show');
            
            // 切换当前状态
            toggle.classList.toggle('active', !isShown);
            hintsList.classList.toggle('show', !isShown);
            
            // 更新按钮文本
            toggle.textContent = isShown ? '查看提示' : '收起提示';
        });
    });
}

// 搜索功能
function search(query) {
    query = query.trim().toLowerCase();
    
    if (!query) {
        filteredProblems = allProblems;
    } else {
        filteredProblems = allProblems.filter(problem => {
            // 支持题号搜索（如 P1000）
            if (problem.id.toLowerCase().includes(query)) {
                return true;
            }
            // 支持题目名称搜索
            if (problem.title.toLowerCase().includes(query)) {
                return true;
            }
            return false;
        });
    }
    
    displayResults(filteredProblems);
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    
    // 点击搜索按钮
    searchBtn.addEventListener('click', () => {
        search(searchInput.value);
    });
    
    // 回车搜索
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            search(searchInput.value);
        }
    });
    
    // 实时搜索（可选）
    searchInput.addEventListener('input', () => {
        // 延迟搜索，避免频繁触发
        clearTimeout(window.searchTimeout);
        window.searchTimeout = setTimeout(() => {
            search(searchInput.value);
        }, 300);
    });
});
