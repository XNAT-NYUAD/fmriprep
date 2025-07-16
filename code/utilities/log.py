import os
from .job import check_job_status
import time

def fetch_logs(client, filepath, localpath, password):
    """Fetch logs from remote server using scp."""
    os.system(f"sshpass -p {password} scp {client.get_username()}@{client.get_host()}:{filepath} {localpath}")

def print_new_logs(last_position, localpath):
    """Print only new lines from the log file."""
    with open(localpath, 'r') as f:
        f.seek(last_position)
        new_data = f.read()
        print(new_data, end='')
        return f.tell()  # Return current position in the file

def continuous_fetch_logs(client, job_id, filepath, localpath, password, retry_interval=5):
    last_position = 0

    while True:
        try:
            if check_job_status(client, job_id):
                fetch_logs(client, filepath, localpath, password)
                last_position = print_new_logs(last_position, localpath)
                time.sleep(retry_interval)  # Sleep for a while before fetching logs again
            else:
                print("Job has finished.")
                # Fetch final logs one last time
                fetch_logs(client, filepath, localpath, password)
                print_new_logs(last_position, localpath)
                break

        except Exception as e:
            print(f"Exception while fetching logs: {e}")
            print(f"Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)