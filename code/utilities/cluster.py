from paramiko.client import SSHClient
import os
from typing import Optional
import re
import subprocess
import re
import sys


def _get_scratch_space(client: SSHClient) -> Optional[int]:
    """
    Gets the used space percentage for the /scratch filesystem using the myquota command.

    Parameters:
    - client (SSHClient): An established SSHClient instance to execute commands on the remote server.

    Returns:
    - Optional[int]: Returns the used space percentage as an integer if found, otherwise returns None.

    Raises:
    - This function may raise exceptions related to SSH command execution, though they aren't explicitly caught here.
    """
    stdin, stdout, stderr = client.exec_command("myquota")
    output = stdout.readlines()

    for line in output:
        if "/scratch" in line:
            space_info = line.split()
            
            if len(space_info) < 4:
                continue
            
            match = re.search(r'\((\s*\d+)%\)', line)
            
            if match:
                used_space_percentage = int(match.group(1))
                return used_space_percentage
            else:
                print(f"Unexpected line: {line}")
                continue

    return None


def create_work_directory(client: SSHClient, username: str, operation_id: str) -> None:
    """
    Creates a directory in the /scratch/ filesystem on the remote server. 
    If the directory already exists, it's removed and recreated.

    Parameters:
    - client (SSHClient): An established SSHClient instance to execute commands on the remote server.
    - username (str): The username corresponding to the desired directory structure.
    - operation_id (str): The operation ID corresponding to the desired directory structure.

    Returns:
    - None: The function returns nothing but has side effects on the remote server.

    Raises:
    - This function may raise exceptions related to SSH command execution, though they aren't explicitly caught here.
    """

    stdin, stdout, stderr = client.exec_command(f"test -d /scratch/{username}/{operation_id} && echo 'exists'")
    directory_check = directory_check = stdout.read().decode('utf-8').strip()
    if directory_check == "exists":
        client.exec_command(f"rm -rf /scratch/{username}/{operation_id}")
        print(f"Removed existing directory /scratch/{username}/{operation_id}")

    stdin, stdout, stderr = client.exec_command(f"mkdir -p /scratch/{username}/{operation_id}/input")
    print(f"Created directory /scratch/{username}/{operation_id}/input")

def delete(client: SSHClient, username: str, path: str) -> None:
    """
    Deletes a directory or file in the /scratch/ filesystem on the remote server. 
    If the path doesn't exist, the function does nothing.

    Parameters:
    - client (SSHClient): An established SSHClient instance to execute commands on the remote server.
    - username (str): The username corresponding to the desired directory structure.
    - path (str): The path corresponding to the desired directory or file.

    Returns:
    - None: The function returns nothing but has side effects on the remote server.

    Raises:
    - This function may raise exceptions related to SSH command execution, though they aren't explicitly caught here.
    """
    stdin, stdout, stderr = client.exec_command(f"[ -d {path} ] && echo 'directory' || echo 'file' ")
    check = stdout.read().decode('utf-8').strip()
    
    if check == "directory":
        client.exec_command(f"rm -rf {path}")
        print(f"Removed directory {path}")
    elif check == "file":
        client.exec_command(f"rm {path}")
        print(f"Removed file {path}")
    else:
        print(f"Path {path} does not exist or is neither a directory nor a file. Nothing to delete.")



