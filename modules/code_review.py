"""代码审查 — 静态分析+AI检查"""
import logging, re, json, os
logger = logging.getLogger('evo.modules.code_review')
class CodeReview:
    def __init__(self): self._ready = True
    def review_file(self, filepath):
        if not os.path.exists(filepath): return {'success':False,'error':'文件不存在'}
        try:
            text = open(filepath,'r',encoding='utf-8',errors='replace').read()
            issues = []
            if re.search(r'except\s*:', text): issues.append({'severity':'error','msg':'裸except: 应指定异常类型'})
            if re.search(r'print\(', text): issues.append({'severity':'warn','msg':'含print()调试语句'})
            if 'TODO' in text: issues.append({'severity':'info','msg':'含TODO标记'})
            if 'FIXME' in text: issues.append({'severity':'info','msg':'含FIXME标记'})
            if 'import os' in text and '.environ' not in text: issues.append({'severity':'warn','msg':'import os但未使用os.environ'})
            return {'success':True,'file':os.path.basename(filepath),'lines':len(text.split('\n')),'issues':issues,'issue_count':len(issues)}
        except Exception as e: return {'success':False,'error':str(e)}
    def review_text(self, code):
        issues = []
        lines = code.split('\n')
        for i,line in enumerate(lines):
            s=line.strip()
            if re.search(r'except\s*:', s): issues.append({'severity':'error','line':i+1,'msg':'裸except'})
            if re.search(r'print\(', s): issues.append({'severity':'warn','line':i+1,'msg':'print调试'})
        return {'success':True,'lines':len(lines),'issues':issues,'issue_count':len(issues)}
    def status(self): return {'name':'code_review','ready':self._ready}
    def execute(self,action='',params=None):
        params=params or {}
        if action=='review': return self.review_file(params.get('path',''))
        if action=='review_text': return self.review_text(params.get('code',''))
        return self.status()
get_status = lambda: CodeReview().status()
register = lambda: {'name':'code_review','class':'CodeReview','description':'代码审查 - 静态分析检查'}\nmodule_class = CodeReview\n