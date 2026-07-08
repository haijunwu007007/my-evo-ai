"""服务器端 PG 配置脚本 — 创建数据库+用户+一次性数据迁移"""
import paramiko, time, json

HOST = '122.51.144.227'
USER = 'ubuntu'
PW = 'Hj711201'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PW, timeout=15)

cmds = """
echo '=== STEP 1: 确保 postgresql 运行 ==='
sudo systemctl start postgresql 2>/dev/null || true
sudo systemctl enable postgresql 2>/dev/null || true
sleep 1

echo '=== STEP 2: 创建 evo 用户和数据库 ==='
sudo -u postgres psql -c "CREATE USER evo WITH PASSWORD 'Evo@2026!PG';" 2>/dev/null || echo 'user exists'
sudo -u postgres psql -c "CREATE DATABASE evodb OWNER evo;" 2>/dev/null || echo 'db exists'
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE evodb TO evo;" 2>/dev/null || true

echo '=== STEP 3: 安装 psycopg2 ==='
pip3 install psycopg2-binary 2>/dev/null | tail -2 || pip install psycopg2-binary 2>/dev/null | tail -2

echo '=== STEP 4: 测试连接 ==='
PGPASSWORD='Evo@2026!PG' psql -h localhost -U evo -d evodb -c 'SELECT 1 as ok;' 2>&1

echo '=== STEP 5: 安装 pgvector ==='
sudo apt-get install -y postgresql-14-pgvector 2>/dev/null | tail -3 || echo 'pgvector already installed or not available'

echo '=== DONE ==='
"""

stdin, stdout, stderr = ssh.exec_command(cmds)
print(stdout.read().decode())
print("STDERR:", stderr.read().decode()[:500])
ssh.close()
