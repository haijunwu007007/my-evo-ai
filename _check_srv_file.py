import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)

stdin, stdout, stderr = s.exec_command("cat /home/ubuntu/my-evo-ai/modules/qodo_review.py")
content = stdout.read().decode()
print(content)
print("FILE SIZE:", len(content))
print("Has name fix:", '"name":' in content)
print("Has QodoReviewModule:", "class QodoReviewModule" in content)
s.close()
