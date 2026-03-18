import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.109', username='userk', password='userk1', timeout=10)
sftp = client.open_sftp()
sftp.put(r'C:\Users\sergen\Desktop\j.txt', '/opt/jarvis/knowledge/jarvis_mimari.md')
sftp.close()
client.close()
print('Done!')
