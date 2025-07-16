import paramiko
import time
import os 

def connect(hostname: str, port: int, username: str, password: str) -> paramiko.SSHClient:
    """
        Establishes an SSH connection to a server.

        Parameters:
            hostname (str): The hostname or IP address of the server.
            port (int): The port number for SSH (usually 22).
            username (str): The username for authentication.
            password (str): The password for authentication.

        Returns:
            paramiko.SSHClient: An SSH client connected to the server.
    """

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    while True:
        try:
            client.connect(hostname, port, username, password)
            break
        except (paramiko.AuthenticationException, paramiko.SSHException):
            time.sleep(10)
            
    print("Connected to the server...")
    return client

def connect_with_key(hostname: str, port: int, username: str, private_key_path: str = None) -> paramiko.SSHClient:
    """
    Establishes an SSH connection to a server using an SSH key.

    Parameters:
        hostname (str): The hostname or IP address of the server.
        port (int): The port number for SSH (usually 22).
        username (str): The username for authentication.
        private_key_path (str): Path to the private key file. Defaults to ~/.ssh/id_rsa if not provided.

    Returns:
        paramiko.SSHClient: An SSH client connected to the server.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if private_key_path is None:
        default_key_path = os.path.expanduser('~/.ssh/id_rsa')
        if not os.path.isfile(default_key_path):
            raise ValueError("Default private key (~/.ssh/id_rsa) not found.")
        private_key_path = default_key_path

    private_key = paramiko.RSAKey.from_private_key_file(private_key_path)

    while True:
        try:
            client.connect(hostname, port, username, pkey=private_key)
            break
        except (paramiko.AuthenticationException, paramiko.SSHException):
            time.sleep(10)
            
    print("Connected to the server using SSH key...")
    return client