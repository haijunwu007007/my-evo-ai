import sys
sys.stdout.reconfigure(encoding='utf-8')
import ast

lines=open('modules/openhands_agent.py','r',encoding='utf-8').readlines()
for i in range(38,48):
    print(f'{i+1}: {repr(lines[i].rstrip())}')
