# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - 数据分析引擎（A级）"""
__module_meta__ = {"id":"data-analysis","name":"Data Analysis","version":"V0.1","group":"data","grade":"A",
    "tags":["data","analysis","statistics"],"description":"数据分析引擎 - 统计/相关性/异常检测"}
import time, uuid, logging, math
from typing import Any, Dict, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin, Result)
logger=logging.getLogger("evo.data-analysis")
class DataAnalysis(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="data-analysis";MODULE_NAME="数据分析";VERSION = "V0.1";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._results={}
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action,params=None):return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status");data=p.get("data",[]);vals=[v for v in data if isinstance(v,(int,float))]
        if not vals:return {"error":"need real data — provide 'data' array of numbers","hint":{"action":"describe","data":[1,2,3,4,5,6,7,8,9,10]}}
        n=len(vals);mean=sum(vals)/n;var=sum((v-mean)**2 for v in vals)/n;std=var**0.5;s_vals=sorted(vals)
        if a=="describe":return {"success":True,"stats":{"count":n,"mean":round(mean,2),"std":round(std,2),"min":min(vals),"p25":s_vals[n//4],"p50":s_vals[n//2],"p75":s_vals[3*n//4],"max":max(vals),"skewness":round(sum((v-mean)**3 for v in vals)/(n*std**3+1e-10),3)if std>0 else 0}}
        if a=="correlation":
            x=p.get("x",vals)
            if not x:return {"error":"need real data for correlation — provide 'x' array"}
            y=p.get("y",[])
            if not y:return {"error":"need real data for correlation — provide 'y' array"}
            mx=sum(x)/len(x);my=sum(y)/len(y);sx=math.sqrt(sum((v-mx)**2 for v in x)/len(x));sy=math.sqrt(sum((v-my)**2 for v in y)/len(y));r=sum((x[i]-mx)*(y[i]-my) for i in range(len(x)))/(len(x)*sx*sy+1e-10)
            return {"success":True,"pearson":round(r,4),"interpretation":"strong positive"if r>0.7 else"weak"if abs(r)<0.3 else"moderate"}
        if a in ("outliers","anomaly"):
            q1=s_vals[n//4];q3=s_vals[3*n//4];iqr=q3-q1;lower=q1-1.5*iqr;upper=q3+1.5*iqr;anomalies=[v for v in vals if v<lower or v>upper]
            return {"success":True,"method":"IQR","q1":round(q1,2),"q3":round(q3,2),"iqr":round(iqr,2),"lower_fence":round(lower,2),"upper_fence":round(upper,2),"anomalies":anomalies,"anomaly_rate":round(len(anomalies)/n*100,1)}
        if a=="histogram":
            bins=int(p.get("bins",10));bw=(max(vals)-min(vals))/bins;h=[0]*bins
            for v in vals:idx=min(bins-1,int((v-min(vals))/bw));h[idx]+=1
            return {"success":True,"histogram":h,"bin_width":round(bw,2),"min":min(vals),"max":max(vals)}
        if a=="normalize":
            method=p.get("method","minmax")
            if method=="minmax":mn,mx=min(vals),max(vals);nrm=[round((v-mn)/(mx-mn+1e-10),4)for v in vals]
            elif method=="zscore":mu=mean;sigma=std if std>0 else 1;nrm=[round((v-mu)/sigma,4)for v in vals]
            else:return{"error":f"unknown_method:{method}"}
            return{"success":True,"method":method,"normalized":nrm,"min":round(min(nrm),4),"max":round(max(nrm),4)}
        if a=="regression":
            x=p.get("x",[]);y=p.get("y",[])
            if not x or not y or len(x)!=len(y):return{"error":"need 'x' and 'y' of equal length"}
            n_r=len(x);mx_r=sum(x)/n_r;my_r=sum(y)/n_r
            num=sum((x[i]-mx_r)*(y[i]-my_r)for i in range(n_r))
            den=sum((x[i]-mx_r)**2 for i in range(n_r))
            slope=num/(den+1e-10);intercept=my_r-slope*mx_r
            r2_num=sum((y[i]-(slope*x[i]+intercept))**2 for i in range(n_r))
            r2_den=sum((y[i]-my_r)**2 for i in range(n_r))
            r2=1-r2_num/(r2_den+1e-10)
            return{"success":True,"slope":round(slope,4),"intercept":round(intercept,4),"r_squared":round(r2,4),"formula":f"y={round(slope,4)}x+{round(intercept,4)}"}
        if a=="clustering":
            k=int(p.get("k",2))
            if k<2 or k>n:return{"error":f"k must be 2-{n}"}
            centroids=[vals[i]for i in range(k)]
            for _ in range(50):
                clusters=[[]for _ in range(k)]
                for v in vals:idx=min(range(k),key=lambda i:abs(v-centroids[i]));clusters[idx].append(v)
                new_centroids=[sum(c)/len(c)if c else centroids[i]for i,c in enumerate(clusters)]
                if all(abs(new_centroids[i]-centroids[i])<1e-6 for i in range(k)):break
                centroids=new_centroids
            return{"success":True,"k":k,"clusters":[{"centroid":round(centroids[i],2),"size":len(clusters[i]),"min":round(min(clusters[i]),2),"max":round(max(clusters[i]),2),"values":clusters[i]}for i in range(k)if clusters[i]]}
        return {"error":f"unknown:{a}"}
    async def shutdown(self)->None:self._results.clear();self.status=ModuleStatus.STOPPED
module_class=DataAnalysis
