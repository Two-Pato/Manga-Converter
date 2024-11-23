import os
import shutil

# Root folder path
root_folder = os.getcwd()  # Current Working Directory

# Rename .cbz files to .zip in every folder within the root folder
def rename_and_unzip_files():
    for sub_folder in os.listdir(root_folder):
        sub_folder_path = os.path.join(root_folder, sub_folder)
        if os.path.isdir(sub_folder_path):
            for file_name in os.listdir(sub_folder_path):
                if file_name.endswith('.cbz'):
                    original_file = os.path.join(sub_folder_path, file_name)
                    new_file = os.path.join(sub_folder_path, file_name.replace('.cbz', '.zip'))

                    # Rename the .cbz file to .zip using shutil.move
                    try:
                        shutil.move(original_file, new_file)
                        print(f"Renamed {original_file} to {new_file}")
                    except OSError as e:
                        print(f"Error renaming file {original_file} to {new_file}: {e}")

                    # Unzip the newly renamed .zip file using shutil.unpack_archive
                    unzip_folder = os.path.join(sub_folder_path, file_name.replace('.cbz', ''))
                    if not os.path.exists(unzip_folder):
                        os.makedirs(unzip_folder)

                    try:
                        shutil.unpack_archive(new_file, unzip_folder)
                        print(f"Unzipped {new_file} to {unzip_folder}")
                    except shutil.ReadError as e:
                        print(f"Error unzipping file {new_file}: {e}")

                    # Remove the old .zip file after unzipping
                    try:
                        os.remove(new_file)
                        print(f"Removed the old zip file {new_file}")
                    except OSError as e:
                        print(f"Error removing file {new_file}: {e}")

# Run the combined function
rename_and_unzip_files()
