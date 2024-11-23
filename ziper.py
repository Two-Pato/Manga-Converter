import os
import shutil

# Root folder path
root_folder = os.getcwd()  # Current Working Directory

# Function to zip folders and rename them to .cbz
def zip_and_rename_folders():
    for sub_folder in os.listdir(root_folder):
        sub_folder_path = os.path.join(root_folder, sub_folder)
        if os.path.isdir(sub_folder_path):
            for folder_name in os.listdir(sub_folder_path):
                folder_path = os.path.join(sub_folder_path, folder_name)
                
                # Check if it's a folder (i.e., extracted folder)
                if os.path.isdir(folder_path):
                    cbz_file = os.path.join(sub_folder_path, folder_name + '.cbz')
                    
                    # Create a .zip archive of the folder
                    try:
                        shutil.make_archive(cbz_file.replace('.cbz', ''), 'zip', folder_path)
                        print(f"Zipped {folder_path} to {cbz_file}")
                    except Exception as e:
                        print(f"Error creating zip file for {folder_path}: {e}")
                    
                    # Rename the .zip file to .cbz (move operation)
                    zip_file = cbz_file.replace('.cbz', '.zip')
                    try:
                        os.rename(zip_file, cbz_file)
                        print(f"Renamed {zip_file} to {cbz_file}")
                    except OSError as e:
                        print(f"Error renaming file {zip_file} to {cbz_file}: {e}")

                    # Optionally, remove the extracted folder after zipping it
                    try:
                        shutil.rmtree(folder_path)
                        print(f"Removed the extracted folder {folder_path}")
                    except OSError as e:
                        print(f"Error removing folder {folder_path}: {e}")

# Run the combined function
zip_and_rename_folders()
