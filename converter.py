import os
import subprocess
import shutil
import re


# Define ANSI escape codes for colors
BLUE = '\033[34m'  # Color for "folders"
ORANGE = '\033[38;5;214m' # Color for "files"
YELLOW = '\033[33m' # Color for "state"
GREEN = '\033[32m'
RED = '\033[31m' # Color for "error"
RESET = '\033[0m'


CWD = os.getcwd()


def move_files_to_new_folder():
    # List all directories in the current directory (excluding files)
    directories = [directory for directory in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, directory))]

    if directories:
        directories.sort()

        print(f"At least one folder exists. Skipping folder creation. Existing folders:")
        for directory in directories:
            print(f"- {BLUE}{directory}{RESET}")
        target_directory = os.path.join(CWD, directories[0])  # Use the first existing directory
    else:
        # If no directory exist, create a new directory named "temp"
        target_directory = os.path.join(CWD, "temp")
        os.makedirs(target_directory)
        print(f"Created new folder: {BLUE}'{os.path.basename(target_directory)}'{RESET} in {BLUE}'{os.path.basename(CWD)}'{RESET}")

    # List all files in the current directory (no directories)
    files = [f for f in os.listdir(CWD) if os.path.isfile(os.path.join(CWD, f))]

    if not files:
        print("No files found to move.")
        return

    # Sort files alphabetically
    files.sort()
    
    for file in files:
        source = os.path.join(CWD, file)
        destination = os.path.join(target_directory, file)

        # Handle potential filename conflicts
        if os.path.exists(destination):
            base, ext = os.path.splitext(file)
            counter = 1
            # Generate a new filename with a counter suffix to avoid overwriting
            while os.path.exists(destination):
                file_name_new = f"{base}_{counter}{ext}"
                destination = os.path.join(target_directory, file_name_new)
                counter += 1

        try:
            shutil.move(source, destination)
            print(f"Moved {ORANGE}'{file}'{RESET} to {BLUE}'{os.path.basename(target_directory)}'{RESET}")
        except Exception as e:
            print(f"{RED}Error moving file '{file}': {e}{RESET}")


# Function to check for ComicInfo.xml and info.txt existence and copy ComicInfo.xml where necessary
def check_comicinfo():
    comicinfo_source_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "ComicInfo.xml")

    if not os.path.exists(comicinfo_source_path):
        print(f"{RED}ComicInfo.xml not found in the 'data' directory.{RESET}")
        return {}

    directories_states ={}

    # Walk through directories once to check both files and copy where needed
    for root, directories, files in os.walk(CWD):
        directories.sort()

        for directory in directories:
            comicinfo_path = os.path.join(root, directory, "ComicInfo.xml")
            info_path = os.path.join(root, directory, "info.txt")

            comicinfo_exists = os.path.exists(comicinfo_path)
            info_found = "Found" if os.path.exists(info_path) else "Not Found"

            # Determine folder status
            directory_status = "Complete" if comicinfo_exists else "Incomplete"
            directories_states[directory] = directory_status

            # Print the folder status and info.txt existence
            print(f"Folder: {BLUE}'{directory}'{RESET} - Status: {YELLOW}{directory_status}{RESET} - info.txt: {YELLOW}{info_found}{RESET}")

            # If the folder is incomplete and ComicInfo.xml doesn't exist, copy it from the data folder
            if directory_status == "Incomplete" and not comicinfo_exists:
                comicinfo_target_path = os.path.join(root, directory, "ComicInfo.xml")
                try:
                    shutil.copy(comicinfo_source_path, comicinfo_target_path)
                    print(f"Folder: {BLUE}'{directory}'{RESET} is incomplete, copied ComicInfo.xml to {BLUE}'{os.path.basename(os.path.join(root, directory))}'{RESET}")
                except Exception as e:
                    print(f"{RED}Error copying file to '{os.path.basename(os.path.join(root, directory))}': {e}{RESET}")
            else:
                print(f"Folder: {BLUE}'{directory}'{RESET} is complete, no need to copy ComicInfo.xml.")

    return directories_states


