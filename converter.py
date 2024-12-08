import os
import subprocess
import shutil

CWD = os.getcwd()

def move_files_to_new_folder():
    # List all directories in the current directory (excluding files)
    existing_folders = [f for f in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, f))]

    if existing_folders:
        # Sort existing folders alphabetically before printing
        existing_folders.sort()
        
        print(f"At least one folder exists. Skipping folder creation. Existing folders:")
        for folder in existing_folders:
            print(f"- {folder}")
        new_folder = os.path.join(CWD, existing_folders[0])  # Use the first existing folder
    else:
        # If no folders exist, create a new folder named "temp"
        new_folder = os.path.join(CWD, "temp")
        folder_name = os.path.basename(new_folder)
        os.makedirs(new_folder)
        print(f"Created new folder: '{folder_name}' in '{CWD}'")

    # List all files in the current directory (no directories)
    all_files = [f for f in os.listdir(CWD) if os.path.isfile(os.path.join(CWD, f))]

    if not all_files:
        print("No files found to move.")
        return

    # Sort files alphabetically
    all_files.sort()

    for file in all_files:
        source = os.path.join(CWD, file)
        destination = os.path.join(new_folder, file)

        # Handle potential filename conflicts
        if os.path.exists(destination):
            base, ext = os.path.splitext(file)
            counter = 1
            # Generate a new filename with a counter suffix to avoid overwriting
            while os.path.exists(destination):
                new_name = f"{base}_{counter}{ext}"
                destination = os.path.join(new_folder, new_name)
                counter += 1

        try:
            shutil.move(source, destination)
            print(f"Moved '{file}' to '{folder_name}'")
        except Exception as e:
            print(f"Error moving file '{file}': {e}")


# Function to check for ComicInfo.xml and info.txt existence and copy ComicInfo.xml where necessary
def check_comic_info():
    folder_comicinfo_old = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "ComicInfo.xml")
    
    if not os.path.exists(folder_comicinfo_old):
        print("ComicInfo.xml not found in the 'data' directory.")
        return {}
    
    folder_states = {}
    
    # Walk through directories once to check both files and copy where needed
    for root, subfolder, files in os.walk(CWD):
        subfolder.sort()
        
        for folder in subfolder:
            comicinfo_path = os.path.join(root, folder, "ComicInfo.xml")
            info_path = os.path.join(root, folder, "info.txt")
            
            comicinfo_exists = os.path.exists(comicinfo_path)
            info_found = "Found" if os.path.exists(info_path) else "Not Found"
            
            # Determine folder status
            folder_status = "Complete" if comicinfo_exists else "Incomplete"
            folder_states[folder] = folder_status

            # Print the folder status and info.txt existence
            print(f"Folder: '{folder}' - Status: {folder_status} - info.txt: {info_found}")
            
            # If the folder is incomplete and ComicInfo.xml doesn't exist, copy it from the data folder
            if folder_status == "Incomplete" and not comicinfo_exists:
                folder_comicinfo_new = os.path.join(root, folder, "ComicInfo.xml")
                folder_name = os.path.basename(os.path.join(root, folder))
                try:
                    shutil.copy(folder_comicinfo_old, folder_comicinfo_new)
                    print(f"Folder: '{folder}' is incomplete, copied ComicInfo.xml to {folder_name}")
                except Exception as e:
                    print(f"Error copying file to {folder_name}: {e}")
            else:
                print(f"Folder: '{folder}' is complete, no need to copy ComicInfo.xml.")
    
    return folder_states


