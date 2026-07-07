import subprocess, sys
subprocess.run(['git', '-C', r'D:\AUTO-EVO-AI-V0.1', 'add', '-A'], check=True)
subprocess.run(['git', '-C', r'D:\AUTO-EVO-AI-V0.1', 'commit', '-m', 'feat: mobile CSS + sidebar hamburger buttons'], check=True)
subprocess.run(['git', '-C', r'D:\AUTO-EVO-AI-V0.1', 'push', 'origin', 'master'], check=True)
print("Done")
