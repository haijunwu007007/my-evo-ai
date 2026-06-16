#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# 删掉前6行（sed插错的+原头部）
C.exec_command("sudo sed -i '1,6d' /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10)
time.sleep(1)
# 重建正确的头部
C.exec_command("sudo sed -i '1i\\from __future__ import annotations' /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10)
C.exec_command("sudo sed -i '2i\\\"\"\"开源中心集成引擎\"\"\"' /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10)
C.exec_command("sudo sed -i '3i\\import os,json,time,subprocess,asyncio,shutil' /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10)
C.exec_command("sudo sed -i '4i\\from pathlib import Path' /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10)
C.exec_command("sudo sed -i '5i\\from api.hub.models import add_project,get_project,update_project,delete_project,list_projects' /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10)
C.exec_command("sudo sed -i '6i\\from core.logging_config import get_logger' /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10)
time.sleep(1)
# 检查前10行
_,o,_=C.exec_command("head -10 /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10,get_pty=True)
print(o.read().decode()[:400])
C.close()
