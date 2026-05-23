# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - RAG 知识引擎（A级）

基于内存向量检索的知识引擎，支持文档索引和语义搜索"""
__module_meta__ = {"id":"rag-knowledge-engine","name":"RAG Knowledge Engine","version":"1.0.0","group":"intelligence","grade":"A",
    "tags":["intelligence","rag","knowledge","search","embedding"],"description":"RAG knowledge engine with vector search"}
import time, uuid, logging, json, math
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.rag-knowledge-engine")
class RAGKnowledgeEngine(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="rag-knowledge-engine";MODULE_NAME="RAG 知识引擎";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._documents:List[Dict]=[];self._embeddings_cache:Dict[str,List[float]]={}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID,checks={"documents":len(self._documents)})
    async def execute(self,action=None,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _tokenize(self,text:str)->List[str]:
        import re;return re.findall(r'\w+',text.lower())
    def _tfidf_vector(self,tokens:List[str])->Dict[str,float]:
        from collections import Counter
        tf=Counter(tokens);max_f=max(tf.values()) if tf else 1
        return{k:v/max_f for k,v in tf.items()}
    def _cosine_similarity(self,v1:Dict[str,float],v2:Dict[str,float])->float:
        all_keys=set(v1)|set(v2)
        dot=sum(v1.get(k,0)*v2.get(k,0) for k in all_keys)
        n1=math.sqrt(sum(v*v for v in v1.values()));n2=math.sqrt(sum(v*v for v in v2.values()))
        return dot/(n1*n2) if n1*n2>0 else 0
    def _dispatch(self,p):
        a=p.get("action","status");limit=int(p.get("limit",5))
        if a=="status":
            return{"success":True,"documents":len(self._documents),"source_count":len(set(d.get("source","") for d in self._documents))}
        if a=="index":
            text=p.get("text","");source=p.get("source","");tags=p.get("tags","")
            if not text:return{"success":False,"error":"text_required"}
            doc_id=str(uuid.uuid4())[:8];tokens=self._tokenize(text)
            doc={"id":doc_id,"text":text,"tokens":tokens[:500],"source":source,"tags":tags,"indexed":time.time()}
            self._documents.append(doc)
            return{"success":True,"doc_id":doc_id,"token_count":len(tokens)}
        if a=="search":
            query=p.get("query","")
            if not query:return{"success":False,"error":"query_required"}
            q_tokens=self._tokenize(query);q_vec=self._tfidf_vector(q_tokens)
            if not self._documents:return{"success":True,"results":[],"count":0}
            scored=[]
            for doc in self._documents:
                d_vec=self._tfidf_vector(doc["tokens"])
                score=self._cosine_similarity(q_vec,d_vec)
                if score>0.01:scored.append((score,doc))
            scored.sort(key=lambda x:-x[0])
            results=[{"id":d["id"],"text":d["text"][:200],"source":d.get("source",""),
                "score":round(s,4)} for s,d in scored[:limit]]
            return{"success":True,"results":results,"count":len(results)}
        if a=="context":
            query=p.get("query","");n=int(p.get("max_tokens",2000))
            results=self._dispatch({"action":"search","query":query,"limit":5})
            if not results.get("success"):return results
            texts=[r["text"] for r in results.get("results",[])]
            context="\n\n".join(texts)
            if len(context)>n:context=context[:n]
            return{"success":True,"context":context,"source_count":len(texts)}
        if a=="chunk":
            text=p.get("text","");size=int(p.get("chunk_size",500));overlap=int(p.get("overlap",50))
            chunks=[text[i:i+size] for i in range(0,len(text),size-overlap)]
            return{"success":True,"chunks":len(chunks),"chunk_size":size,"overlap":overlap,"total_chars":len(text)}
        if a=="rerank":
            query=p.get("query","");results=p.get("results",[]);top_k=int(p.get("top_k",5))
            q_tokens=self._tokenize(query);q_vec=self._tfidf_vector(q_tokens)
            scored=[]
            for r in results:
                r_tokens=self._tokenize(r.get("text",""));r_vec=self._tfidf_vector(r_tokens)
                score=self._cosine_similarity(q_vec,r_vec)
                scored.append({**r,"score":round(score,4)})
            scored.sort(key=lambda x:-x["score"])
            return{"success":True,"results":scored[:top_k],"count":len(scored[:top_k])}
        if a=="feedback":
            doc_id=p.get("doc_id","");rating=int(p.get("rating",5))
            for d in self._documents:
                if d.get("id")==doc_id:
                    d["feedback"]=rating;d["feedback_at"]=time.time()
                    return{"success":True,"doc_id":doc_id,"rating":rating}
            return{"success":False,"error":"doc_not_found"}
        if a=="document_stats":
            if not self._documents:return{"success":True,"documents":0}
            avg_len=sum(len(d.get("text",""))for d in self._documents)/len(self._documents)
            sources={d.get("source","unknown")for d in self._documents}
            return{"success":True,"documents":len(self._documents),"avg_length":round(avg_len,1),
                "sources":list(sources),"total_tokens":sum(len(d.get("tokens",[]))for d in self._documents)}
        return{"success":False,"error":f"unknown_action:{a}"}
    async def shutdown(self)->None:self._documents.clear();self.status=ModuleStatus.STOPPED
module_class=RAGKnowledgeEngine
