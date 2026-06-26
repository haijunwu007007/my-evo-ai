import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)

# Read current config
stdin, stdout, stderr = s.exec_command("sudo cat /etc/nginx/sites-available/autoevoai.com")
cfg = stdout.read().decode()

# Fix: Change "listen 443 ssl;" to "listen 443 ssl default_server;"
# So HTTPS IP access works without needing server_name match
cfg = cfg.replace("listen 443 ssl; # managed by Certbot", "listen 443 ssl default_server; # managed by Certbot")

# Fix the port 80 block: add default_server and proper server_name
old_http = """    listen 80;
    server_name 122.51.144.227;
    return 301 https://$host$request_uri; # managed by Certbot"""

new_http = """    listen 80 default_server;
    server_name autoevoai.com www.autoevoai.com 122.51.144.227;
    return 301 https://$host$request_uri; # managed by Certbot"""

cfg = cfg.replace(old_http, new_http, 1)

# Write back
sftp = s.open_sftp()
with sftp.open("/home/ubuntu/evo_nginx.conf", "w") as f:
    f.write(cfg)
sftp.close()

stdin, stdout, stderr = s.exec_command(
    "sudo cp /home/ubuntu/evo_nginx.conf /etc/nginx/sites-available/autoevoai.com && sudo nginx -t 2>&1"
)
result = (stdout.read() + stderr.read()).decode()
print("test:", result[:200])

if "test is successful" in result:
    s.exec_command("sudo nginx -s reload")
    print("reloaded")
else:
    print("FAILED")

s.close()
