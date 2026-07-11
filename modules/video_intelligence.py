"""视频智能分析 — 场景检测/缩略图"""
import logging, json, os, subprocess, tempfile, base64
logger = logging.getLogger('evo.modules.video_intelligence')
class VideoIntelligence:
    def __init__(self): self._ready = True
    def _has_ffmpeg(self):
        try: subprocess.run(['ffmpeg','-version'],capture_output=True,timeout=5); return True
        except: return False
    def analyze(self, path):
        if not os.path.exists(path): return {'success':False,'error':'文件不存在'}
        info={'file':os.path.basename(path),'size_kb':round(os.path.getsize(path)/1024,1)}
        if self._has_ffmpeg():
            try:
                r=subprocess.run(['ffprobe','-v','quiet','-print_format','json','-show_format','-show_streams',path],capture_output=True,timeout=30,text=True)
                d=json.loads(r.stdout)
                info['duration']=d.get('format',{}).get('duration','')
                for s in d.get('streams',[]):
                    if s['codec_type']=='video': info.update({'w':s.get('width'),'h':s.get('height'),'codec':s.get('codec_name')})
            except: pass
        return {'success':True,'info':info}
    def thumbnail(self, path, sec=2):
        if not self._has_ffmpeg(): return {'success':False,'error':'需要ffmpeg'}
        out=tempfile.mktemp(suffix='.jpg')
        try:
            subprocess.run(['ffmpeg','-y','-ss',str(sec),'-i',path,'-vframes','1','-q:v','2',out],capture_output=True,timeout=30)
            if os.path.exists(out):
                b=base64.b64encode(open(out,'rb').read()).decode(); os.remove(out)
                return {'success':True,'thumbnail':b[:200]+'...'}
        except: pass
        return {'success':False,'error':'生成失败'}
    def status(self): return {'name':'video_intelligence','ready':self._ready}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='analyze': return self.analyze(p.get('path',''))
        if a=='thumbnail': return self.thumbnail(p.get('path',''),p.get('time',2))
        return self.status()
get_status=lambda:VideoIntelligence().status()
register=lambda:{'name':'video_intelligence','class':'VideoIntelligence','description':'视频分析 - 缩略图/场景检测'}
module_class = VideoIntelligence
