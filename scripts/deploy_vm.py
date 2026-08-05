import paramiko
import os
import time


def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} must be provided outside the repository")
    return value

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
    hostname = required_env("QODE_VM_HOST")
    username = required_env("QODE_VM_USER")
    key_path = required_env("QODE_VM_KEY_PATH")
    print("Connecting to VM...")
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        hostname,
        username=username,
        key_filename=os.path.expanduser(key_path),
        look_for_keys=False,
        timeout=5,
    )
    print("Connected successfully.")
    
    # Open an interactive shell
    channel = client.invoke_shell()
    
    # Wait for prompt
    time.sleep(2)
    if channel.recv_ready():
        print(channel.recv(4096).decode('utf-8'))
        
    commands = [
        "test -d qode/.git || git clone https://github.com/AlperKartkaya/qode.git qode",
        "git -C qode pull --ff-only",
        "cd qode && chmod +x deploy.sh && ./deploy.sh",
    ]
    
    for cmd in commands:
        run_command_interactive(channel, cmd)
        
    client.close()
    print("Deployment script finished.")

if __name__ == "__main__":
    deploy()
