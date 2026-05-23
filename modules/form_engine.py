# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 表单引擎（A级）

动态表单生成与验证引擎"""
__module_meta__ = {"id":"form-engine","name":"Form Engine","version":"1.0.0","group":"system","grade":"A",
    "tags":["system","form","validation","builder"],"description":"Dynamic form generation and validation engine"}
import time, uuid, logging, re
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.form-engine")
class FormEngine(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="form-engine";MODULE_NAME="表单引擎";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):super().__init__(config);self._templates:Dict[str,Dict]={}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        if a=="status":return{"success":True,"templates":len(self._templates)}
        if a=="create":
            name=p.get("name","");fields=p.get("fields",[])
            if not name or not fields:return{"success":False,"error":"name_and_fields_required"}
            self._templates[name]={"fields":fields,"created":time.time()}
            return{"success":True,"template":name,"fields":len(fields)}
        if a=="validate":
            template_name=p.get("template","");data=p.get("data",{})
            tmpl=self._templates.get(template_name)
            if not tmpl:return{"success":False,"error":f"unknown_template:{template_name}"}
            errors=[]
            for field in tmpl["fields"]:
                fname=field.get("name","");ftype=field.get("type","text");required=field.get("required",False)
                val=data.get(fname)
                if required and (val is None or str(val).strip()==""):
                    errors.append({"field":fname,"error":"required","message":f"{fname} is required"});continue
                if val is None or str(val).strip()=="":continue
                if ftype=="email" and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$',str(val)):
                    errors.append({"field":fname,"error":"invalid_email"})
                elif ftype=="number":
                    try:float(val)
                    except:errors.append({"field":fname,"error":"invalid_number"})
                elif ftype=="min_length" and len(str(val))<int(field.get("min",0)):
                    errors.append({"field":fname,"error":"too_short"})
            return{"success":True,"valid":len(errors)==0,"errors":errors,"template":template_name,"fields_validated":len(tmpl["fields"])}
        if a=="render":
            template_name=p.get("template","")
            tmpl=self._templates.get(template_name)
            if not tmpl:return{"success":False,"error":f"unknown_template:{template_name}"}
            return{"success":True,"template":template_name,"fields":tmpl["fields"],"schema":{"type":"object","properties":{f["name"]:{"type":f.get("type","string"),"required":f.get("required",False)} for f in tmpl["fields"]}}}
        if a=="submit":
            template_name=p.get("template","");data=p.get("data",{})
            val_result=self._dispatch({"action":"validate","template":template_name,"data":data})
            if not val_result.get("success"):return val_result
            if not val_result.get("valid",False):return{"success":False,"errors":val_result.get("errors",[])}
            submission_id=str(uuid.uuid4())[:8]
            return{"success":True,"submission_id":submission_id,"template":template_name}
        if a=="export":
            template_name=p.get("template","");fmt=p.get("format","json")
            tmpl=self._templates.get(template_name)
            if not tmpl:return{"success":False,"error":f"unknown_template:{template_name}"}
            schema=[{"name":f.get("name",""),"type":f.get("type","text"),"required":f.get("required",False)}for f in tmpl["fields"]]
            if fmt=="json":return{"success":True,"format":"json","schema":schema,"fields":len(schema)}
            elif fmt=="html":html="<form>";html+="".join(f'<label>{f.get("name","")}: <input type="{f.get("type","text")}"{" required"if f.get("required")else""}/></label><br/>'for f in tmpl["fields"]);html+="</form>";return{"success":True,"format":"html","html":html}
            return{"success":False,"error":f"unsupported_format:{fmt}"}
        if a=="delete":
            name=p.get("name","")
            if name in self._templates:del self._templates[name];return{"success":True,"deleted":name}
            return{"success":False,"error":f"template_not_found:{name}"}
        if a=="list":
            return{"success":True,"templates":[{"name":k,"fields":len(v["fields"]),"created":v.get("created",0)}for k,v in self._templates.items()],"count":len(self._templates)}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=FormEngine
