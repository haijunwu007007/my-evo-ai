"""AgentK8s — Agent弹性部署框架（K8s编排+冷启动优化+自动扩缩容）"""
import os, json
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or "sk-e7a7f4e700d847f28027c5608e3f5c02"
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def agentk8s_deploy(agent_name: str = "", image: str = "auto-evo-ai:latest",
                    replicas: int = 2, cpu_limit: str = "1",
                    memory_limit: str = "1Gi", auto_scale: bool = True) -> dict:
    """部署Agent到K8s集群
    Args:
        agent_name: Agent名称
        image: Docker镜像
        replicas: 副本数
        cpu_limit: CPU限制
        memory_limit: 内存限制
        auto_scale: 是否自动扩缩容
    Returns:
        {"success": bool, "yaml": str, "deploy_status": str}
    """
    api_key = os.environ.get("KUBE_CONFIG", "")
    if not api_key:
        # 生成部署清单，让用户手动应用
        yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {agent_name or 'evo-agent'}
  labels:
    app: evo-agent
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: evo-agent
  template:
    metadata:
      labels:
        app: evo-agent
    spec:
      containers:
      - name: agent
        image: {image}
        ports:
        - containerPort: 8765
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: {cpu_limit}
            memory: {memory_limit}
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: evo-secrets
              key: openai_api_key
---
apiVersion: v1
kind: Service
metadata:
  name: evo-agent-svc
spec:
  selector:
    app: evo-agent
  ports:
  - port: 80
    targetPort: 8765
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: evo-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {agent_name or 'evo-agent'}
  minReplicas: {replicas}
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
""" if auto_scale else yaml.split("---apiVersion: autoscaling")[0]

        yaml_path = f"deploy/k8s/{agent_name or 'evo-agent'}-deploy.yaml"
        from pathlib import Path
        Path(yaml_path).parent.mkdir(parents=True, exist_ok=True)
        Path(yaml_path).write_text(yaml, encoding='utf-8')

        return {
            "success": True,
            "yaml": yaml,
            "yaml_path": yaml_path,
            "deploy_status": "清单已生成",
            "next_step": f"运行: kubectl apply -f {yaml_path}"
        }

    return {"success": False, "error": "K8s 配置未就绪，已生成部署清单"}
