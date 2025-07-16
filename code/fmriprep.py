import argparse
import sys
import os 

from utilities import connect_with_key,\
    check_storage,\
    create_work_directory,\
    sync_data_with_key,\
    create_bash_script,\
    submit_job,\
    delete,\
    check_job_status,\
    try_with_infinite_retry,\
    print_log,\
    find_fmriprep_freesurfer_resources_by_subject

import time

def main(workflow_id, run_anat_only, flags, session_label, project_id):
    hostname = "jubail.abudhabi.nyu.edu"
    port = 22
    username = "mri"

    client = None
    job_id = ''
    completed = False
    found_fs = False

    def prepare_input_data():
        global found_fs
        found_fs = find_fmriprep_freesurfer_resources_by_subject(
            xnat_url="http://10.230.12.52",
            username=os.getenv('XNAT_USER'),
            password=os.getenv('XNAT_PASS'),
            project=project_id,
            session=session_label
        )

    def connect_server():
        global client
        client = connect_with_key(hostname=hostname,port=port,username=username,)

    def check_scratch_space():
        global client
        check_storage(client=client)

    def create_workspace():
        global client
        create_work_directory(client=client, username=username, operation_id=workflow_id)

    def send_data():
        global found_fs

        sync_data_with_key(action='send', hostname=hostname, username=username, source='/input', destination= f'/scratch/{username}/{workflow_id}')
        if found_fs:
            sync_data_with_key(action='send', hostname=hostname, username=username, source='/app/freesurfer', destination= f'/scratch/{username}/{workflow_id}/input/')
                
    def send_fs():
        sync_data_with_key(action='send', hostname=hostname, username=username, source='/opt/fs', destination= f'/scratch/{username}/{workflow_id}/license.txt')

    def create_job_script():
        create_bash_script(location=f'/scratch/{username}', workflow_id=workflow_id, anat_only=run_anat_only, flags=flags)

    def send_script():
        sync_data_with_key(action='send',username=username, hostname=hostname, source=f'./{workflow_id}.slurm', destination=f'/home/{username}')

    def run_job():
        global client, job_id
        job_id = submit_job(client=client, script_location=f'/home/{username}/{workflow_id}.slurm')

    def wait_job_finish():
        global client, job_id
        while(check_job_status(client=client, job_id=job_id, method='squeue') and job_id is not None):
            time.sleep(120)

    def get_output_data():
        global client,completed,job_id  
        sync_data_with_key(action='get', hostname=hostname, username=username, source=f'/home/{username}/slurm-{workflow_id}.out', destination=f'/temp_files',output=False)
        sync_data_with_key(action='get', hostname=hostname, username=username, source=f'/home/{username}/slurm-{workflow_id}.err', destination=f'/temp_files',output=False)
        completed = check_job_status(client=client, job_id=job_id)
        print(f"_________________________________________________________\n")
        print_log(f'/temp_files/slurm-{workflow_id}.out')
        
        if completed:
            sync_data_with_key(action='get', hostname=hostname, username=username, source=f'/scratch/{username}/{workflow_id}/fmriprep/*', destination=f'/fmriprep', output=False)
            # Empty fmriprep directory before copying new data
            sync_data_with_key(action='get', hostname=hostname, username=username, source=f'/scratch/{username}/{workflow_id}/freesurfer/*', destination=f'/freesurfer', output=False)
        else:
            print(f"_________________________________________________________\n")
            print_log(f'/temp_files/slurm-{workflow_id}.err')
            print(f"_________________________________________________________\n")
    
    def clean_up():
        global client, completed
        delete(client=client, username=username, path=f'/scratch/{username}/{workflow_id}')
        delete(client=client, username=username, path=f'/home/{username}/{workflow_id}.slurm')
        delete(client=client, username=username, path=f'/home/{username}/slurm-{workflow_id}.out')
        delete(client=client, username=username, path=f'/home/{username}/slurm-{workflow_id}.err')
        client.close(),
        if not completed:
            sys.exit(1)

    steps = [
            ("Prepare input data, its may take a few minutes", prepare_input_data),
            ("Connect to cluster", connect_server),
            ("Check scratch space", check_scratch_space),
            ("Create operation directory", create_workspace),
            ("Move /input directory into operation directory ", send_data),
            ("Move fs license into operation directory ", send_fs),
            ("Create job script", create_job_script),
            ("Move submit script into cluster", send_script),
            ("Submit job", run_job),
            ("Waiting job finish",wait_job_finish),
            ("Get output data from cluster", get_output_data),
            ("Clean up operation files", clean_up)
        ]
    
    for step_name, step_func in steps:
        print(f"Executing step: {step_name}")
        try_with_infinite_retry(step_func)    


def str_to_bool(value: str) -> bool:
    """Convert string input to a boolean value."""
    if value.lower() in ('true', 't', '1'):
        return True
    elif value.lower() in ('false', 'f', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError(f"Invalid boolean value: '{value}'. Use 'true' or 'false'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run FMRIPrep in Jubail cluster.')

    parser.add_argument('--flags', type=str, help="Command to run. Use 'run' to run FMRIPrep.")
    parser.add_argument('--anat-only', type=str_to_bool, help="Run FMRIPrep only for anatomical data. Use 'true' or 'false'.")
    parser.add_argument('--session-label', type=str, help="Session label to process, e.g., 'Subject_0017_ses_01'.")
    parser.add_argument('--project-id', type=str, help="Project label to process, e.g., 'NYU_HBN'.")

    args = parser.parse_args()

    workflow_id = os.getenv('XNAT_WORKFLOW_ID')
    if workflow_id is None:
        print("Error: XNAT_WORKFLOW_ID environment variable is not set.")
    elif args.session_label is None:
        print("Error: Session label is required.")
    else:

        # Call the main function with processed arguments
        main(
            workflow_id,
            args.anat_only,
            args.flags,
            args.session_label,
            args.project_id
        )
