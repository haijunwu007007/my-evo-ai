import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
_,o,_=C.exec_command("sudo journalctl -u evo -n 40 --no-pager 2>/dev/null|grep -A3 'Error\\|error\\|Traceback'|head -30",timeout=15,get_pty=True)
print(o.read().decode()[:1000])
C.close()
