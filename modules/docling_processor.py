"""文档解析器"""
import logging,os,json
logger=logging.getLogger("evo.modules.docling_processor")
class DoclingProcessor:
 def __init__(s):s._ready=True
 def parse(s,path):
  if not os.path.exists(path):return{"success":False,"error":"文件不存在"}
  try:
   ext=os.path.splitext(path)[1].lower()
   if ext==".txt":text=open(path,"r",encoding="utf-8",errors="replace").read()
   elif ext==".json":text=json.dumps(json.loads(open(path,"r",encoding="utf-8").read()),ensure_ascii=False,indent=2)
   elif ext==".csv":
    import csv;rows=[]
    with open(path,"r",encoding="utf-8")as f:
     for row in csv.DictReader(f):rows.append(row)
    text=json.dumps(rows,ensure_ascii=False,indent=2)
   else:text=open(path,"r",encoding="utf-8",errors="replace").read()
   return{"success":True,"file":os.path.basename(path),"text":text[:2000],"length":len(text)}
  except Exception as e:return{"success":False,"error":str(e)}
 def status(s):return{"name":"docling_processor","ready":s._ready}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="parse":return s.parse(p.get("path",""))
  return s.status()
get_status=lambda:DoclingProcessor().status()
register=lambda:{"name":"docling_processor","class":"DoclingProcessor","description":"文档解析器"}\nmodule_class = DoclingProcessor\n