import xnat
import re
import os
import shutil

# Define the regex pattern to extract the directory path
pattern = r'^(freesurfer/.+)/[^/]+\.[^/]+$'
# Set the default input directory
input_dir = '/app'

def find_fmriprep_freesurfer_resources_by_subject(xnat_url: str, username: str = None, password: str = None, project: str = None, session: str = None):
    if not project:
        print("Error: Project ID is required")
        return False
        
    try:
        with xnat.connect(xnat_url, user=username, password=password) as connection:
            project_obj = connection.projects[project]

            if not session:
                print("Error: Session ID is required")
                return False

            try:
                experiments = project_obj.experiments.values()
                session_obj = None
                
                for experiment in experiments:
                    if experiment.label == session:
                        session_obj = experiment
                        break
                
                if not session_obj:
                    print(f"Error: Session {session} not found in project")
                    return False

            except Exception as e:
                print(f"Error accessing session {session}: {str(e)}")
                return False

            print(f"\nExploring Resources for Session: {session}")
            print("-" * 50)
            
            session_resources = session_obj.resources.values()
            
            for resource in session_resources:
                if 'freesurfer' in resource.label.lower():
                    target_dir = os.path.join(input_dir, 'freesurfer')
                    os.makedirs(target_dir, exist_ok=True)
                    
                    # Get all files in the resource
                    for file in resource.files.values():
                        # Get the file path relative to the resource
                        file_path = file.path
                        
                        # Remove any potential 'files/' prefix and get just the nested path
                        clean_path = file_path.split('files/')[-1] if 'files/' in file_path else file_path
                        
                        # Create the target path
                        target_path = os.path.join(target_dir, clean_path)
                        
                        # Create directory structure
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        
                        # Download file using stream to handle large files
                        print(f"Downloading: {clean_path}")
                        with open(target_path, 'wb') as f:
                            file.download_stream(f)
                    
                    print(f"Copied freesurfer resources for session: {session}")
                    print(f"Contents of /app directory: {os.listdir(input_dir)}")
                    return True

            print(f"No freesurfer resources found for session: {session}")
            return False

    except Exception as e:
        print(f"Error accessing XNAT: {str(e)}")
        return False