# Function to convert all images to JPG
def convert_images(directories_states):
    for root, directories, files in os.walk(CWD):
        files.sort()

        directory = os.path.basename(root)

        if directories_states.get(directory) == "Complete":
            print(f"Folder: {BLUE}'{directory}'{RESET} is complete. Skipping image conversion.")
            continue  # Skip this folder and move to the next

        elif directories_states.get(directory) == "Incomplete":
            print(f"Folder: {BLUE}'{directory}'{RESET} is incomplete. Starting image conversion.")

        for image in files:
            image_path = os.path.join(root, image)

            # Check if the file is of a valid image type (PNG, AVIF, JPG, WEBP)
            if image.lower().endswith((".png", ".avif", ".jpg", ".webp")):
                try:
                    print(f"Processing image: {BLUE}'{directory}'{RESET}/{ORANGE}'{image}'{RESET}")

                    # Convert and resize the image
                    command = ['magick', 'mogrify', '-format', 'jpg', '-quality', '100', '-resize', 'x2500', image_path]
                    subprocess.run(command, check=True)
                    print(f"Converted {ORANGE}'{image}'{RESET} to JPG and resized it.")

                    # Check if JPG was created and remove the original if needed
                    image_path_new = os.path.splitext(image_path)[0] + '.jpg'
                    if os.path.exists(image_path_new):
                        if image.lower().endswith((".png", ".avif", ".webp")):
                            os.remove(image_path)
                            print(f"Removed original file: {ORANGE}'{image}'{RESET}")
                    else:
                        print(f"{RED}JPG conversion failed for '{image}'. Skipping removal.{RESET}")

                except subprocess.CalledProcessError as e:
                    print(f"{RED}Error converting image '{image}': {e}{RESET}")
                except Exception as e:
                    print(f"{RED}Unexpected error processing file '{image}': {e}{RESET}")


# Function to create or rename directories based on the manga title found in "info.txt"
def rename_directories():
    # Walk through all directories to find the 'info.txt' file
    info_path = None
    for root, directories, files in os.walk(CWD):
        if "info.txt" in files:
            info_path = os.path.join(root, "info.txt")
            break  # Stop once the first info.txt is found

    if not info_path:
        print(f"{RED}Error: 'info.txt' file not found in any folder.{RESET}")
        return  # Exit if no info.txt is found

    manga_title = ""

    try:
        # Open 'info.txt' and extract the original title
        with open(info_path, 'r') as info_file:
            for line in info_file:
                if "ORIGINAL TITLE:" in line:
                    manga_title = line.split("ORIGINAL TITLE: ", maxsplit=1)[-1].rstrip()  # Extract title
                    break

        if not manga_title:
            print(f"{RED}Error: 'ORIGINAL TITLE' not found in info.txt.{RESET}")
            return  # Exit if no original title is found

        # List all directories in the current directory and sort them
        directories = [directory for directory in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, directory))]
        directories.sort()

        # Create or rename directories based on the manga title
        for i, directory in enumerate(directories, start=1):
            directory_renamed = os.path.join(CWD, f"{manga_title} v{i:02d}")

            # Check if the directory already exists before renaming
            if not os.path.exists(directory_renamed):
                directory_current = os.path.join(CWD, directory)
                os.rename(directory_current, directory_renamed)
                print(f"Renamed folder {BLUE}'{os.path.relpath(directory_current, CWD)}'{RESET} to {BLUE}'{os.path.relpath(directory_renamed, CWD)}'{RESET}.")
            else:
                print(f"Folder: {BLUE}'{os.path.relpath(directory_renamed, CWD)}'{RESET} already exists. Skipping renaming folder.")

    except Exception as e:
        print(f"{RED}Error processing 'info.txt': {e}{RESET}")


