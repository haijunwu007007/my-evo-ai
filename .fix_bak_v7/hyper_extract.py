"""
AUTO-EVO-AI V0.1 — Hyper-Extract 智能知识提取引擎
Grade: A (生产级) | Category: 数据处理
职责：从非结构化文档中提取结构化知识实体、关系、摘要
"""

__module_meta__ = {
    "id": "hyper-extract",
    "name": "Hyper Extract",
    "version": "V0.1",
    "group": "developer",
    "description": "从文档/文本中提取结构化知识 — 实体、关系、关键词、摘要、分类",
    "grade": "A",
}

import os
import re
import json
import time
import hashlib
import logging
from typing import Any, Optional
from datetime import datetime
from collections import Counter

logger = logging.getLogger("hyper_extract")

class ExtractionResult:
    def __init__(self, source: str, source_type: str = "text"):
        self.id = hashlib.md5(f"{source}:{time.time_ns()}".encode()).hexdigest()[:12]
        self.source = source[:1000]
        self.source_type = source_type
        self.entities = []
        self.relations = []
        self.keywords = []
        self.summary = ""
        self.category = ""
        self.confidence = 0.0
        self.timestamp = datetime.now().isoformat()

class HyperExtract:
    """超提取引擎 — 非结构化→结构化知识转换"""

    def __init__(self):
        self._history = []

    def extract_entities(self, text: str, entity_types: list = None) -> dict:
        """从文本中提取实体（人名、地名、组织、日期、金额、技术术语等）"""
        if entity_types is None:
            entity_types = ["person", "location", "organization", "date", "money", "tech", "product"]
        start = time.time()
        result = ExtractionResult(text[:500], "text")

        entities = []

        # 1. 人名提取（中文2-4字常见姓）
        person_pattern = re.findall(r'[李王张刘陈杨赵黄周吴徐孙马胡朱郭何罗高林][\u4e00-\u9fff]{1,3}(?:先生|女士|总|经理|老师|教授)?', text)
        for p in set(person_pattern):
            entities.append({"name": p, "type": "person", "method": "pattern", "count": person_pattern.count(p)})

        # 2. 金额提取
        money_pattern = re.findall(r'[¥￥$€]?\d+(?:,\d{3})*(?:\.\d+)?\s*(?:元|美元|欧元|港币|人民币|万|亿)?', text)
        for m in set(money_pattern):
            entities.append({"name": m.strip(), "type": "money", "method": "pattern"})

        # 3. 日期提取
        date_pattern = re.findall(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?|\d{1,2}月\d{1,2}[日号]?|今天|明天|昨天|下周|下月', text)
        for d in set(date_pattern):
            entities.append({"name": d, "type": "date", "method": "pattern"})

        # 4. 邮箱
        email_pattern = re.findall(r'[\w.-]+@[\w.-]+\.\w+', text)
        for e in set(email_pattern):
            entities.append({"name": e, "type": "email", "method": "pattern"})

        # 5. 网址
        url_pattern = re.findall(r'https?://[^\s，。、；）)]+', text)
        for u in set(url_pattern):
            entities.append({"name": u[:80], "type": "url", "method": "pattern"})

        # 6. 技术术语（驼峰/专业名词）
        tech_pattern = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', text)
        for t in set(tech_pattern):
            entities.append({"name": t, "type": "tech_term", "method": "pattern"})

        # 7. 中文组织名
        org_pattern = re.findall(r'(?:有限公司|集团|公司|局|部|委|院|所|中心|实验室(?:室)?|银行|保险|基金)[\u4e00-\u9fff]{0,10}', text)
        org_pattern += re.findall(r'[\u4e00-\u9fff]{2,10}(?:有限公司|集团|公司|局|部|委|院|所|中心|银行|保险)', text)
        for o in set(org_pattern):
            entities.append({"name": o, "type": "organization", "method": "pattern"})

        # 去重
        seen = set()
        deduped = []
        for e in entities:
            key = f"{e['name']}|{e['type']}"
            if key not in seen:
                seen.add(key)
                deduped.append(e)
            else:
                # 合并计数
                for de in deduped:
                    if de['name'] == e['name'] and de['type'] == e['type'] and 'count' in e:
                        de['count'] = de.get('count', 1) + e['count']

        # 按类型分组统计
        type_counts = Counter(e['type'] for e in deduped)

        elapsed = time.time() - start
        return {
            "success": True,
            "entities": deduped[:100],
            "total": len(deduped),
            "type_distribution": dict(type_counts.most_common()),
            "text_length": len(text),
            "elapsed_seconds": round(elapsed, 3),
        }

    def extract_keywords(self, text: str, top_n: int = 10) -> dict:
        """TF-IDF风格关键词提取"""
        start = time.time()
        # 中文分词（简单基于字频）
        words = []
        # 英文词
        en_words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        words.extend([w.lower() for w in en_words if w.lower() not in {
            'the','and','for','are','but','not','you','all','can','had','her','was',
            'one','our','out','has','have','been','some','them','than','that','this',
            'with','from','which','what','when','where','will','would','could','should',
            'also','its','their','they','about','into','over','after','before','just',
            'more','most','much','many','very','such','only','other','than','then'
        }])

        # 中文词（双字及以上）
        cn_chars = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
        words.extend(cn_chars)

        counter = Counter(words)
        keywords = [{"word": w, "count": c} for w, c in counter.most_common(top_n)]

        elapsed = time.time() - start
        return {
            "success": True,
            "keywords": keywords,
            "total_unique": len(counter),
            "total_words": len(words),
            "elapsed_seconds": round(elapsed, 3),
        }

    def extract_summary(self, text: str, max_sentences: int = 3) -> dict:
        """基于句子重要度的摘要提取"""
        start = time.time()
        # 分句
        sentences = re.split(r'[。！？
.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if not sentences:
            return {"success": True, "summary": "", "sentences": 0}

        # 计算词频
        all_words = re.findall(r'[\u4e00-\u9fff\w]+', text.lower())
        word_freq = Counter(all_words)
        max_freq = max(word_freq.values()) if word_freq else 1

        # 计算每句得分
        scored = []
        for s in sentences:
            words = re.findall(r'[\u4e00-\u9fff\w]+', s.lower())
            score = sum(word_freq.get(w, 0) / max_freq for w in set(words))
            scored.append((score, s))

        scored.sort(reverse=True, key=lambda x: x[0])
        top = [s for _, s in scored[:max_sentences]]

        # 按原文顺序重排
        ordered = []
        for s in sentences:
            if s in top and s not in ordered:
                ordered.append(s)
            if len(ordered) >= max_sentences:
                break

        summary = '。'.join(ordered) + ('。' if ordered else '')
        elapsed = time.time() - start
        return {
            "success": True,
            "summary": summary,
            "total_sentences": len(sentences),
            "selected": len(ordered),
            "elapsed_seconds": round(elapsed, 3),
        }

    def classify_text(self, text: str) -> dict:
        """基于关键词的文本分类"""
        categories = {
            "技术/编程": ["代码", "函数", "API", "接口", "部署", "架构", "算法", "数据库", "前端", "后端",
                        "bug", "commit", "merge", "docker", "k8s", "python", "javascript"],
            "商业/管理": ["营收", "利润", "增长", "市场", "战略", "投资", "融资", "IPO", "并购",
                        "财报", "股东", "CEO", "董事会", "季度"],
            "金融/投资": ["股票", "基金", "理财", "A股", "港股", "美股", "ETF", "指数", "收益率",
                        "跌幅", "涨幅", "成交量", "市值"],
            "学术/研究": ["论文", "研究", "实验", "数据", "分析", "方法论", "假设", "验证", "期刊",
                        "引用", "文献", "综述", "统计"],
            "产品/设计": ["用户体验", "UI", "UX", "设计", "原型", "交互", "用户调研", "可用性",
                        "界面", "交互设计", "产品经理"],
        }
        text_lower = text.lower()
        scores = {}
        for cat, kws in categories.items():
            score = sum(text_lower.count(kw.lower()) for kw in kws)
            if score > 0:
                scores[cat] = score

        if not scores:
            return {"success": True, "category": "未分类", "scores": {}, "confidence": 0}

        best = max(scores, key=scores.get)
        total = sum(scores.values())
        confidence = round(scores[best] / total, 3) if total > 0 else 0
        return {
            "success": True,
            "category": best,
            "scores": dict(sorted(scores.items(), key=lambda x: -x[1])),
            "confidence": confidence,
        }

    def full_analysis(self, text: str) -> dict:
        """全量分析：提取+关键词+摘要+分类"""
        start = time.time()
        entities = self.extract_entities(text)
        keywords = self.extract_keywords(text)
        summary = self.extract_summary(text)
        category = self.classify_text(text)
        elapsed = time.time() - start
        return {
            "success": True,
            "entities": entities,
            "keywords": keywords,
            "summary": summary,
            "category": category,
            "text_length": len(text),
            "elapsed_seconds": round(elapsed, 3),
        }

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        if params is None:
            params = {}
        try:
            text = params.get("text", "")
            dispatch = {
                "entities": lambda: self.extract_entities(text, params.get("entity_types")),
                "keywords": lambda: self.extract_keywords(text, int(params.get("top_n", 10))),
                "summary": lambda: self.extract_summary(text, int(params.get("max_sentences", 3))),
                "classify": lambda: self.classify_text(text),
                "analyze": lambda: self.full_analysis(text),
                "status": lambda: {"success": True, "status": "ready", "version": "V0.1"},
            }
            handler = dispatch.get(action)
            if handler:
                return handler()
            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"HyperExtract error: {e}")
            return {"success": False, "error": str(e)[:200]}

module_class = HyperExtract