def sync_data(action: str, username: str, password: str, hostname: str, source: str, destination: str, retry_delay: int = 10) -> Optional[str]:
    """
    Uses rsync to sync data between local and remote hosts. Can either send data to or get data from a remote server.

    Parameters:
    - action (str): Action to perform, either "send" or "get".
    - username (str): Username on the remote host.
    - hostname (str): IP address or hostname of the remote server.
    - source (str): Source path for the data (depends on the action).
    - destination (str): Destination path for the data (depends on the action).

    Returns:
    - Optional[str]: Returns error message if there's an error, otherwise None.
    """
    
    ssh_command = f"sshpass -p {password} ssh -o StrictHostKeyChecking=no"
    
    if action == "send":
        if not os.path.exists(source):
            error_message = f"The provided source '{source}' does not exist."
            raise Exception(error_message)
        remote_path = f"{username}@{hostname}:{destination}"
        rsync_command = ["rsync", "-av", "-e", ssh_command, source, remote_path]
    elif action == "get":
        if not os.path.exists(destination):
            error_message = f"The provided destination '{destination}' does not exist."
            raise Exception(error_message)
        rsync_command = ["rsync", "-avz", "-e", ssh_command, f"{username}@{hostname}:{source}", destination]
    else:
        error_message = "Invalid action specified. Choose either 'send' or 'get'."
        print(error_message)
        return error_message
    
    try:
        rsync_result = subprocess.run(rsync_command, capture_output=True, text=True, check=True)
        print(rsync_result.stdout)
        if action == "send":
            print(f"Data copied successfully to {remote_path}!")
        else:
            print(f"Data retrieved successfully to {destination}!")

        return None
    
    except subprocess.CalledProcessError as e:
        pass

def     sync_data_with_key(action: str, username: str, hostname: str, source: str, destination: str, output: bool = True) -> Optional[str]:
    """
    Uses rsync with SSH key authentication to sync data between local and remote hosts.
    Can either send data to or get data from a remote server.

    Parameters:
    - action (str): Action to perform, either "send" or "get".
    - username (str): Username on the remote host.
    - private_key_path (str): Path to the SSH private key file.
    - hostname (str): IP address or hostname of the remote server.
    - source (str): Source path for the data (depends on the action).
    - destination (str): Destination path for the data (depends on the action).
    - output (bool): Whether to print the output of the rsync command. Default is True.

    Returns:
    - An optional boolean flag indicating the presence of an error. If an error occurs, it returns True; otherwise, it returns False.
    """
    
    ssh_command = f"ssh -i /amrshadid/.ssh/id_rsa -o StrictHostKeyChecking=no"

    if action == "send":
        if not os.path.exists(source):
            error_message = f"The provided source '{source}' does not exist."
            raise Exception(error_message)
        remote_path = f"{username}@{hostname}:{destination}"
        print(remote_path)
        rsync_command = ["rsync", "-av", "-e", ssh_command, source, remote_path]
    elif action == "get":
        if not os.path.exists(destination):
            error_message = f"The provided destination '{destination}' does not exist."
            raise Exception(error_message)
        rsync_command = ["rsync", "-avz", "-e", ssh_command, f"{username}@{hostname}:{source}", destination]
    else:
        error_message = "Invalid action specified. Choose either 'send' or 'get'."
        print(error_message)
        raise Exception(error_message)
    
    try:
        rsync_result = subprocess.run(rsync_command, capture_output=True, text=True, check=True)

        if output:
            print(rsync_result.stdout)

            if action == "send":
                print(f"Data copied successfully to {remote_path}!")
            else:
                print(f"Data retrieved successfully to {destination}!")
        
        return True
    
    except subprocess.CalledProcessError as e:
        return False

def print_log(log_path):
    """
    Prints the content of a log file to the console while preserving its original format.

    Args:
    - log_path (str): The path to the log file.

    Returns:
    - None

    Raises:
    - FileNotFoundError: If the specified log file is not found.
    - Exception: For any other unforeseen errors during file reading.
    """
    try:
        with open(log_path, 'r') as log_file:
            log_content = log_file.read()
            
            print(log_content, end='') 
    except FileNotFoundError:
        print(f"Log file '{log_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    

def check_storage(client: SSHClient) -> None:
    """
    Checks the usage of the /scratch space on the server.

    Parameters:
        client (SSHClient): An SSH client connected to the server.

    Returns:
        None
    """
    used_percentage = _get_scratch_space(client)
    
    if used_percentage is None:
        print("Could not fetch the /scratch space info.")
        client.close()
        sys.exit(1)
    elif used_percentage >= 100:
        print("/scratch space is full. Exiting the program.")
        client.close()
        sys.exit(1)
    else:
        print("/scratch has enough space. Proceeding...")