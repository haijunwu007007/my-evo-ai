"""
AUTO-EVO-AI V0.1 — Excel智能分析
上传CSV/Excel → AI自动分析趋势 → 生成可视化报告
"""
from fastapi import APIRouter, UploadFile, File, Form
import os, json, csv, io, uuid, re
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.api.data_analyzer")
router = APIRouter(prefix="/api/v1/data-analyzer", tags=["data_analyzer"])

BASE = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE / "output" / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/analyze")
async def analyze_data(file: UploadFile = File(...), question: str = Form("")):
    """上传Excel/CSV → 自动分析 → 返回可视化报告"""
    try:
        # 1. 读取文件
        content = await file.read()
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "csv"
        
        # 2. 解析数据
        data = _parse_data(content, ext)
        if not data or len(data) < 2:
            return {"success": False, "error": "数据为空或格式不正确"}
        
        headers = data[0]
        rows = data[1:]
        
        # 3. 统计分析
        stats = _analyze(headers, rows)
        
        # 4. LLM生成报告（降级模板）
        report = _generate_report(headers, rows, stats, question)
        
        # 5. 生成HTML报告
        report_id = uuid.uuid4().hex[:8]
        report_file = OUTPUT_DIR / f"report_{report_id}.html"
        
        html = _build_html(headers, rows, stats, report, file.filename)
        report_file.write_text(html, encoding="utf-8")
        
        return {
            "success": True,
            "filename": file.filename,
            "rows": len(rows),
            "cols": len(headers),
            "headers": headers[:10],
            "stats": stats,
            "report": report,
            "report_url": f"/output/reports/report_{report_id}.html",
            "preview": rows[:5],
        }
    except Exception as e:
        logger.error(f"[Data] analyze error: {e}")
        return {"success": False, "error": str(e)[:200]}

