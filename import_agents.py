import os, glob, shutil
src = r'c:\Users\sergen\Desktop\Yeni klasör\agency-agents_real'
dst = r'c:\Users\sergen\Desktop\jarvis-mission-control\server\agent_prompts'
os.makedirs(dst, exist_ok=True)
count = 0
for root, _, files in os.walk(src):
    for f in files:
        if f.endswith('.md') and f.lower() not in ['readme.md', 'contributing.md']:
            shutil.copy2(os.path.join(root, f), os.path.join(dst, f))
            count += 1
print(f'Basariyla {count} adet ajan rolu eklendi!')
