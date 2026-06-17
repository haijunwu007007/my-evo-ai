import sys; sys.path.insert(0,'api')
from agent_tools import list_tools
t = list_tools()
print('Tools:', len(t))
for x in t:
    if x['name'] in ['generate_image','transcribe_audio','convert_file','send_webhook','run_code_sandbox','capture_analyze']:
        print(f'  [{x["category"]}] {x["name"]}')
