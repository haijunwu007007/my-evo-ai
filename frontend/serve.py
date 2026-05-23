"""AUTO-EVO-AI V0.1 — 独立前端开发服务器

独立运行前端，通过 CORS 调用后端 API。
用法: python frontend/serve.py [--port 8081] [--api http://127.0.0.1:8765]
"""
import argparse, http.server, json, os, sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent

class FrontendHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, api_url="http://127.0.0.1:8765", **kwargs):
        self.api_url = api_url
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api-config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"api_url": self.api_url}).encode())
            return
        return super().do_GET()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

def main():
    parser = argparse.ArgumentParser(description="EVO Frontend Dev Server")
    parser.add_argument("--port", type=int, default=8081, help="前端端口")
    parser.add_argument("--api", default="http://127.0.0.1:8765", help="后端API地址")
    args = parser.parse_args()

    server = http.server.HTTPServer(("127.0.0.1", args.port),
        lambda *a: FrontendHandler(*a, api_url=args.api))
    print(f"前端独立服务器: http://127.0.0.1:{args.port}")
    print(f"后端API地址: {args.api}")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

if __name__ == "__main__":
    main()
