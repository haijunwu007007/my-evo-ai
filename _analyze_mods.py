"""Analyze boilerplate ratio in weakest modules and inject real logic"""
import os, re, sys

root = 'D:/AUTO-EVO-AI-V0.1/modules'
# Focus on 8 representative weak modules
targets = ['goal_tracker.py','agency_swarm.py','event_bus.py','module_adapter.py',
           'template_registry.py','github_webhook.py','workflow_manager.py','memory_guard.py']

for fname in targets:
    fp = os.path.join(root, fname)
    code = open(fp, 'r', encoding='utf-8', errors='ignore').read()
    # Count lines
    lines = code.split('\n')
    total = len(lines)
    
    # Count boilerplate patterns
    boiler_keywords = ['__module_meta__', '# Grade:', '"""', "'''", 
                       'def _get_available_actions', 'def get_status',
                       'def health_check', 'def initialize', 'def __init__',
                       '_action_', 'self._history.append', 'self._stats']
    boiler_count = 0
    for l in lines:
        stripped = l.strip()
        if any(kw in stripped for kw in boiler_keywords):
            boiler_count += 1
    
    # Count non-boiler non-comment non-blank lines
    real = [l for l in lines if l.strip() and not l.strip().startswith('#') 
            and not l.strip().startswith('"""') and not l.strip().startswith("'''")
            and 'self._history' not in l and '_action_' not in l]
    
    # Inline approach: add real logic to initialize + health_check
    has_real_init = 'self.' in code and ('open(' in code or 'import ' in code)
    
    print(f'{fname:35s} {total:4d} total, {len(real):4d} real, {boiler_count:3d} boiler')
    
    # Check if initialize/health_check have real logic or just stubs
    init_match = re.search(r'def initialize\(self.*?\):(.*?)(?=\n\s+def|\nclass)', code, re.DOTALL)
    hc_match = re.search(r'def health_check\(self.*?\):(.*?)(?=\n\s+def|\nclass)', code, re.DOTALL)
    
    has_real_init = False
    has_real_hc = False
    if init_match:
        init_body = init_match.group(1)
        has_real_init = any(kw in init_body for kw in ['load', 'connect', 'open', 'read', 'import', 'self._', 'try'])
    if hc_match:
        hc_body = hc_match.group(1)
        has_real_hc = any(kw in hc_body for kw in ['return {"', 'try', 'import', 'self.'])
    
    print(f'         init_real={has_real_init}, hc_real={has_real_hc}')
    print()