# Function to rename image files sequentially
def rename_images(directories_states):
    for root, directories, files in os.walk(CWD):
        # Only consider jpg files in the current folder
        files_jpg = [file for file in files if file.lower().endswith(".jpg")]
        files_jpg.sort()

        # Check directory completion status from directories_states
        directory_path_relative = os.path.relpath(root, CWD)  # Get the relative path of the folder
        if directories_states.get(directory_path_relative) == "Complete":
            print(f"Folder: {BLUE}'{directory_path_relative}'{RESET} is complete. Skipping renaming images.")
            continue  # Skip this folder and move to the next
            
        elif directories_states.get(directory_path_relative) == "Incomplete":
            print(f"Folder: {BLUE}'{directory_path_relative}'{RESET} is incomplete. Starting renaming images.")

            # Rename files to a sequential format (e.g., 001.jpg, 002.jpg, etc.)
            for i, image in enumerate(files_jpg):
                image_path_old = os.path.join(root, image)
                image_name_new = f"{i:03d}.jpg"  # New name in a 3-digit format
                image_path_new = os.path.join(root, image_name_new)

                try:
                    os.rename(image_path_old, image_path_new)
                    print(f"Renamed: {ORANGE}{os.path.relpath(image_path_old, CWD)}{RESET} -> {ORANGE}{os.path.relpath(image_path_new, CWD)}{RESET}")
                except Exception as e:
                    print(f"{RED}Error renaming file {os.path.relpath(image_path_old, CWD)}: {e}{RESET}")


# Function to update metadata in "ComicInfo.xml" based on the folder content and "info.txt"
def metadata():
    metadata_dict = {}
    count_all = 0
    count_directory = 0

    for root, directories, files in os.walk(CWD):
        # Skip the root folder, process only subfolders
        if root == CWD:
            continue

        # Count the number of non-text, non-xml files
        count_all = 0
        for file in files:
            if not (file.endswith(".txt") or file.endswith(".xml")):
                count_all += 1

        # Define the path to the directory's "info.txt" and "ComicInfo.xml"
        comicinfo_path = os.path.join(root, "ComicInfo.xml")
        info_path = os.path.join(root, "info.txt")

        if not os.path.exists(info_path):
            print(f"{RED}Error: 'info.txt' not found in folder: '{os.path.basename(root)}'. Skipping metadata update.{RESET}")
            continue

        # Read metadata from the "info.txt" file
        try:
            with open(info_path, 'r') as info_file:
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
            print(f"{RED}Error reading 'info.txt' for {root}: {e}{RESET}")
            continue

        # Check if ComicInfo.xml exists in the current folder
        if os.path.exists(comicinfo_path):
            try:
                # Read the ComicInfo.xml file to update metadata
                with open(comicinfo_path, 'r') as comicinfo_file:
                    lines = comicinfo_file.readlines()

                # Update metadata in ComicInfo.xml
                for i, line in enumerate(lines):
                    if "<Title>" in line:
                        lines[i] = f"  <Title>{metadata_dict.get('Original_Title', '')}</Title>\n"
                    elif "<LocalizedSeries>" in line:
                        if metadata_dict.get('Original_Title', '') == metadata_dict.get('Title', ''):
                            lines[i] = "  <LocalizedSeries></LocalizedSeries>\n"  # Empty if both titles are the same
                        else:
                            lines[i] = f"  <LocalizedSeries>{metadata_dict.get('Title', '')}</LocalizedSeries>\n"
                    elif "<Writer>" in line:
                        lines[i] = f"  <Writer>{metadata_dict.get('Artist', '')}</Writer>\n"
                    elif "<PageCount>" in line:
                        lines[i] = f"  <PageCount>{count_all}</PageCount>\n"
                    elif "<Tags>" in line:
                        original_tags = metadata_dict.get("Tags", "")

                        excluded_tags = {"digital", "rough grammar"}

                        # Regex pattern to find tags like C12 or C345
                        pattern = re.compile(r'^C\d{2,3}$', re.IGNORECASE)

                        # Check if any tag matches the pattern
                        tags_list = [tag.strip() for tag in original_tags.split(",")]
                        if any(pattern.match(tag) for tag in tags_list):
                            # If matched, add those tags to excluded_tags dynamically
                            for tag in tags_list:
                                if pattern.match(tag):
                                    excluded_tags.add(tag.lower())  # Add the matched tag to exclude (case-insensitive)

                        # Filter tags excluding those in excluded_tags
                        filtered_tags = ", ".join(
                            tag for tag in tags_list
                            if tag.lower() not in excluded_tags
                        )

                        lines[i] = f"  <Tags>{filtered_tags}</Tags>\n"

                # Write updated content back to ComicInfo.xml
                with open(comicinfo_path, 'w') as comicinfo_file:
                    comicinfo_file.writelines(lines)

                print(f"Updated 'ComicInfo.xml' for {BLUE}'{os.path.basename(root)}'{RESET}.")

            except Exception as e:
                print(f"{RED}Error processing 'ComicInfo.xml' for '{os.path.basename(root)}': {e}{RESET}")
        else:
            print(f"'{RED}Error: ComicInfo.xml' not found in folder '{os.path.basename(root)}'. Skipping update.{RESET}")


