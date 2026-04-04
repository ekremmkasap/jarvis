#!/usr/bin/env python3
"""Simple Gemini chat for testing"""

import os
from pathlib import Path

# Load .env
env_path = Path(".env")
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

import google.genai as genai

# Setup
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# Chat
print("Jarvis Gemini Chat (type 'quit' to exit)")
print("-" * 40)

while True:
    user_input = input("\nSiz: ").strip()

    if user_input.lower() in ["quit", "exit", "cikis"]:
        break

    if not user_input:
        continue

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=user_input
        )
        print(f"Jarvis: {response.text}\n")
    except Exception as e:
        print(f"Hata: {e}\n")