def _parse_data(content: bytes, ext: str) -> list:
    """解析CSV/Excel数据"""
    if ext in ("csv", "txt"):
        text = content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        return [row for row in reader if any(c.strip() for c in row)]
    elif ext in ("xlsx", "xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
            ws = wb.active
            data = []
            for row in ws.iter_rowd(values_only=True):
                data.append([str(c) if c is not None else "" for c in row])
            wb.close()
            return data
        except Exception:
            # 降级CSV读取
            return _parse_data(content, "csv")
    return []

def _analyze(headers: list, rows: list) -> dict:
    """统计分析"""
    numeric_cols = []
    text_cols = []
    for i, h in enumerate(headers):
        vals = [r[i] for r in rows if i < len(r) and r[i].strip()]
        nums = []
        for v in vals:
            try: nums.append(float(v.replace(",","").replace("¥","").replace("$","").replace("%","")))
            except: pass
        if len(nums) > len(vals) * 0.5:
            numeric_cols.append({"idx": i, "name": h, "values": nums})
        else:
            text_cols.append({"idx": i, "name": h})
    
    stats = {}
    for c in numeric_cols[:5]:
        v = c["values"]
        if v:
            stats[c["name"]] = {
                "avg": round(sum(v)/len(v), 2),
                "max": round(max(v), 2),
                "min": round(min(v), 2),
                "sum": round(sum(v), 2),
                "count": len(v),
                "trend": "上升" if len(v) > 1 and v[-1] > v[0] else "下降" if len(v) > 1 and v[-1] < v[0] else "平稳"
            }
    
    return {
        "numeric_cols": [c["name"] for c in numeric_cols[:5]],
        "text_cols": [c["name"] for c in text_cols[:5]],
        "total_rows": len(rows),
        "total_cols": len(headers),
        "column_stats": stats,
    }

def _generate_report(headers: list, rows: list, stats: dict, question: str) -> str:
    """AI生成报告（优先LLM，降级模板）"""
    try:
        from api.agent_llm import call_llm
        import threading, queue
        q = queue.Queue()
        def _do():
            try:
                summary = f"数据维度: {len(rows)}行x{len(headers)}列\n列名: {', '.join(headers[:8])}\n"
                if stats.get("column_stats"):
                    for k, v in stats["column_stats"].items():
                        summary += f"{k}: 平均{v['avg']}, 最大{v['max']}, 最小{v['min']}\n"
                text, _ = call_llm([
                    {"role": "system", "content": "你是数据分析师，用中文输出简明的数据分析报告。"},
                    {"role": "user", "content": f"分析以下数据并给出发现和建议：\n{summary}\n额外问题: {question}"}
                ], None, "")
                q.put(text or "")
            except: q.put("")
        t = threading.Thread(target=_do, daemon=True)
        t.start()
        t.join(timeout=15)
        if not t.is_alive() and not q.empty():
            result = q.get_nowait()
            if result: return result
    except: pass
    
    # 降级模板
    report = f"## 数据分析报告\n\n### 数据概览\n共 {len(rows)} 条记录，{len(headers)} 个字段。\n\n### 关键发现\n"
    for k, v in stats.get("column_stats", {}).items():
        report += f"- **{k}**: 平均{v['avg']}，最大{v['max']}，最小{v['min']}，趋势{v['trend']}\n"
    report += "\n### 建议\n- 建议定期监控数据变化\n- 关注异常值\n- 结合更多维度进行分析"
    return report

def _build_html(headers: list, rows: list, stats: dict, report: str, filename: str) -> str:
    """生成可视化报告 HTML"""
    # 构建图表数据
    chart_data = []
    for k, v in stats.get("column_stats", {}).items():
        chart_data.append(f"{{label:'{k}',avg:{v['avg']},max:{v['max']},min:{v['min']}}}")
    
    preview_rows = rows[:8]
    table_html = "<table><tr>" + "".join(f"<th>{h}</th>" for h in headers[:6]) + "</tr>"
    for row in preview_rows:
        table_html += "<tr>" + "".join(f"<td>{r[:30]}</td>" for r in row[:6]) + "</tr>"
    table_html += "</table>"
    
    return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>数据分析报告 - {filename}</title>
<link rel="stylesheet" href="/frontend/share.css">
<style>
body{{padding:24px;max-width:1000px;margin:0 auto}}
h1{{font-size:22px;margin-bottom:4px;display:flex;align-items:center;gap:8px}}
.sub{{color:var(--text2);font-size:14px;margin-bottom:20px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin-bottom:20px}}
.stat{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center}}
.stat .num{{font-size:20px;font-weight:700;color:var(--accent)}}
.stat .lb{{font-size:11px;color:var(--text2);margin-top:4px}}
.chart{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:20px;margin-bottom:16px;min-height:200px}}
.bar{{display:flex;align-items:flex-end;gap:12px;height:160px;padding:10px 0;justify-content:center}}
.bar-item{{display:flex;flex-direction:column;align-items:center;gap:4px;width:60px}}
.bar-fill{{width:40px;border-radius:4px 4px 0 0;min-height:10px;background:linear-gradient(to top,var(--accent),#7c3aed);transition:height .5s}}
.bar-label{{font-size:10px;color:var(--text2);text-align:center;max-width:60px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.report{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:20px;margin-bottom:16px;line-height:1.8;font-size:14px}}
.report h2{{font-size:16px;margin:12px 0 6px;color:var(--accent)}}
.report h3{{font-size:14px;margin:8px 0 4px}}
.report ul{{padding-left:18px}}
.report li{{margin:4px 0}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin:10px 0}}
th,td{{padding:6px 8px;text-align:left;border-bottom:1px solid var(--border);max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
th{{color:var(--text2);font-weight:600;font-size:11px}}
.preview{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:20px;margin-bottom:16px}}
.preview h3{{font-size:14px;margin-bottom:8px;color:var(--accent)}}
</style></head><body>
<h1>📊 数据分析报告</h1>
<p class="sub">{filename} · {stats.get('total_rows',0)}行 × {stats.get('total_cols',0)}列</p>

<div class="stats">
<div class="stat"><div class="num">{stats.get('total_rows',0)}</div><div class="lb">📦 数据行数</div></div>
<div class="stat"><div class="num">{stats.get('total_cols',0)}</div><div class="lb">📋 字段数</div></div>
<div class="stat"><div class="num">{len(stats.get('numeric_cols',[]))}</div><div class="lb">🔢 数值列</div></div>
</div>

<div class="chart">
<h3 style="font-size:14px;margin-bottom:10px;color:var(--text2)">📈 关键指标概况</h3>
<div class="bar" id="chartBars"></div>
</div>

<script>
var chartData = [{','.join(chart_data)}];
var h = '';
var maxVal = Math.max(...chartData.map(function(d){{return d.max}}), 1);
chartData.forEach(function(d){{
  var ht = Math.max(10, (d.avg/maxVal)*140);
  h += '<div class="bar-item"><div class="bar-fill" style="height:'+ht+'px" title="平均:'+d.avg+'"></div><div class="bar-label">'+d.label+'</div></div>';
}});
document.getElementById('chartBars').innerHTML = h;
</script>

<div class="report">
<h3>📝 AI 分析报告</h3>
{report.replace('<','&lt;').replace('>','&gt;').replace('\\n','<br>')}
</div>

<div class="preview">
<h3>👁️ 数据预览（前8行）</h3>
{table_html}
</div>
</body></html>"""
