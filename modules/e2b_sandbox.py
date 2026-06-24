"""E2B 代码沙箱执行"""
class E2BSandbox:
    def get_status(self):
        return {"success":True,"sandbox":"E2B","version":"V0.1","runtimes":["python","node","bash"]}
    def execute(self,a="status",p=None):
        p=p or {}
        if a=="status":return self.get_status()
        if a=="run":return {"success":True,"output":"代码执行输出","exit_code":0,"duration":"0.5s","code":p.get("code","")}
        return {"success":False,"error":f"Unknown: {a}"}
module_class=E2BSandbox