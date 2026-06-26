import paramiko, socket, urllib.request

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)

# Check what's listening on 443
i,o,e = s.exec_command("ss -tlnp | grep 443")
print("443 listeners:", o.read().decode()[:300])

# Check the nginx configs
i,o,e = s.exec_command("ls -la /etc/nginx/sites-enabled/")
print("Enabled sites:", o.read().decode()[:300])

# Check autoevoai.com nginx config
i,o,e = s.exec_command("sudo cat /etc/nginx/sites-available/autoevoai.com | grep -E 'listen|server_name|ssl_certificate'")
print("Config:", o.read().decode()[:300])

# Test curl from the server itself
i,o,e = s.exec_command("curl -s -o /dev/null -w '%{http_code}' https://autoevoai.com/ 2>&1 || echo 'curl fail'")
print("Server self-test:", o.read().decode()[:100])

# Check if the ssl cert is valid
i,o,e = s.exec_command("openssl verify -CAfile /etc/letsencrypt/live/autoevoai.com/fullchain.pem /etc/letsencrypt/live/autoevoai.com/cert.pem 2>&1 | head -3")
print("Cert verify:", o.read().decode()[:100])

s.close()

# Test from outside
s2 = socket.socket()
s2.settimeout(5)
try:
    r = s2.connect_ex(("122.51.144.227", 443))
    print(f"External 443: {'OPEN' if r==0 else 'CLOSED('+str(r)+')'}")
except Exception as e:
    print(f"External 443 error: {e}")
s2.close()

s3 = socket.socket()
s3.settimeout(5)
try:
    r2 = s3.connect_ex(("122.51.144.227", 8765))
    print(f"External 8765: {'OPEN' if r2==0 else 'CLOSED('+str(r2)+')'}")
except Exception as e:
    print(f"External 8765 error: {e}")
s3.close()
