"""会议机器人 — 纪要/日程"""
import logging, time
logger = logging.getLogger('evo.modules.meeting_bot')
class MeetingBot:
    def __init__(self): self._ready=True; self._meetings={}
    def create(self, title, participants='', notes=''):
        mid=f'm_{int(time.time())}'
        self._meetings[mid]={'id':mid,'title':title,'participants':participants.split(',') if participants else [],'notes':notes,'created':time.time()}
        return {'success':True,'meeting':self._meetings[mid]}
    def add_notes(self, mid, notes):
        if mid in self._meetings: self._meetings[mid]['notes']+=f'\n{notes}'; return {'success':True}
        return {'success':False,'error':'不存在'}
    def summarize(self, mid):
        m=self._meetings.get(mid)
        if not m: return {'success':False,'error':'不存在'}
        return {'success':True,'summary':f"# {m['title']}\n参与人: {', '.join(m['participants'])}\n{m['notes'][:500]}"}
    def status(self): return {'name':'meeting_bot','ready':self._ready,'meetings':len(self._meetings)}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='create': return self.create(p.get('title',''),p.get('participants',''),p.get('notes',''))
        if a=='add_notes': return self.add_notes(p.get('id',''),p.get('notes',''))
        if a=='summarize': return self.summarize(p.get('id',''))
        return self.status()
get_status=lambda:MeetingBot().status()
register=lambda:{'name':'meeting_bot','class':'MeetingBot','description':'会议机器人 - 纪要日程'}
