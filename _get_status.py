import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)

stdin, stdout, stderr = s.exec_command("sudo systemctl status evo.service 2>&1 | head -8")
print("SERVICE STATUS:")
print(stdout.read().decode()[:400])

# Get ALL journal lines since last boot
stdin2, stdout2, stderr2 = s.exec_command("journalctl -u evo.service --no-pager --since '1 minute ago' 2>&1")
log = stdout2.read().decode().strip()
if log:
    print("\nRECENT LOGS:")
    for line in log.split("\n")[-20:]:
        print(line[:200])
else:
    print("\nNo recent logs")
    
s.close()
