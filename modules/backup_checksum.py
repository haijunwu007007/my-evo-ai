"""备份校验 — SHA256校验"""
import logging, hashlib, os
logger = logging.getLogger('evo.modules.backup_checksum')
class BackupChecksum:
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
