"""Java项目自动检测→构建→部署"""
import os, subprocess, json, re, shutil

def detect_java_type(project_dir):
    """检测Java项目类型和构建工具"""
    if not os.path.isdir(project_dir):
        return {"type": "unknown", "build_tool": "none", "has_java": False}
    files = set(os.listdir(project_dir))
    result = {"type": "unknown", "build_tool": "none", "has_java": False,
              "spring_boot": False, "framework": "none", "jdk_version": "11"}
    # 检测构建工具
    if "pom.xml" in files:
        result["build_tool"] = "maven"
        result["type"] = "maven"
        with open(os.path.join(project_dir, "pom.xml"), "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            if "<spring-boot" in content or "<springframework.boot" in content:
                result["spring_boot"] = True
                result["framework"] = "spring-boot"
            if "<java.version>" in content:
                m = re.search(r"<java\.version>(\d+)", content)
                if m: result["jdk_version"] = m.group(1)
    elif "build.gradle" in files or "build.gradle.kts" in files:
        result["build_tool"] = "gradle"
        result["type"] = "gradle"
        gf = "build.gradle" if "build.gradle" in files else "build.gradle.kts"
        with open(os.path.join(project_dir, gf), "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            if "spring" in content.lower():
                result["spring_boot"] = True
                result["framework"] = "spring-boot"
    elif "build.xml" in files:
        result["build_tool"] = "ant"
        result["type"] = "ant"
    # 检测是否有Java文件
    java_files = []
    for root, dirs, fs in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "__pycache__", "target", "build", ".gradle")]
        java_files.extend(f for f in fs if f.endswith(".java"))
    result["has_java"] = len(java_files) > 0
    result["java_file_count"] = len(java_files)
    if not result["build_tool"] and result["has_java"]:
        result["build_tool"] = "manual"
        result["type"] = "java-source"
    return result

def auto_build_java(project_dir, output_dir=None):
    """自动构建Java项目"""
    info = detect_java_type(project_dir)
    if not info["has_java"] and info["build_tool"] == "none":
        return {"ok": False, "data": "未检测到Java项目"}
    if output_dir is None:
        output_dir = os.path.join(project_dir, "target")
    os.makedirs(output_dir, exist_ok=True)
    try:
        if info["build_tool"] == "maven":
            r = subprocess.run(["mvn", "package", "-DskipTests", "-q"],
                             cwd=project_dir, capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                jars = [f for f in os.listdir(os.path.join(project_dir, "target")) if f.endswith(".jar")]
                return {"ok": True, "data": f"Maven构建成功: {jars}", "jar": jars}
            return {"ok": False, "data": f"Maven失败: {r.stderr[-200:]}"}
        elif info["build_tool"] == "gradle":
            r = subprocess.run(["gradle", "build", "-x", "test", "-q"],
                             cwd=project_dir, capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                jars = [f for f in os.listdir(os.path.join(project_dir, "build", "libs")) if f.endswith(".jar")]
                return {"ok": True, "data": f"Gradle构建成功: {jars}", "jar": jars}
            return {"ok": False, "data": f"Gradle失败: {r.stderr[-200:]}"}
        else:
            return {"ok": False, "data": f"纯Java源码项目: {info['java_file_count']}个文件，需要创建构建脚本"}
    except FileNotFoundError:
        return {"ok": False, "data": f"未找到{info['build_tool']}命令，请先安装"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "data": "构建超时(>5分钟)"}

def create_build_script(project_dir, info):
    """为无构建工具的Java项目生成pom.xml"""
    if info["type"] != "java-source":
        return {"ok": False, "data": "已有构建工具，无需创建"}
    pom = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.evo</groupId>
  <artifactId>auto-project</artifactId>
  <version>1.0</version>
  <properties><maven.compiler.source>11</maven.compiler.source>
    <maven.compiler.target>11</maven.compiler.target></properties>
</project>"""
    with open(os.path.join(project_dir, "pom.xml"), "w") as f:
        f.write(pom)
    return {"ok": True, "data": "pom.xml已生成，请执行 mvn package"}
