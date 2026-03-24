Set WshShell = CreateObject("WScript.Shell")
Set oEnv = WshShell.Environment("PROCESS")
oEnv("OLLAMA_API_KEY") = "ee772cf9b7ac4c0c90fff1de8ce1c61a.IABOZ2BhMZ_4x4J3ojNOczI4"
WshShell.Run "C:\Program Files\Python311\python.exe C:\Users\sergen\Desktop\jarvis-mission-control\server\bridge.py", 0, False
