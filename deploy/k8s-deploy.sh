#!/bin/bash
# deploy/k8s-deploy.sh — 一键部署 AUTO-EVO-AI 到 K8s
# 用法: bash deploy/k8s-deploy.sh <namespace>
set -euo pipefail

NS="${1:-auto-evo-ai}"
REGISTRY="${REGISTRY:-docker.io/evo}"
TAG="${TAG:-latest}"
DOMAIN="${DOMAIN:-evo.your-domain.com}"

echo "=== AUTO-EVO-AI K8s 部署 ==="
echo "命名空间: $NS"
echo "镜像: $REGISTRY/auto-evo-ai:$TAG"
echo "域名: $DOMAIN"
echo ""

# 1. 构建并推送镜像
echo "[1/4] 构建 Docker 镜像..."
docker build -t "$REGISTRY/auto-evo-ai:$TAG" -f Dockerfile .
docker push "$REGISTRY/auto-evo-ai:$TAG"

# 2. 替换模板变量
echo "[2/4] 生成配置..."
sed "s|auto-evo-ai:latest|$REGISTRY/auto-evo-ai:$TAG|g" k8s/deployment.yaml > /tmp/evo-deploy.yaml
sed -i "s|evo.your-domain.com|$DOMAIN|g" /tmp/evo-deploy.yaml

# 3. 创建命名空间和 Secrets
echo "[3/4] 创建 K8s 资源..."
kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f -

# 创建 Secrets（如已存在则跳过）
kubectl -n "$NS" get secret evo-secrets 2>/dev/null || \
  kubectl -n "$NS" create secret generic evo-secrets \
    --from-literal=api_key="${EVO_API_KEY:-changeme}" \
    --from-literal=jwt_secret="${EVO_JWT_SECRET:-$(openssl rand -hex 32)}"

# 4. 部署全部资源
echo "[4/4] 部署到 K8s..."
for f in k8s/rbac.yaml k8s/pdb.yaml k8s/network-policy.yaml k8s/hpa.yaml /tmp/evo-deploy.yaml k8s/ingress.yaml; do
    if [ -f "$f" ]; then
        echo "  应用: $f"
        kubectl apply -f "$f"
    fi
done

echo ""
echo "=== 部署完成 ==="
echo "查看状态: kubectl -n $NS get pods"
echo "查看日志: kubectl -n $NS logs -l app=evo-api"
echo "访问地址: https://$DOMAIN"
