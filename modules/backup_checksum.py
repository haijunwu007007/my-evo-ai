"""备份校验 — SHA256校验"""
import logging, hashlib, os
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, HealthReport
logger = logging.getLogger('evo.modules.backup_checksum')
class BackupChecksum(EnterpriseModule):
    def __init__(self): self._ready = True
    def checksum(self, path):
        if not os.path.exists(path): return {'success':False,'error':'文件不存在'}
        h=hashlib.sha256()
        with open(path,'rb') as f:
            while True:
                c=f.read(65536)
                if not c: break
                h.update(c)
        return {'success':True,'file':os.path.basename(path),'sha256':h.hexdigest(),'size':os.path.getsize(path)}
    def verify(self, path, expected):
        r=self.checksum(path)
        if not r.get('success'): return r
        return {'success':True,'match':r['sha256']==expected,'computed':r['sha256']}
    def status(self): return {'name':'backup_checksum','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='checksum': return self.checksum(p.get('path',''))
        if a=='verify': return self.verify(p.get('path',''),p.get('hash',''))
        return self.status()
get_status=lambda:BackupChecksum().status()
register=lambda:{'name':'backup_checksum','class':'BackupChecksum','description':'备份校验 - SHA256'}

async def execute(self, action=None, params=None):
 return await self._safe_execute(action, params, handler=self._dispatch)

async def _dispatch(self, action, params):
 action = action.lower().strip() if action else "status"
 return await self.status()

async def status(self):
 return {"module": "backup_checksum", "ready": getattr(self, "_ready", True),
         "status": self.status.value if hasattr(self, "status") else "running"}

def health_check(self):
 return HealthReport(status=self.status.value if hasattr(self, "status") else "running",
                    healthy=getattr(self, "_ready", True), module_id=self.MODULE_ID)

def initialize(self):
 self.status = ModuleStatus.RUNNING
 return {"success": True}

def shutdown(self):
 self.status = ModuleStatus.STOPPED
 return {"success": True}

module_class = BackupChecksum
