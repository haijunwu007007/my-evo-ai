"""
AUTO-EVO-AI V0.1 — AI简历优化+模拟面试
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json, os, time
from pathlib import Path

router = APIRouter(prefix="/api/v1/resume", tags=["resume"])
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class ResumeRequest(BaseModel):
    resume: str
    job_title: Optional[str] = ""

@router.post("/analyze")
async def analyze_resume(req: ResumeRequest):
    lines = req.resume.strip().split("\n")
    word_count = len(req.resume)
    skill_keywords = ["Python","Java","JavaScript","SQL","项目管理","沟通","团队","领导","分析","设计"]
    found_skills = [s for s in skill_keywords if s.lower() in req.resume.lower()]
    score = min(100, max(40, 40 + len(found_skills)*5 + min(int(word_count/20), 30)))
    suggestions = []
    if word_count < 200: suggestions.append("内容过少，建议补充工作经历和项目细节")
    if len(found_skills) < 3: suggestions.append("技能描述不清晰，建议列出具体技术栈")
    if "量化" not in req.resume.lower(): suggestions.append("建议用具体数字量化工作成果")
    if "结果" not in req.resume.lower(): suggestions.append("增加成果导向的描述")
    questions = [
        f"请简要介绍你在{req.job_title or '该领域'}的相关经验",
        "你最大的职业成就是什么？",
        f"你为什么认为自己适合{req.job_title or '这个职位'}？",
        "你的职业规划是什么？",
    ]
    return {"success":True,"score":score,"word_count":word_count,"skills":found_skills,
            "suggestions":suggestions,"interview_questions":questions}

class FeedbackRequest(BaseModel):
    resume: str
    question: str
    answer: str
    job_title: Optional[str] = ""

@router.post("/feedback")
async def interview_feedback(req: FeedbackRequest):
    score = min(10, max(3, len(req.answer)//20 + 5))
    tips = []
    if len(req.answer) < 30: tips.append("回答太简短，建议展开具体案例")
    if "我" in req.answer: tips.append("回答以个人为中心，建议结合岗位需求")
    if "结果" not in req.answer.lower(): tips.append("建议补充结果和数据")
    return {"success":True,"score":score,"tips":tips,"summary":f"回答评分{score}/10，建议回答时多结合具体数据"}