# Function to update ComicInfo.xml fields like <Number> and <Count>
def update_comicinfo_number_and_count():
    directories_states = {}


    # List all directories in the current directory and sort them
    directories = [directory for directory in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, directory))]
    directories.sort()

    count_directory = len(directories)

    # Iterate through the directories and process ComicInfo.xml
    for directory in directories:
        directory_path = os.path.join(CWD, directory)
        comicinfo_path = os.path.join(directory_path, "ComicInfo.xml")

        # Check if ComicInfo.xml exists in the current directory
        if os.path.exists(comicinfo_path):
            try:
                with open(comicinfo_path, 'r') as comicinfo_file:
                    lines = comicinfo_file.readlines()

                # Directory number is extracted from the last two characters of the directory name
                directory_number = directory[-2:]
                if directory_number.startswith("0"):
                    directory_number = directory_number[1]

                # Update the <Number> field with the directory number
                for i, line in enumerate(lines):
                    if "<Number>" in line:
                        lines[i] = f"  <Number>{directory_number}</Number>\n"

                # Update the <Count> field with the total directory count
                for i, line in enumerate(lines):
                    if "<Count>" in line:
                        lines[i] = f"  <Count>{count_directory}</Count>\n"

                # Write the updated content back to ComicInfo.xml
                with open(comicinfo_path, 'w') as comicinfo_file:
                    comicinfo_file.writelines(lines)

                print(f"Updated <Number> and <Count> in ComicInfo.xml for {BLUE}'{directory}'{RESET}")
            except Exception as e:
                print(f"{RED}Error updating 'ComicInfo.xml' for '{directory}': {e}{RESET}")
        else:
            print(f"'ComicInfo.xml' not found in folder {BLUE}'{directory}'{RESET}. Skipping update.")


# Function to delete all "info.txt" files from directories
def delete_info():
    for root, directories, files in os.walk(CWD):
        for file in files:
            if file == "info.txt":
                try:
                    os.remove(os.path.join(root, file))
                    print(f"Deleted {ORANGE}'{file}'{RESET} from {BLUE}'{os.path.basename(root)}'{RESET}")
                except Exception as e:
                    print(f"{RED}Error deleting file {file}: {e}{RESET}")


# Function to zip each directory and rename the zip file to .cbz
def zip_and_rename():
    for directories in os.listdir(CWD):
        directory_path = os.path.join(CWD, directories)
        if os.path.isdir(directory_path):
            zip_name = os.path.basename(directory_path)
            try:
                zip_file = shutil.make_archive(zip_name, format='zip', root_dir=directory_path)
                cbz_file = os.path.join(CWD, f"{zip_name}.cbz")
                os.rename(zip_file, cbz_file)
                print(f"Zipped and renamed: {BLUE}'{zip_name}'{RESET} -> {ORANGE}'{os.path.basename(cbz_file)}'{RESET}")
            except Exception as e:
                print(f"{RED}Error zipping and renaming {directory_path}: {e}{RESET}")


# Main execution flow
def process_manga():
    move_files_to_new_folder()
    directories_states = check_comicinfo()
    convert_images(directories_states)
    rename_images(directories_states)
    rename_directories()
    metadata()
    update_comicinfo_number_and_count()
    delete_info()
    zip_and_rename()

process_manga()