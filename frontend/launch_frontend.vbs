Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "E:\AUTO-EVO-AI-V0.1"
shell.Run "python E:\AUTO-EVO-AI-V0.1\frontend\serve.py --port 8080", 0, False