def convert(folder_states):
    # Walk through the directory structure
    for root, subfolder, files in os.walk(CWD):
        # Sort the files alphabetically
        files.sort()
        
        folder_name = os.path.basename(root)
        
        if folder_states.get(folder_name) == "Complete":
            print(f"Folder: '{folder_name}' is complete. Skipping image conversion.")
            continue  # Skip this folder and move to the next
        
        elif folder_states.get(folder_name) == "Incomplete":
            print(f"Folder: '{folder_name}' is incomplete. Starting image conversion.")
        
        for filename in files:
            filepath = os.path.join(root, filename)

            # Check if the file is of a valid image type (PNG, AVIF, JPG, WEBP)
            if filename.lower().endswith((".png", ".avif", ".jpg", ".webp")):
                try:
                    print(f"Processing file: {folder_name}/{filename}")
                    
                    # Convert and resize the image
                    command = ['magick', 'mogrify', '-format', 'jpg', '-quality', '100', '-resize', 'x2500', filepath]
                    subprocess.run(command, check=True)
                    print(f"Converted {filename} to JPG and resized it.")
                    
                    # Remove the original file if it was PNG, AVIF, or WEBP
                    if filename.lower().endswith((".png", ".avif", ".webp")):
                        os.remove(filepath)
                        print(f"Removed original file: {filepath}")
                    
                except subprocess.CalledProcessError as e:
                    print(f"Error converting file {filepath}: {e}")
                except Exception as e:
                    print(f"Unexpected error processing file {filepath}: {e}")


# Function to create or rename folders based on the manga title found in "info.txt"
def rename_folders():
    # Walk through all directories to find the 'info.txt' file in the folders
    info_txt_path = None
    for root, subfolder, files in os.walk(CWD):
        # Look for info.txt in each folder
        if "info.txt" in files:
            info_txt_path = os.path.join(root, "info.txt")
            break  # Stop once the first info.txt is found

    if not info_txt_path:
        print("Error: 'info.txt' file not found in any folder.")
        return  # Exit if no info.txt is found
    
    manga_name = ""

    try:
        # Open 'info.txt' and extract the original title
        with open(info_txt_path, 'r') as info_file:
            for line in info_file:
                if "ORIGINAL TITLE:" in line:
                    manga_name = line.split("ORIGINAL TITLE: ", maxsplit=1)[-1].rstrip()  # Extract title
                    break

        if not manga_name:
            print("Error: 'ORIGINAL TITLE' not found in info.txt.")
            return  # Exit if no original title is found

        # List all folders in the current directory and sort them
        folders = [folder for folder in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, folder))]
        folders.sort()

        # Create or rename folders based on manga title
        for i, folder in enumerate(folders, start=1):
            folder_renamed = os.path.join(CWD, f"{manga_name} v{i:02d}")

            # Check if the folder already exists before renaming
            if not os.path.exists(folder_renamed):
                old_folder_path = os.path.join(CWD, folder)
                os.rename(old_folder_path, folder_renamed)
                print(f"Renamed folder '{os.path.relpath(old_folder_path, CWD)}' to '{os.path.relpath(folder_renamed, CWD)}'.")
            else:
                print(f"Folder: '{os.path.relpath(folder_renamed, CWD)}' already exists. Skipping renaming folder.")

    except Exception as e:
        print(f"Error processing 'info.txt': {e}")


# Function to rename image files sequentially
def rename_jpgs(folder_states):
    for root, subfolder, files in os.walk(CWD):
        # Only consider jpg files in the current folder
        jpg_files = [file for file in files if file.lower().endswith(".jpg")]
        jpg_files.sort()

        # Check folder completion status from folder_states
        relative_foldername = os.path.relpath(root, CWD)  # Get the relative path of the folder
        if folder_states.get(relative_foldername) == "Complete":
            print(f"Folder: '{relative_foldername}' is complete. Skipping renaming images.")
            continue  # Skip this folder and move to the next
        
        elif folder_states.get(relative_foldername) == "Incomplete":
            print(f"Folder: '{relative_foldername}' is incomplete. Starting renaming images.")

            # Rename files to a sequential format (e.g., 001.jpg, 002.jpg, etc.)
            for i, image in enumerate(jpg_files):
                old_filepath = os.path.join(root, image)
                new_filename = f"{i:03d}.jpg"  # New name in a 3-digit format
                new_filepath = os.path.join(root, new_filename)

                try:
                    os.rename(old_filepath, new_filepath)
                    print(f"Renamed: {os.path.relpath(old_filepath, CWD)} -> {os.path.relpath(new_filepath, CWD)}")
                except Exception as e:
                    print(f"Error renaming file {os.path.relpath(old_filepath, CWD)}: {e}")


