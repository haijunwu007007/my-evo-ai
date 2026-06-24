# coding: utf-8
import logging
logger = logging.getLogger("perplexica_search")
class Perplexica:
    def __init__(s):
        s.st = {"module":"Perplexica","v":"V0.1","ready":True}
    def get_status(s): return {"success":True,**s.st}
    def execute(s,a="status",p=None):
        p=p or {}
        if a=="status":return s.get_status()
        return {"success":True,"action":a,"params":p}
module_class=Perplexica
