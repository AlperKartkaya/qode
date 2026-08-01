import paramiko
import time

hostname = '34.86.94.186'
username = 'u4865671'
password = 'Hqt4Ch2j2eQHSVLh'

def run_command_interactive(channel, command):
    print(f"Executing: {command}")
    channel.send(command + '\n')
    output = ""
    while True:
        time.sleep(1)
        if channel.recv_ready():
            chunk = channel.recv(4096).decode('utf-8')
            output += chunk
            print(chunk, end='')
            if chunk.strip().endswith('$') or chunk.strip().endswith('#'):
                break
    return output

def deploy():
    print("Connecting to VM...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, username=username, password=password, timeout=5)
    print("Connected successfully.")
    
    # Open an interactive shell
    channel = client.invoke_shell()
    
    # Wait for prompt
    time.sleep(2)
    if channel.recv_ready():
        print(channel.recv(4096).decode('utf-8'))
        
    commands = [
        "rm -rf qode", # Clean slate
        "git clone https://github.com/AlperKartkaya/qode.git",
        "cd qode",
        "cp backend/.env.example backend/.env",
        "chmod +x deploy.sh",
        "./deploy.sh"
    ]
    
    for cmd in commands:
        run_command_interactive(channel, cmd)
        
    client.close()
    print("Deployment script finished.")

if __name__ == "__main__":
    deploy()
