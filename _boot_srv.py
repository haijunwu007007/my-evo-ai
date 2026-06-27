import sys, os, traceback
os.environ['EVO_WORKERS'] = '1'
os.chdir('D:/AUTO-EVO-AI-V0.1')
sys.path.insert(0, 'D:/AUTO-EVO-AI-V0.1')
try:
    exec(open('D:/AUTO-EVO-AI-V0.1/api_server.py', encoding='utf-8').read())
except SystemExit:
    pass
except:
    with open('D:/_crash.txt', 'w', encoding='utf-8') as f:
        traceback.print_exc(file=f)
    print('CRASHED - see D:/_crash.txt', file=sys.stderr)
