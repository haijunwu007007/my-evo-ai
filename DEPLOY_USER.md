# 用户部署方案

## 给用户分配系统的方式

### 方式一：复制整个文件夹

```
1. 把 D:\AUTO-EVO-AI-V0.1 整个文件夹复制给用户
2. 用户双击 start.ps1（右键管理员运行）
3. 浏览器打开 http://localhost:8765/app/login
```

**前提：**
- Windows 电脑
- 已安装 Python 3.13+
- 已安装 Docker Desktop（如需启动外部工具）

### 方式二：云服务器一键部署

```
1. 购买 腾讯云/阿里云 2核2G 服务器（约30元/月）
2. 选择 Ubuntu 22.04
3. 把 deploy.sh 传给用户
4. 用户执行：bash deploy.sh <服务器IP>
5. 手机访问 http://<IP>:8765/app/login
```

### 方式三：Docker 单容器部署

```
（后续开发——把系统打包成单个 Docker 镜像）
docker run -d -p 8765:8765 auto-evo-ai:latest
```

> 当前阶段推荐方式一（复制文件夹）。
> 等确认用户有真实需求，再升级到方式二。
