"""项目脚手架技能 — 生成模板项目"""
from pathlib import Path

skill_def = {
    "name": "project-scaffold", "version": "1.0.0",
    "description": "快速创建项目脚手架（Django/FastAPI/Vue/React）",
    "author": "AUTO-EVO-AI", "category": "代码", "icon": "🏗️",
    "tags": ["脚手架", "Django", "FastAPI", "Vue", "React"],
    "input_schema": {"type": "object", "properties": {"framework": {"type": "string", "enum": ["django", "fastapi", "vue", "react"]}, "name": {"type": "string"}}},
    "output_schema": {"type": "object", "properties": {"path": {"type": "string"}, "files": {"type": "array"}}}
}

TEMPLATES = {
    "fastapi": {
        "main.py": 'from fastapi import FastAPI\n\napp = FastAPI(title="{name}")\n\n@app.get("/")\ndef root():\n    return {"message": "Hello from {name}"}\n',
        "requirements.txt": "fastapi\nuvicorn\n",
        "README.md": "# {name}\n\nFastAPI project scaffolded by AUTO-EVO-AI\n",
    },
    "django": {
        "manage.py": "#!/usr/bin/env python\n\"\"\"Django's command-line utility\"\"\"\nimport sys\n\ndef main():\n    from django.core.management import execute_from_command_line\n    execute_from_command_line(sys.argv)\n\nif __name__ == '__main__':\n    main()\n",
        "requirements.txt": "django\ndjangorestframework\n",
    },
    "vue": {
        "index.html": "<!DOCTYPE html><html><head><title>{name}</title></head><body><div id='app'></div><script src='https://unpkg.com/vue@3/dist/vue.global.js'></script><script>const app=Vue.createApp({data(){return{msg:'{name}'}}}).mount('#app')</script></body></html>",
        "README.md": "# {name}\n\nVue 3 project\n",
    },
    "react": {
        "index.html": "<!DOCTYPE html><html><head><title>{name}</title></head><body><div id='root'></div><script src='https://unpkg.com/react@18/umd/react.production.min.js'></script><script src='https://unpkg.com/react-dom@18/umd/react-dom.production.min.js'></script><script>ReactDOM.createRoot(document.getElementById('root')).render(React.createElement('h1',null,'{name}'))</script></body></html>",
        "README.md": "# {name}\n\nReact project\n",
    }
}

def execute(params, context=None):
    framework = params.get("framework", "fastapi")
    name = params.get("name", "my-project")
    base = Path(__file__).resolve().parent.parent.parent / "output" / "scaffolds" / name
    base.mkdir(parents=True, exist_ok=True)
    tmpl = TEMPLATES.get(framework, TEMPLATES["fastapi"])
    files = []
    for fname, content in tmpl.items():
        fp = base / fname
        fp.write_text(content.replace("{name}", name), encoding="utf-8")
        files.append(str(fp))
    return {"path": str(base), "files": files}
