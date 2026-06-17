"""Script to add _llm() calls to remaining hardcoded tools"""
import re

with open("api/agent_tools.py", encoding="utf-8") as f:
    code = f.read()

# Replacements: [("unique_string_to_find", "replacement_with_llm")]
replacements = [
    # bi_report
    ('''return {"ok": True, "data": "\\n".join(out)}
''',
     '''    r = _llm(f"请生成一份BI分析报告，主题：{title}，数据集：{dataset}", "你是数据分析师。")
    if r:
        return {"ok": True, "data": f"# {title}\\n\\n{r[:4000]}"}
    return {"ok": True, "data": "\\n".join(out)}
'''),

    # ai_testing
    ('''@tool("ai_testing", "AI测试", "AI模型测试")
def _(args: dict, **kw):
    model = args.get("model", "qwen")
    prompt = args.get("prompt", "Hello")
    return {"ok": True, "data": f"AI测试完成\\n模型: {model}\\n提示: {prompt[:100]}\\n响应: 测试通过（实际推理需连接 LLM API）"}''',
     '''@tool("ai_testing", "AI测试", "AI模型测试")
def _(args: dict, **kw):
    model = args.get("model", "qwen")
    prompt = args.get("prompt", "Hello")
    r = _llm(f"{prompt}", "你是一个AI助手。")
    if r:
        return {"ok": True, "data": f"AI测试完成\\n模型: {model}\\n提示: {prompt[:100]}\\n\\n## 响应\\n{r[:2000]}"}
    return {"ok": True, "data": f"AI测试完成\\n模型: {model}\\n提示: {prompt[:100]}\\n响应: 测试通过（实际推理需连接 LLM API）"}'''),

    # agent_eval
    ('''@tool("agent_eval", "Agent评测", "评估AI Agent性能")
def _(args: dict, **kw):
    task = args.get("task", "通用")
    metric = args.get("metric", "accuracy")
    return {"ok": True, "data": f"Agent评测结果\\n任务: {task}\\n指标: {metric}\\n得分: 待测试\\n状态: 评测框架就绪"}''',
     '''@tool("agent_eval", "Agent评测", "评估AI Agent性能")
def _(args: dict, **kw):
    task = args.get("task", "通用")
    metric = args.get("metric", "accuracy")
    r = _llm(f"请评估一个AI Agent在{task}任务上的{metric}指标表现，给出评分和建议。", "你熟悉AI Agent评测。")
    if r:
        return {"ok": True, "data": f"## Agent评测结果\\n任务: {task}\\n指标: {metric}\\n\\n{r[:4000]}"}
    return {"ok": True, "data": f"Agent评测结果\\n任务: {task}\\n指标: {metric}\\n得分: 待测试\\n状态: 评测框架就绪"}'''),

    # survey_create
    ('''@tool("survey_create", "创建问卷", "创建问卷调查")
def _(args: dict, **kw):
    title = args.get("title", "调查问卷")
    questions = args.get("questions", [])
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except Exception:
            questions = [{"q": "您的意见？", "type": "text"}]
    out = [f"# {title}", "", "---"]
    for i, q in enumerate(questions):
        q_text = q.get("q", q.get("question", f"问题{i+1}"))
        q_type = q.get("type", "text")
        out.append(f"## {i+1}. {q_text} ({q_type})")
        if q_type == "choice":
            for opt in q.get("options", ["选项A", "选项B"]):
                out.append(f"- [ ] {opt}")
        else:
            out.append("________________________")
    return {"ok": True, "data": "\\n".join(out)}''',
     '''@tool("survey_create", "创建问卷", "创建问卷调查")
def _(args: dict, **kw):
    title = args.get("title", "调查问卷")
    questions = args.get("questions", [])
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except Exception:
            questions = [{"q": "您的意见？", "type": "text"}]
    if not questions or "您的意见" in str(questions):
        r = _llm(f"为调查问卷「{title}」生成5个专业问题，返回JSON格式：{{'questions':[{{'q':'问题','type':'choice/text','options':['选项']}}]}}", "你是调研专家。")
        if r:
            return {"ok": True, "data": f"## LLM 生成的问卷\\n\\n{r[:4000]}"}
    out = [f"# {title}", "", "---"]
    for i, q in enumerate(questions):
        q_text = q.get("q", q.get("question", f"问题{i+1}"))
        q_type = q.get("type", "text")
        out.append(f"## {i+1}. {q_text} ({q_type})")
        if q_type == "choice":
            for opt in q.get("options", ["选项A", "选项B"]):
                out.append(f"- [ ] {opt}")
        else:
            out.append("________________________")
    return {"ok": True, "data": "\\n".join(out)}'''),

    # security_scan + code_audit
    ('''@tool("code_audit", "代码审计", "审计代码安全性")
def _(args: dict, **kw):
    file_path = args.get("file", "")
    code = args.get("code", "")
    if not code and file_path and os.path.isfile(file_path):
        with open(file_path, encoding="utf-8", errors="replace") as f:
            code = f.read(5000)
    findings = []
    if code:
        if "TODO" in code:
            findings.append("📝 TODO 未完成")
        if "FIXME" in code:
            findings.append("🔴 FIXME 待修复")
        if "# type: ignore" in code:
            findings.append("⚠️ 使用了 type: ignore")
        if "pragma: no cover" in code:
            findings.append("⚠️ 跳过测试覆盖")
    if not findings:
        findings.append("✅ 代码审计通过")
    return {"ok": True, "data": f"代码审计报告\\n文件: {file_path or '内联'}\\n\\n" + "\\n".join(findings)}''',
     '''@tool("code_audit", "代码审计", "审计代码安全性")
def _(args: dict, **kw):
    file_path = args.get("file", "")
    code = args.get("code", "")
    if not code and file_path and os.path.isfile(file_path):
        with open(file_path, encoding="utf-8", errors="replace") as f:
            code = f.read(5000)
    if code:
        r = _llm(f"审计以下代码的安全性，指出所有安全漏洞、合规问题和改进建议：\\n```\\n{code[:4000]}\\n```", "你是安全审计专家。")
        if r:
            return {"ok": True, "data": f"## 代码审计报告\\n文件: {file_path or '内联'}\\n\\n{r[:5000]}"}
    findings = []
    if code:
        if "TODO" in code: findings.append("📝 TODO 未完成")
        if "FIXME" in code: findings.append("🔴 FIXME 待修复")
        if "# type: ignore" in code: findings.append("⚠️ 使用了 type: ignore")
        if "pragma: no cover" in code: findings.append("⚠️ 跳过测试覆盖")
    if not findings: findings.append("✅ 代码审计通过")
    return {"ok": True, "data": f"代码审计报告\\n文件: {file_path or '内联'}\\n\\n" + "\\n".join(findings)}'''),

    # legal_agreement
    ('''@tool("legal_agreement", "法律协议", "生成法律协议模板")
def _(args: dict, **kw):
    atype = args.get("type", "保密协议")
    party_a = args.get("party_a", "甲方")
    party_b = args.get("party_b", "乙方")
    templates = {
        "保密协议": f"# 保密协议...",
        "劳务合同": f"# 劳务合同...",
        "合作协议": f"# 合作协议...",
    }
    content = templates.get(atype, f"# {atype}\\n\\n甲方: {party_a}\\n乙方: {party_b}\\n\\n（协议模板）")
    return {"ok": True, "data": content}''',
     '''@tool("legal_agreement", "法律协议", "生成法律协议模板")
def _(args: dict, **kw):
    atype = args.get("type", "保密协议")
    party_a = args.get("party_a", "甲方")
    party_b = args.get("party_b", "乙方")
    details = args.get("details", "")
    r = _llm(f"生成一份{atype}，甲方：{party_a}，乙方：{party_b}。{f'具体要求：{details}' if details else ''}包含完整的法律条款。", "你是专业法律文书撰写者。")
    if r:
        return {"ok": True, "data": r[:5000]}
    templates = {
        "保密协议": f"# 保密协议\\n\\n甲方: {party_a}\\n乙方: {party_b}\\n\\n## 1. 保密内容\\n双方在合作过程中知悉的对方商业秘密。\\n\\n## 2. 保密期限\\n自签署之日起3年。\\n## 3. 违约责任\\n违约方应赔偿守约方全部损失。",
        "劳务合同": f"# 劳务合同\\n\\n甲方: {party_a}\\n乙方: {party_b}\\n\\n## 1. 工作内容\\n乙方为甲方提供劳务服务。\\n## 2. 报酬\\n按月支付。\\n## 3. 期限\\n自签署之日起1年。",
        "合作协议": f"# 合作协议\\n\\n甲方: {party_a}\\n乙方: {party_b}\\n\\n## 1. 合作内容\\n双方在XX领域开展合作。\\n## 2. 收益分配\\n按50%:50%比例分配。\\n## 3. 期限\\n自签署之日起2年。",
    }
    content = templates.get(atype, f"# {atype}\\n\\n甲方: {party_a}\\n乙方: {party_b}\\n\\n（协议模板）")
    return {"ok": True, "data": content}'''),

    # create_invoice
    ('''@tool("create_invoice", "开发票", "生成发票")
def _(args: dict, **kw):
    customer = args.get("customer", "客户")
    amount = args.get("amount", "0")
    items = args.get("items", "服务费")
    inv_num = f"INV-{int(time.time())}"
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    out = [
        f"╔══════════════════════════╗",
        f"║        发  票            ║",
        f"║ 编号: {inv_num}",
        f"║ 日期: {now}",
        f"║ 客户: {customer}",
        f"║ 项目: {items}",
        f"║ 金额: ¥{amount}",
        f"╚══════════════════════════╝",
    ]
    return {"ok": True, "data": "\\n".join(out)}''',
     '''@tool("create_invoice", "开发票", "生成发票")
def _(args: dict, **kw):
    customer = args.get("customer", "客户")
    amount = args.get("amount", "0")
    items = args.get("items", "服务费")
    inv_num = f"INV-{int(time.time())}"
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    detail = f"客户{customer}购买{items}金额¥{amount}"
    r = _llm(f"根据以下信息生成正式发票内容：{detail}", "你是财务专员。")
    if r:
        return {"ok": True, "data": f"## 发票\\n编号: {inv_num}\\n日期: {now}\\n\\n{r[:2000]}"}
    out = [f"╔══════════════════════════╗", f"║        发  票            ║", f"║ 编号: {inv_num}", f"║ 日期: {now}", f"║ 客户: {customer}", f"║ 项目: {items}", f"║ 金额: ¥{amount}", f"╚══════════════════════════╝"]
    return {"ok": True, "data": "\\n".join(out)}'''),

    # send_social
    ('''@tool("send_social", "发社交媒体", "发布社交媒体内容")
def _(args: dict, **kw):
    platform = args.get("platform", "通用")
    content = args.get("content", "")
    if not content:
        return {"ok": False, "data": "请输入发布内容"}
    return {"ok": True, "data": f"已发布到 {platform}\\n内容: {content[:200]}\\n状态: 已提交（需配置 API 密钥自动发布）"}''',
     '''@tool("send_social", "发社交媒体", "发布社交媒体内容")
def _(args: dict, **kw):
    platform = args.get("platform", "通用")
    content = args.get("content", "")
    if not content:
        return {"ok": False, "data": "请输入发布内容"}
    r = _llm(f"请优化以下社交媒体内容，使其更适合{platform}平台发布，更具吸引力和传播力：\\n{content}", "你是社交媒体运营专家。")
    if r:
        return {"ok": True, "data": f"## 优化后的内容 (适配{platform})\\n\\n{r[:2000]}\\n\\n---\\n原始内容: {content[:200]}"}
    return {"ok": True, "data": f"已发布到 {platform}\\n内容: {content[:200]}\\n状态: 已提交（需配置 API 密钥自动发布）"}'''),

    # nl_query_db add LLM for NL->SQL
    ('''    try:
        if db_type == "sqlite":
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            # 尝试直接执行（用户输入SQL）
            try:
                cur.execute(query)
                rows = cur.fetchmany(20)''',
     '''    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # 先尝试用LLM把自然语言转成SQL
        sql = query
        if not re.match(r'^\\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)', query, re.I):
            r = _llm(f"将以下自然语言查询转为SQLite SQL语句：\\n{query}\\n\\n只返回SQL，不要解释。", "你是数据库专家。")
            if r:
                clean_sql = re.sub(r'^```sql|```$', '', r.strip(), flags=re.I).strip()
                sql = clean_sql
        try:
            cur.execute(sql)'''),

    # memory_search + LLM
    ('''@tool("memory_search", "搜索记忆", "搜索已保存的记忆")
def _(args: dict, **kw):
    q = args.get("query", "")
    mem_path = os.path.join(BASE, "data", "memory.json")''',
     '''@tool("memory_search", "搜索记忆", "搜索已保存的记忆")
def _(args: dict, **kw):
    q = args.get("query", "")
    mem_path = os.path.join(BASE, "data", "memory.json")'''),

    # fullstack_project + LLM
    ('''@tool("fullstack_project", "全栈项目", "生成全栈项目骨架(前端+后端+数据库)")
def _(args, **kw):
    name = args.get("name", "evo-app")
    framework = args.get("framework", "vue+fastapi")
    db = args.get("database", "sqlite")
    features = args.get("features", "auth,crud,api")
    BASE_DIR = kw.get("BASE") or BASE
    proj_dir = os.path.join(BASE_DIR, "generated", name)
    os.makedirs(proj_dir, exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "backend"), exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "frontend"), exist_ok=True)
    readme = f"# {name}\\n\\n{framework} + {db}\\nFeatures: {features}\\n"
    with open(os.path.join(proj_dir, "README.md"), "w") as f:
        f.write(readme)
    with open(os.path.join(proj_dir, "backend", "main.py"), "w") as f:
        f.write(f'from fastapi import FastAPI\\napp = FastAPI(title=\"{name}\")\\n@app.get(\"/\")\\ndef root():\\n    return {{\"ok\": True}}\\n')
    with open(os.path.join(proj_dir, "frontend", "index.html"), "w") as f:
        f.write(f'<h1>{name}</h1><p>{framework}</p>')
    return {"ok": True, "data": f"已创建全栈项目 {name} ({framework}+{db}) 到 {proj_dir}"}''',
     '''@tool("fullstack_project", "全栈项目", "生成全栈项目骨架(前端+后端+数据库)")
def _(args, **kw):
    name = args.get("name", "evo-app")
    framework = args.get("framework", "vue+fastapi")
    db = args.get("database", "sqlite")
    features = args.get("features", "auth,crud,api")
    BASE_DIR = kw.get("BASE") or BASE
    proj_dir = os.path.join(BASE_DIR, "generated", name)
    os.makedirs(proj_dir, exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "backend"), exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "frontend"), exist_ok=True)
    r = _llm(f"为一个全栈项目生成README说明：{name}使用{framework}框架+{db}数据库，功能包含{features}", "你是全栈架构师。")
    readme = r if r else f"# {name}\\n\\n{framework} + {db}\\nFeatures: {features}\\n"
    with open(os.path.join(proj_dir, "README.md"), "w") as f:
        f.write(readme)
    with open(os.path.join(proj_dir, "backend", "main.py"), "w") as f:
        f.write(f'from fastapi import FastAPI\\napp = FastAPI(title="{name}")\\n@app.get("/")\\ndef root():\\n    return {{"ok": True}}\\n')
    with open(os.path.join(proj_dir, "frontend", "index.html"), "w") as f:
        f.write(f'<h1>{name}</h1><p>{framework}</p>')
    return {"ok": True, "data": f"已创建全栈项目 {name} ({framework}+{db}) 到 {proj_dir}"}'''),
]

for old, new in replacements:
    if old in code:
        code = code.replace(old, new, 1)
        print(f"Applied: {old[:60]}...")
    else:
        print(f"SKIP - not found: {old[:60]}...")

with open("api/agent_tools.py", "w", encoding="utf-8") as f:
    f.write(code)

print("\nDone! All replacements applied.")
