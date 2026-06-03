"""AUTO-EVO-AI 建筑膜 PPT — 5页架构演示"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# ——— 调色板 ———
BG_DARK = RGBColor(0x1E, 0x27, 0x61)   # 深海蓝
BG_CARD = RGBColor(0xCA, 0xDC, 0xFC)   # 冰蓝
ACCENT = RGBColor(0x02, 0x80, 0x90)    # 青绿
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF2, 0xF2, 0xF2)
DARK_TEXT = RGBColor(0x1A, 0x1A, 0x2E)
MUTED = RGBColor(0x88, 0x92, 0xB0)

def add_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_shape(slide, left, top, w, h, color, alpha=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape

def add_text_box(slide, left, top, w, h, text, font_size=14, bold=False, color=DARK_TEXT, align=PP_ALIGN.LEFT):
    txBox = slide.shapes.add_textbox(left, top, w, h)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = align
    return txBox

# ────── Page 1: 封面 ──────
slide1 = prs.slides.add_slide(prs.slide_layouts[6])  # blank
add_bg(slide1, BG_DARK)

# 蓝色渐变条
bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(3.2), Inches(13.333), Inches(1.6))
bar.fill.solid()
bar.fill.fore_color.rgb = ACCENT
bar.line.fill.background()

add_text_box(slide1, Inches(1), Inches(1.5), Inches(11), Inches(1.2),
             "AUTO-EVO-AI V0.1", 48, True, WHITE, PP_ALIGN.CENTER)
add_text_box(slide1, Inches(1), Inches(2.8), Inches(11), Inches(0.6),
             "Enterprise AI Automation Platform", 20, False, LIGHT, PP_ALIGN.CENTER)
add_text_box(slide1, Inches(1), Inches(3.8), Inches(11), Inches(0.6),
             "457 Modules · 57 Tools · 100 Industries · AI Agent Teams · 9 Languages", 18, False, WHITE, PP_ALIGN.CENTER)
add_text_box(slide1, Inches(4), Inches(5.5), Inches(5), Inches(0.5),
             "Architecture Overview — June 2026", 14, False, MUTED, PP_ALIGN.CENTER)

# ────── Page 2: 系统架构总览 ──────
slide2 = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide2, WHITE)

add_text_box(slide2, Inches(0.8), Inches(0.4), Inches(10), Inches(0.7),
             "System Architecture Overview", 36, True, BG_DARK)

# 4 层架构卡片
layers = [
    ("🎨  Frontend Layer", "Vue3 + Naive UI\nChat.html (SPA)\ni18n (9 languages)\nAgent Team UI", ACCENT),
    ("⚙️  API Layer", "FastAPI + Uvicorn\nREST · WebSocket\nLLM Gateway (13 providers)\nCLI Interface", RGBColor(0x02, 0x80, 0x90)),
    ("🧠  Engine Layer", "Scheduler · Pipeline\nAgent Orchestrator\nEvent Engine\nFileOps · Alert", RGBColor(0x06, 0x5A, 0x82)),
    ("📦  Tool Layer", "57 Docker Tools\n100 Industry Configs\nAgent-S Desktop\nGitea · Metabase · More", RGBColor(0x21, 0x29, 0x5C)),
]
for i, (title, desc, clr) in enumerate(layers):
    x = Inches(0.8 + i * 3.1)
    y = Inches(1.7)
    card = add_shape(slide2, x, y, Inches(2.8), Inches(4.8), clr)
    add_text_box(slide2, x + Inches(0.2), y + Inches(0.3), Inches(2.4), Inches(0.5),
                 title, 18, True, WHITE, PP_ALIGN.CENTER)
    add_text_box(slide2, x + Inches(0.2), y + Inches(1.0), Inches(2.4), Inches(3.5),
                 desc, 14, False, LIGHT, PP_ALIGN.CENTER)

# ────── Page 3: 核心能力 ──────
slide3 = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide3, BG_DARK)

add_text_box(slide3, Inches(0.8), Inches(0.4), Inches(10), Inches(0.7),
             "Core Capabilities", 36, True, WHITE)

caps = [
    ("🤖  Multi-Agent\n    Collaboration", "6 AI agents (Athena, Hermes,\nApollo...) discuss complex tasks\nand produce reports"),
    ("🔗  LLM Integration", "13 major providers:\nOpenAI · Anthropic · DeepSeek\nQwen · GLM · Kimi · Ollama · more"),
    ("🖥️  Desktop\n    Automation", "Agent-S bridge for\nmouse/keyboard/screenshot\ncontrol of any application"),
    ("📁  File & Email\n    Operations", "Generate Word, edit Excel,\nsend email, all programmatically"),
]
for i, (title, desc) in enumerate(caps):
    x = Inches(0.6 + i * 3.2)
    y = Inches(1.6)
    card = add_shape(slide3, x, y, Inches(2.9), Inches(4.7), ACCENT if i % 2 == 0 else RGBColor(0x1C, 0x72, 0x93))
    add_text_box(slide3, x + Inches(0.2), y + Inches(0.3), Inches(2.5), Inches(0.8),
                 title, 20, True, WHITE, PP_ALIGN.CENTER)
    add_text_box(slide3, x + Inches(0.2), y + Inches(1.3), Inches(2.5), Inches(3.0),
                 desc, 14, False, LIGHT, PP_ALIGN.CENTER)

# ────── Page 4: 多智能体协作 ──────
slide4 = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide4, LIGHT)

add_text_box(slide4, Inches(0.8), Inches(0.4), Inches(10), Inches(0.7),
             "Multi-Agent Team Collaboration", 36, True, BG_DARK)

# 智能体卡片
agents = [
    ("🦉  Athena", "Project Manager\nTask assignment\nResult aggregation"),
    ("⚡  Hermes", "Information Collector\nData query\nWeb search"),
    ("🔮  Apollo", "Analyst\nData analysis\nInsight generation"),
    ("🛡️  Hecate", "Security Auditor\nCompliance check\nRisk assessment"),
    ("🔬  Minerva", "Researcher\nDeep research\nTech proposals"),
    ("⚙️  Phoebus", "Executor\nCode execution\nTask operation"),
]
for i, (name, desc) in enumerate(agents):
    col = i % 3
    row = i // 3
    x = Inches(0.8 + col * 4.0)
    y = Inches(1.6 + row * 2.7)
    card = add_shape(slide4, x, y, Inches(3.6), Inches(2.3), WHITE)
    add_text_box(slide4, x + Inches(0.2), y + Inches(0.3), Inches(3.2), Inches(0.5),
                 name, 18, True, BG_DARK, PP_ALIGN.CENTER)
    add_text_box(slide4, x + Inches(0.2), y + Inches(0.9), Inches(3.2), Inches(1.2),
                 desc, 13, False, MUTED, PP_ALIGN.CENTER)

# ────── Page 5: 行业方案 & 部署 ──────
slide5 = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide5, WHITE)

add_text_box(slide5, Inches(0.8), Inches(0.4), Inches(10), Inches(0.7),
             "Industry Solutions & Deployment", 36, True, BG_DARK)

# 左侧：100行业
add_shape(slide5, Inches(0.5), Inches(1.5), Inches(6.0), Inches(5.0), RGBColor(0x02, 0x80, 0x90))
add_text_box(slide5, Inches(0.8), Inches(1.7), Inches(5.5), Inches(0.5),
             "🏭  100 Industry Templates", 22, True, WHITE)
add_text_box(slide5, Inches(0.8), Inches(2.4), Inches(5.5), Inches(3.8),
             "Manufacturing · Retail · Finance · Healthcare\n"
             "Education · HR · Enterprise · IT · Legal\n"
             "Media · Agriculture · Construction · Energy\n"
             "Transportation · Insurance · Telecom · Auto\n"
             "Food · Sports · Entertainment · Publishing\n"
             "R&D · Environmental · Security · Beauty\n"
             "Cross-border E-commerce · And 73 more...",
             14, False, LIGHT)

# 右侧：部署方式
add_shape(slide5, Inches(6.8), Inches(1.5), Inches(6.0), Inches(5.0), BG_DARK)
add_text_box(slide5, Inches(7.1), Inches(1.7), Inches(5.5), Inches(0.5),
             "🚀  One-Click Deployment", 22, True, WHITE)
add_text_box(slide5, Inches(7.1), Inches(2.4), Inches(5.5), Inches(3.8),
             "•  deploy-industry.bat — pick #1-100\n"
             "•  Docker auto-launch for all tools\n"
             "•  CLI: python cli.py industry 5\n"
             "•  Web: localhost:8765/app\n\n"
             "Supported: 57 Docker services\n"
             "Auto-startup on boot (VBS)\n"
             "GitHub: haijunwu007007/my-evo-ai",
             14, False, LIGHT)

# 底部
add_text_box(slide5, Inches(4), Inches(6.8), Inches(5), Inches(0.5),
             "AUTO-EVO-AI V0.1 | June 2026", 12, False, MUTED, PP_ALIGN.CENTER)

# 保存
path = r"D:\AUTO-EVO-AI-V0.1\AUTO-EVO-AI-Architecture.pptx"
prs.save(path)
print(f"PPT saved: {path}")
