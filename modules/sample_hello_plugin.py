"""示例Hello插件 — 插件开发模板"""
import logging
logger = logging.getLogger('evo.modules.sample_hello_plugin')
class SampleHelloPlugin:
    def __init__(self): self._ready=True; self._name='HelloPlugin'
    def hello(self, name='World'): return {'success':True,'message':f'Hello, {name}! 这是示例插件'}
    def echo(self, text): return {'success':True,'echo':text}
    def status(self): return {'name':'sample_hello_plugin','ready':self._ready,'name':self._name}
    def execute(self, a='', p=None):
        p=p or {}
        if a=='hello': return self.hello(p.get('name','World'))
        if a=='echo': return self.echo(p.get('text',''))
        return self.status()
get_status=lambda:SampleHelloPlugin().status()
register=lambda:{'name':'sample_hello_plugin','class':'SampleHelloPlugin','description':'示例Hello插件'}
module_class = SampleHelloPlugin
