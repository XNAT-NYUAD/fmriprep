import re
from paramiko import SSHClient
from typing import Callable, Any
import time

def submit_job(client: SSHClient, script_location: str) -> str:
    """
    Submit a job to a remote scheduler using the sbatch command.

    Parameters:
    - client (SSHClient): An established SSHClient instance to execute commands on the remote server.
    - script_location (str): The path to the script on the remote server that you want to submit using sbatch.

    Returns:
    - str: The job ID obtained from the sbatch command.
    """
    
    stdin, stdout, stderr = client.exec_command(f"/opt/slurm/default/bin/sbatch {script_location}")
    
    # Read the output
    output = stdout.read().decode('utf-8').strip()
    
    # Extract the job ID from the output using regular expressions
    match = re.search(r"(\d+)$", output)
    job_id = match.group(1) if match else None
    print(output)

    # Optionally, you can also read the error stream if desired.
    error_output = stderr.read().decode('utf-8').strip()
    if error_output:
        print(f"Error occurred: {error_output}")

    return job_id

def check_job_status(client: SSHClient, job_id: str, method: str ='sacct') -> bool:
    """
    Check the status of a specific job on a remote scheduler.

    Parameters:
    - client (SSHClient): An established SSHClient instance to execute commands on the remote server.
    - job_id (str): The job ID you want to check the status for.
    - method (str): The method to be used to check the job status. Default is 'sacct'.

    Returns:
    - bool: based on the method if use squeue return True if job is running else False, otherwise if the method is sacct return False if job not completed else True
    """
    if method == 'squeue':
        stdin, stdout, stderr = client.exec_command(f"/opt/slurm/default/bin/{method} -j {job_id}")
        output = stdout.read().decode('utf-8')
        lines = output.splitlines()
        if len(lines) > 1:
            return True
        else:
            return False

    elif method == 'sacct':
        command = f"/opt/slurm/default/bin/{method} -j {job_id} -o state | grep 'FAILED'"
        stdin, stdout, stderr = client.exec_command(command)

        # Read the output from the command
        output = stdout.read().decode('utf-8').strip()

        # Check if the output contains any lines indicating a FAILED state
        if output:
            print('Error occurred during job execution: Job failed!')
            return False

        # If no FAILED states are found, we assume all jobs are completed successfully
        print('Job completed successfully!')
        return True
      
def try_with_infinite_retry(func: Callable[..., Any], delay: int = 20) -> Any:
    """
    Retry executing a function indefinitely in case of exceptions.

    Parameters:
        func (Callable[..., Any]): The function to be executed.
        delay (int, optional): The delay in seconds between retries. Default is 20.

    Returns:
        Any: The return value of the function.

    Raises:
        Exception: If the function continues to raise exceptions after retries.
    """
    while True:
        try:
            return func()
        except Exception as e:
            time.sleep(delay)


def create_bash_script(location: str, workflow_id: str, anat_only: bool, flags: str = '') -> None:
    """
    Creates a bash script file with predefined content.

    Parameters:
    - location (str): The location where the input and output directories are located.
    - workflow_id (str): Unique operation ID to be embedded in the script.
    - anat_only (bool): If True, add the --anat-only flag to the command.
    - flags (str): Additional flags to be included in the command. Can be empty.

    Returns:
    - None
    """

    # Determine the anat-only flag based on anat_only
    anat_flag = '--anat-only' if anat_only else ''

    # List of existing flags in the command
    existing_flags = {
        '--skip_bids_validation', 
        '--fs-license-file', 
        '--anat-only'
    }

    # Filter out existing flags from the input flags string if flags are not empty
    filtered_flags = ' '.join(
        flag for flag in flags.split() if flag not in existing_flags
    ) if flags else ''

    content = f"""#!/bin/bash -l

#SBATCH -n 1
#SBATCH -c 16
#SBATCH -a 1
#SBATCH -t 16:00:00
#SBATCH -o slurm-{workflow_id}.out
#SBATCH -e slurm-{workflow_id}.err

# Load FMRIPrep module
module load singularity
SINGULARITY_IMG=/scratch/mri/singularityimages/fmriprep_24.1.1.sif
export TEMPLATEFLOW_HOME='/scratch/mri/.cache/templateflow'

export SINGULARITYENV_FS_LICENSE='{location}/{workflow_id}/license.txt'

WORKDIR='{location}/{workflow_id}'
INPUT_DIR='{location}/{workflow_id}/input'

FREESURFER_OUTPUT_DIR='{location}/{workflow_id}/freesurfer'
FMRIPREP_OUTPUT_DIR='{location}/{workflow_id}/fmriprep'

# Check if input/freesurfer exists and copy it, otherwise create empty directory
if [ -d "${{INPUT_DIR}}/freesurfer" ]; then
    cp -r "${{INPUT_DIR}}/freesurfer" "${{FREESURFER_OUTPUT_DIR}}"
else
    mkdir -p "${{FREESURFER_OUTPUT_DIR}}"
fi

# Create fmriprep output directory if it doesn't exist
mkdir -p "${{FMRIPREP_OUTPUT_DIR}}"

singularity run --cleanenv \\
    -B "${{INPUT_DIR}}":/data:ro \\
    -B "${{FMRIPREP_OUTPUT_DIR}}":/fmriprep \\
    -B "${{WORKDIR}}":/work \\
    -B "${{FREESURFER_OUTPUT_DIR}}":/freesurfer \\
    "${{SINGULARITY_IMG}}" \\
    /data /fmriprep participant \\
    --fs-subjects-dir /freesurfer \\
    --work-dir /work \\
    --skip_bids_validation \\
    --output-space T1w:res-native fsnative:den-41k fsaverage:den-41k \\
    --nthreads 16 \\
    --no-submm-recon \\
    {anat_flag} \\
    {filtered_flags}
    """

    file_name = f'{workflow_id}.slurm'

    with open(file_name, 'w') as file:
        file.write(content)

    print(f"File '{file_name}' has been created!")