# Function to update metadata in "ComicInfo.xml" based on the folder content and "info.txt"
def metadata():
    metadata_dict = {}
    count_all = 0
    folder_count = 0

    # Iterate through the subdirectories in the current working directory (skip root folder)
    for root, subfolder, files in os.walk(CWD):
        # Skip the root folder, process only subfolders
        if root == CWD:
            continue
        
        # Count the number of non-text, non-xml files
        count_all = 0
        for file_name in files:
            if not (file_name.endswith(".txt") or file_name.endswith(".xml")):
                count_all += 1
        
        # Count the number of subfolders in the current folder
        folder_count = sum(os.path.isdir(os.path.join(CWD, item)) for item in os.listdir(CWD))

        # Define the path to the folder's "info.txt" and "ComicInfo.xml"
        info_txt_path = os.path.join(root, "info.txt")
        comicinfo_path = os.path.join(root, "ComicInfo.xml")
        
        if not os.path.exists(info_txt_path):
            folder_name = os.path.basename(root)
            print(f"Error: 'info.txt' not found in folder: '{folder_name}'. Skipping metadata update.")
            continue

        # Read metadata from the "info.txt" file
        try:
            with open(info_txt_path, 'r') as info_file:
                for line in info_file:
                    if "ORIGINAL TITLE:" in line:
                        metadata_dict["Original_Title"] = line.split("ORIGINAL TITLE: ", maxsplit=1)[-1].rstrip()
                    elif "TITLE:" in line:
                        metadata_dict["Title"] = line.split("TITLE: ", maxsplit=1)[-1].rstrip()
                    elif "ARTIST:" in line:
                        metadata_dict["Artist"] = line.split("ARTIST: ", maxsplit=1)[-1].rstrip()
                    elif "TAGS:" in line:
                        metadata_dict["Tags"] = line.split("TAGS: ", maxsplit=1)[-1].rstrip()
        except Exception as e:
            print(f"Error reading 'info.txt' for {root}: {e}")
            continue

        # Check if ComicInfo.xml exists in the current folder
        if os.path.exists(comicinfo_path):
            try:
                # Read the ComicInfo.xml file to update metadata
                with open(comicinfo_path, 'r') as comic_info_file:
                    lines = comic_info_file.readlines()

                # Update metadata in ComicInfo.xml
                for i, line in enumerate(lines):
                    # Update <Title> and <LocalizedSeries>
                    if "<Title>" in line:
                        lines[i] = f"  <Title>{metadata_dict.get('Original_Title', '')}</Title>\n"
                    elif "<LocalizedSeries>" in line:
                        if metadata_dict.get('Original_Title', '') == metadata_dict.get('Title', ''):
                            lines[i] = "  <LocalizedSeries></LocalizedSeries>\n"  # Empty if both titles are the same
                        else:
                            lines[i] = f"  <LocalizedSeries>{metadata_dict.get('Title', '')}</LocalizedSeries>\n"
                    # Update <Writer> (Artist)
                    elif "<Writer>" in line:
                        lines[i] = f"  <Writer>{metadata_dict.get('Artist', '')}</Writer>\n"
                    # Update <Number> with folder number (last two characters of folder name)
                    elif "<Number>" in line:
                        folder_number = os.path.basename(root)[-2:]  # Extract the last two characters of folder name
                        if folder_number.startswith("0") and len(folder_number) == 2:
                            folder_number = folder_number[1]  # Remove leading zero if any
                        lines[i] = f"  <Number>{folder_number}</Number>\n"
                    # Update <Count> and other fields
                    elif "<Count>" in line:
                        lines[i] = f"  <Count>{folder_count}</Count>\n"
                    elif "<PageCount>" in line:
                        lines[i] = f"  <PageCount>{count_all}</PageCount>\n"
                    elif "<Tags>" in line:
                        lines[i] = f"  <Tags>{metadata_dict.get('Tags', '')}</Tags>\n"                   

                # Write updated content back to ComicInfo.xml
                with open(comicinfo_path, 'w') as comic_info_file:
                    comic_info_file.writelines(lines)

                folder_name = os.path.basename(root)
                print(f"Updated 'ComicInfo.xml' for '{folder_name}'.")
            except Exception as e:
                folder_name = os.path.basename(root)
                print(f"Error processing 'ComicInfo.xml' for '{folder_name}': {e}")
        else:
            folder_name = os.path.basename(root)
            print(f"'ComicInfo.xml' not found in folder '{folder_name}'. Skipping update.")


