"""AUTO-EVO-AI V0.1 — IoT 边缘网关桥接（A级）

抽象物联网关接口：模拟设备注册/遥测/命令。
"""
__module_meta__ = {"id":"iot-edge","name":"IoT Edge","version":"V0.1","group":"iot","grade":"A",
    "tags":["iot","edge"],"description":"IoT 边缘网关 — 设备注册/遥测/命令"}
import time, json, logging
from pathlib import Path
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin)
logger=logging.getLogger("evo.iot-edge")

DEVICES_FILE=Path(".evo_data/iot_devices.json")
def _load_devices():
    if DEVICES_FILE.exists():
        return json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
    return {"devices":[],"telemetry":[]}
def _save(data):
    DEVICES_FILE.parent.mkdir(parents=True,exist_ok=True)
    DEVICES_FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

class IoTEdge(CircuitBreakerMixin,RateLimiterMixin,EnterpriseModule):
    MODULE_ID="iot-edge";MODULE_NAME="IoT Edge";VERSION="v1.0";MODULE_LEVEL="A"
    def __init__(self,config=None):
        super().__init__(config);self._start=time.time()
    def initialize(self)->None:self.status=ModuleStatus.RUNNING
    def health_check(self)->HealthReport:
        return HealthReport(status=self.status.value,healthy=True,module_id=self.MODULE_ID)
    async def execute(self,action=None,params=None):
        return await self._safe_execute(action,params,handler=self._dispatch)
    def _dispatch(self,p):
        a=p.get("action","status")
        try:
            data=_load_devices()
            if a=="status":
                return{"success":True,"devices":len(data.get("devices",[])),
                    "telemetry_points":len(data.get("telemetry",[])),"uptime":round(time.time()-self._start,1)}
            if a=="register":
                dev={"id":p.get("device_id",f"dev_{int(time.time())}"),"name":p.get("name","sensor"),
                    "type":p.get("type","temperature"),"protocol":p.get("protocol","mqtt"),"registered":time.time()}
                data["devices"].append(dev);_save(data)
                return{"success":True,"device":dev}
            if a=="telemetry":
                did=p.get("device_id","");metric=p.get("metric","temperature");val=p.get("value",0)
                data["telemetry"].append({"device":did,"metric":metric,"value":val,"ts":time.time()})
                _save(data)
                return{"success":True,"recorded":True,"device":did,"metric":metric,"value":val}
            if a=="command":
                did=p.get("device_id","");cmd=p.get("command","reboot")
                return{"success":True,"device":did,"command":cmd,"status":"delivered","simulated":True}
            if a=="list_devices":
                return{"success":True,"devices":data.get("devices",[]),"count":len(data.get("devices",[]))}
            return{"success":False,"error":f"unknown_action:{a}"}
        except Exception as e:
            logger.error("[IoTEdge] %s: %s",a,e,exc_info=True)
            return{"success":False,"error":str(e)}
    async def shutdown(self)->None:self.status=ModuleStatus.STOPPED
module_class=IoTEdge
