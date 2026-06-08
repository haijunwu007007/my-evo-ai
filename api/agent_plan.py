"""智能体 — Markdown规划文件（Manus风格任务分解）"""
import os, json, time, re
from pathlib import Path

class MarkdownPlan:
    """基于Markdown文件的任务规划（planning-with-files风格）"""
    def __init__(self, BASE):
        self.plans_dir = BASE / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)

    def create_plan(self, title, steps=None, description=""):
        """创建规划文件"""
        safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', title[:20]).strip('_')
        now = time.strftime("%Y-%m-%d %H:%M")
        plan = f"""# 规划: {title}

> 创建时间: {now}
> 状态: 📋 待执行

## 目标
{title}
{description}

## 执行步骤

"""
        if steps:
            for i, s in enumerate(steps, 1):
                name = s.get('name', '未命名') if isinstance(s, dict) else str(s)
                plan += f"### 步骤 {i}: {name}\n"
                plan += f"- 动作: {s.get('action', '待定') if isinstance(s, dict) else '待定'}\n"
                plan += f"- 预期结果: {s.get('expected', '待定') if isinstance(s, dict) else '待定'}\n"
                plan += f"- 状态: ⏳ 待执行\n\n"
        else:
            plan += "### 步骤 1: 分析需求\n- 动作: 调用LLM分析\n- 状态: ⏳ 待执行\n\n"
            plan += "### 步骤 2: 生成代码\n- 动作: file_write\n- 状态: ⏳ 待执行\n\n"
            plan += "### 步骤 3: 审查结果\n- 动作: 代码审查\n- 状态: ⏳ 待执行\n\n"
        
        fp = self.plans_dir / f"{safe_name}.md"
        fp.write_text(plan, encoding='utf-8')
        return {"path": str(fp), "title": title, "steps": len(steps) if steps else 3}

    def load_plan(self, name):
        """加载规划文件"""
        fp = self.plans_dir / f"{name}.md" if not name.endswith('.md') else Path(name)
        if fp.exists():
            return fp.read_text(encoding='utf-8')
        # 搜索
        for f in self.plans_dir.glob("*.md"):
            if name in f.stem:
                return f.read_text(encoding='utf-8')
        return None

    def update_step(self, plan_name, step_num, status, note=""):
        """更新执行步骤状态"""
        content = self.load_plan(plan_name)
        if not content: return False
        old = f"### 步骤 {step_num}:"
        new_status = {"⏳":"待执行","🔄":"执行中","✅":"已完成","❌":"失败","⏸":"暂停"}
        icon = {k:v for v,k in new_status.items()}.get(status, "⏳")
        lines = content.split('\n')
        updated = []
        in_step = False; step_found = False
        for line in lines:
            if line.startswith(f"### 步骤 {step_num}:"):
                in_step = True; step_found = True
            elif line.startswith("### 步骤 ") and in_step:
                in_step = False
            if in_step and line.startswith("- 状态:"):
                line = f"- 状态: {icon} {status}"
                if note: line += f" ({note})"
            updated.append(line)
        
        if step_found:
            fp = self.plans_dir / f"{plan_name}.md" if not plan_name.endswith('.md') else Path(plan_name)
            fp.write_text('\n'.join(updated), encoding='utf-8')
            return True
        return False

    def save_plan(self, plan_data):
        """保存规划数据（兼容接口）"""
        if isinstance(plan_data, dict):
            title = plan_data.get("title", "未命名")
            steps = plan_data.get("steps", [])
            if isinstance(steps, int):
                # 从create_plan返回的是步骤数量
                steps = [{"name": f"步骤{i}", "action": "待定"} for i in range(1, steps + 1)]
            return self.create_plan(title, steps)
        return str(self.plans_dir / "plan.md")

    def list_plans(self):
        """列出所有规划"""
        plans = []
        for f in sorted(self.plans_dir.glob("*.md"), reverse=True):
            plans.append({"name": f.stem, "path": str(f), "size": f.stat().st_size})
        return plans

def create_plan_from_msg(msg, BASE):
    """从用户消息自动创建规划"""
    plan = MarkdownPlan(BASE)
    safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', msg[:20]).strip('_')
    steps = [
        {"name": "需求分析", "action": "LLM分析", "expected": "结构化需求文档"},
        {"name": "架构设计", "action": "LLM规划", "expected": "技术方案"},
        {"name": "代码实现", "action": "file_write/execute_module", "expected": "可运行代码"},
        {"name": "审查迭代", "action": "代码审查", "expected": "达标通过"},
    ]
    return plan.create_plan(msg[:50], steps)