# Function to update ComicInfo.xml fields like <Number> and <Count>
def check_comicinfo_number_and_count():
    folder_states = {}
    
    # List all directories in the current working directory
    folders = [folder for folder in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, folder))]
    folders.sort()  # Sort folders alphabetically
    
    folder_count = len(folders)
    
    # Iterate through the directories and process ComicInfo.xml
    for folder in folders:
        folder_path = os.path.join(CWD, folder)
        comicinfo_path = os.path.join(folder_path, "ComicInfo.xml")
        
        # Check if ComicInfo.xml exists in the current folder
        if os.path.exists(comicinfo_path):
            try:
                with open(comicinfo_path, 'r') as comicinfo_file:
                    lines = comicinfo_file.readlines()

                # Folder number is extracted from the last two characters of the folder name
                folder_number = folder[-2:]
                if folder_number.startswith("0"):
                    folder_number = folder_number[1]

                # Update the <Number> field with the folder number
                for i, line in enumerate(lines):
                    if "<Number>" in line:
                        lines[i] = f"  <Number>{folder_number}</Number>\n"
                    
                # Update the <Count> field with the total folder count
                for i, line in enumerate(lines):
                    if "<Count>" in line:
                        lines[i] = f"  <Count>{folder_count}</Count>\n"
                
                # Write the updated content back to ComicInfo.xml
                with open(comicinfo_path, 'w') as comicinfo_file:
                    comicinfo_file.writelines(lines)

                print(f"Updated <Number> and <Count> in ComicInfo.xml for '{folder}'")
            except Exception as e:
                print(f"Error updating 'ComicInfo.xml' for {folder}: {e}")
        else:
            print(f"'ComicInfo.xml' not found in folder '{folder}'. Skipping update.")


# Function to delete all "info.txt" files from subfolders
def delete_info():
    for root, subfolder, files in os.walk(CWD):
        for file in files:
            if file == "info.txt":
                try:
                    os.remove(os.path.join(root, file))
                    folder_name = os.path.basename(root)
                    print(f"Deleted '{file}' from '{folder_name}'")
                except Exception as e:
                    print(f"Error deleting file {file}: {e}")


# Function to zip each folder and rename the zip file to .cbz
def zip_and_rename():
    for subfolder in os.listdir(CWD):
        folder_path = os.path.join(CWD, subfolder)
        if os.path.isdir(folder_path):
            zip_name = os.path.basename(folder_path)
            try:
                zip_file = shutil.make_archive(zip_name, format='zip', root_dir=folder_path)
                cbz_file = os.path.join(CWD, f"{zip_name}.cbz")
                os.rename(zip_file, cbz_file)
                print(f"Zipped and renamed: '{zip_name}' -> '{os.path.basename(cbz_file)}'")
            except Exception as e:
                print(f"Error zipping and renaming {folder_path}: {e}")


# Main execution flow
def process_manga():
    move_files_to_new_folder()
    folder_states = check_comic_info()
    convert(folder_states)
    rename_jpgs(folder_states)
    rename_folders()
    metadata()
    check_comicinfo_number_and_count()
    delete_info()
    zip_and_rename()

process_manga()