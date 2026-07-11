"""多Agent团队"""
import logging,time
logger=logging.getLogger("evo.modules.multi_agent_crew")
class MultiAgentCrew:
 def __init__(s):s._ready=True;s._agents={};s._crews={}
 def add_agent(s,name,role,goal):
  aid="a_"+str(len(s._agents)+1);s._agents[aid]={"id":aid,"name":name,"role":role,"goal":goal};return{"success":True,"agent":s._agents[aid]}
 def create_crew(s,name,agent_ids):
  cid="c_"+str(int(time.time()));s._crews[cid]={"id":cid,"name":name,"agents":[s._agents.get(a,{})for a in agent_ids],"created":time.time()};return{"success":True,"crew":s._crews[cid]}
 def run_crew(s,cid,task):
  c=s._crews.get(cid)
  if not c:return{"success":False,"error":"不存在"}
  results=[]
  for a in c["agents"]:
   rn=a.get("name","");rr=a.get("role","")+"完成: "+task[:50]
   results.append({"agent":rn,"result":rr})
  return{"success":True,"crew":c["name"],"results":results}
 def status(s):return{"name":"multi_agent_crew","ready":s._ready,"agents":len(s._agents),"crews":len(s._crews)}
 def execute(s,a="",p=None):
  p=p or{}
  if a=="add_agent":return s.add_agent(p.get("name",""),p.get("role",""),p.get("goal",""))
  if a=="create_crew":return s.create_crew(p.get("name",""),p.get("agent_ids",[]))
  if a=="run_crew":return s.run_crew(p.get("crew_id",""),p.get("task",""))
  return s.status()
get_status=lambda:MultiAgentCrew().status()
register=lambda:{"name":"multi_agent_crew","class":"MultiAgentCrew","description":"多Agent团队"}
module_class = MultiAgentCrew
