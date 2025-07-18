import os
import subprocess
import shutil
import re


# Define ANSI escape codes for colors
BLUE = '\033[34m' # Color for "error" and # Color for "bad state"
ORANGE = '\033[38;5;214m' # Color for "files"
YELLOW = '\033[33m'
GREEN = '\033[32m' # Color for "folders"
RED = '\033[31m' # Color for "good state"
RESET = '\033[0m'


CWD = os.getcwd()


def move_files_to_new_folder():
    # If no directory exist, create a new directory named "temp"
    def get_or_create_target_directory():
        dirs = sorted([d for d in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, d))])
        if dirs:
            print(f"At least one folder exists. Skipping folder creation. Existing folders:")
            for d in dirs:
                print(f"- {GREEN}{d}{RESET}")
            return os.path.join(CWD, dirs[0])
        else:
            new_dir = os.path.join(CWD, "temp")
            os.makedirs(new_dir)
            print(f"Created new folder: {GREEN}'temp'{RESET} in {GREEN}'{os.path.basename(CWD)}'{RESET}")
            return new_dir

    # Handle potential filename conflicts
    def unique_destination(path, name):
        base, ext = os.path.splitext(name)
        counter = 1
        new_path = os.path.join(path, name)
        while os.path.exists(new_path):
            new_path = os.path.join(path, f"{base}_{counter}{ext}")
            counter += 1
        return new_path

    target_dir = get_or_create_target_directory()
    files = sorted(f for f in os.listdir(CWD) if os.path.isfile(os.path.join(CWD, f)))

    if not files:
        print("No files found to move.")
        return

    for file in files:
        source = os.path.join(CWD, file)
        destination = unique_destination(target_dir, file)
        try:
            shutil.move(source, destination)
            print(f"Moved {ORANGE}'{file}'{RESET} to {GREEN}'{os.path.basename(target_dir)}'{RESET}")
        except Exception as e:
            print(f"{BLUE}Error moving file '{file}': {e}{RESET}")


# Function to check for ComicInfo.xml and info.txt existence and copy ComicInfo.xml where necessary
def check_comicinfo():
    def get_comicinfo_template():
        comicinfo_source_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "ComicInfo.xml")
        if not os.path.exists(comicinfo_source_path):
            print(f"{BLUE}ComicInfo.xml not found in the 'data' directory.{RESET}")
            return None
        return comicinfo_source_path

    def analyze_directory(base_dir, template_path):
        states = {}
        for root, dirs, _ in os.walk(base_dir):
            dirs.sort()
            for d in dirs:
                folder_path = os.path.join(root, d)
                comicinfo_path = os.path.join(folder_path, "ComicInfo.xml")
                info_txt_path = os.path.join(folder_path, "info.txt")

                comicinfo_exists = os.path.exists(comicinfo_path)
                info_exists = os.path.exists(info_txt_path)
                status = "Complete" if comicinfo_exists else "Incomplete"

                states[d] = status

                # Print the folder status and info.txt existence
                status_color = RED if status == "Complete" else BLUE
                info_color = RED if info_exists else BLUE
                print(f"Folder: {GREEN}'{d}'{RESET} - Status: {status_color}{status}{RESET} - info.txt: {info_color}{'Found' if info_exists else 'Not Found'}{RESET}")

                # If the folder is incomplete and ComicInfo.xml doesn't exist, copy it from the data folder
                if not comicinfo_exists and template_path:
                    try:
                        shutil.copy(template_path, comicinfo_path)
                        print(f"{GREEN}'{d}'{RESET} was {BLUE}incomplete{RESET}. Copied {ORANGE}'ComicInfo.xml'{RESET}.")
                    except Exception as e:
                        print(f"{BLUE}Error copying ComicInfo.xml to '{d}': {e}{RESET}")
                else:
                    print(f"  No action needed for {GREEN}'{d}'{RESET}.")

        return states

    comicinfo_template = get_comicinfo_template()
    if not comicinfo_template:
        return {}

    return analyze_directory(CWD, comicinfo_template)


# Function to convert all images to JPG
def convert_images(directories_states):
    # List and print statuses of all dirs in sorted order (skip root)
    dirs = sorted(d for d in directories_states.keys() if os.path.isdir(os.path.join(CWD, d)))

    print("Folder statuses:")
    for d in dirs:
        status = directories_states.get(d, "Unknown")
        status_color = RED if status == "Complete" else BLUE
        print(f"Folder: {GREEN}'{d}'{RESET} - Status: {status_color}{status}{RESET}")

    # For each folder marked Incomplete, convert images
    for d in dirs:
        status = directories_states.get(d)
        if status != "Incomplete":
            continue  # Skip folders not incomplete

        folder_path = os.path.join(CWD, d)
        print(f"\nStarting image conversion in folder: {GREEN}'{d}'{RESET} (Status: {BLUE}Incomplete{RESET})")

        # List and sort files inside the folder
        files = sorted(f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)))

        for image in files:
            if not image.lower().endswith((".png", ".avif", ".jpg", ".webp")):
                continue  # skip non-image files

            image_path = os.path.join(folder_path, image)
            print(f"Processing image: {GREEN}{d}{RESET}/{ORANGE}{image}{RESET}")

            try:
                command = [
                    'magick', 'mogrify', '-format', 'jpg', '-quality', '100', '-resize', 'x2500', image_path
                ]
                subprocess.run(command, check=True)

                print(f"Converted {ORANGE}'{image}'{RESET} to JPG and resized it.")

                image_path_new = os.path.splitext(image_path)[0] + '.jpg'
                if os.path.exists(image_path_new):
                    if image.lower().endswith((".png", ".avif", ".webp")):
                        os.remove(image_path)
                        print(f"Removed original file: {ORANGE}'{image}'{RESET}")
                else:
                    print(f"{BLUE}JPG conversion failed for {ORANGE}'{image}'{RESET}. Original file kept.{RESET}")

            except subprocess.CalledProcessError as e:
                print(f"{BLUE}Error converting image {ORANGE}'{image}'{RESET}: {e}{RESET}")
            except Exception as e:
                print(f"{BLUE}Unexpected error processing file {ORANGE}'{image}'{RESET}: {e}{RESET}")


def rename_images(directories_states):
    # Get dirs from directories_states keys, sorted
    dirs = sorted(d for d in directories_states.keys() if os.path.isdir(os.path.join(CWD, d)))

    print("Starting image renaming process:")
    for d in dirs:
        status = directories_states.get(d)
        if status == "Complete":
            print(f"Folder: {GREEN}'{d}'{RESET} is {RED}complete{RESET}. Skipping renaming images.")
            continue
        elif status == "Incomplete":
            print(f"Folder: {GREEN}'{d}'{RESET} is {BLUE}incomplete{RESET}. Starting to rename images.")

            folder_path = os.path.join(CWD, d)
            files_jpg = sorted(f for f in os.listdir(folder_path) if f.lower().endswith(".jpg"))

            for i, image in enumerate(files_jpg, start=0):
                old_path = os.path.join(folder_path, image)
                new_name = f"{i:03d}.jpg"
                new_path = os.path.join(folder_path, new_name)

                if old_path != new_path:
                    try:
                        os.rename(old_path, new_path)
                        print(f"Renamed: {GREEN}{os.path.relpath(os.path.dirname(old_path), CWD)}{RESET}/"
                              f"{ORANGE}{os.path.basename(old_path)}{RESET} -> "
                              f"{GREEN}{os.path.relpath(os.path.dirname(new_path), CWD)}{RESET}/"
                              f"{ORANGE}{os.path.basename(new_path)}{RESET}")
                    except Exception as e:
                        print(f"{BLUE}Error renaming file {GREEN}{os.path.relpath(os.path.dirname(old_path), CWD)}{RESET}/"
                              f"{ORANGE}{os.path.basename(old_path)}{RESET}: {e}{RESET}")


def metadata():
    dirs = sorted(d for d in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, d)))

    print("Folder statuses for metadata update:")
    folder_statuses = {}

    for d in dirs:
        folder_path = os.path.join(CWD, d)
        info_txt_path = os.path.join(folder_path, "info.txt")
        comicinfo_path = os.path.join(folder_path, "ComicInfo.xml")

        has_info = os.path.exists(info_txt_path)
        has_comicinfo = os.path.exists(comicinfo_path)

        if not has_info and not has_comicinfo:
            print(f"{BLUE}Error: Both 'info.txt' and 'ComicInfo.xml' are missing in folder: '{d}'. Skipping metadata update.{RESET}")
            folder_statuses[d] = "Invalid"
            continue

        status = "Incomplete" if has_info else "Complete"
        folder_statuses[d] = status
        status_color = RED if status == "Complete" else BLUE
        print(f"Folder: {GREEN}'{d}'{RESET} - Status: {status_color}{status}{RESET}")

        if status == "Complete":
            print(f"  Skipping metadata update for {GREEN}'{d}'{RESET}.")

    # Process only folders marked as "Incomplete"
    for d in dirs:
        if folder_statuses.get(d) != "Incomplete":
            continue

        folder_path = os.path.join(CWD, d)
        comicinfo_path = os.path.join(folder_path, "ComicInfo.xml")
        info_path = os.path.join(folder_path, "info.txt")

        # Count image files
        count_all = sum(1 for f in os.listdir(folder_path)
                        if os.path.isfile(os.path.join(folder_path, f)) and
                        not f.endswith((".txt", ".xml")))

        # Read metadata from info.txt
        metadata_dict = {}
        try:
            with open(info_path, 'r') as info_file:
                for line in info_file:
                    if "ORIGINAL TITLE:" in line:
                        metadata_dict["Original_Title"] = line.split("ORIGINAL TITLE: ", 1)[-1].strip()
                    elif "TITLE:" in line:
                        metadata_dict["Title"] = line.split("TITLE: ", 1)[-1].strip()
                    elif "ARTIST:" in line:
                        metadata_dict["Artist"] = line.split("ARTIST: ", 1)[-1].strip()
                    elif "TAGS:" in line:
                        metadata_dict["Tags"] = line.split("TAGS: ", 1)[-1].strip()
        except Exception as e:
            print(f"{BLUE}Error reading 'info.txt' for '{d}': {e}{RESET}")
            continue

        if os.path.exists(comicinfo_path):
            try:
                with open(comicinfo_path, 'r') as comicinfo_file:
                    lines = comicinfo_file.readlines()

                for i, line in enumerate(lines):
                    if "<Title>" in line:
                        lines[i] = f"  <Title>{metadata_dict.get('Original_Title', '')}</Title>\n"
                    elif "<LocalizedSeries>" in line:
                        if metadata_dict.get('Original_Title') == metadata_dict.get('Title'):
                            lines[i] = "  <LocalizedSeries></LocalizedSeries>\n"
                        else:
                            lines[i] = f"  <LocalizedSeries>{metadata_dict.get('Title', '')}</LocalizedSeries>\n"
                    elif "<Writer>" in line:
                        lines[i] = f"  <Writer>{metadata_dict.get('Artist', '')}</Writer>\n"
                    elif "<PageCount>" in line:
                        lines[i] = f"  <PageCount>{count_all}</PageCount>\n"
                    elif "<Tags>" in line:
                        original_tags = metadata_dict.get("Tags", "")
                        if not original_tags:
                            continue

                        excluded_tags = {"digital", "rough grammar", "rough translation"}
                        pattern = re.compile(r'^(C\d{2,3}|Comic.*)$', re.IGNORECASE)
                        tags_list = [tag.strip() for tag in original_tags.split(",")]

                        for tag in tags_list:
                            if pattern.match(tag):
                                excluded_tags.add(tag.lower())

                        filtered_tags = ", ".join(
                            tag for tag in tags_list if tag.lower() not in excluded_tags
                        )
                        lines[i] = f"  <Tags>{filtered_tags}</Tags>\n"

                with open(comicinfo_path, 'w') as comicinfo_file:
                    comicinfo_file.writelines(lines)

                print(f"Updated metadata in {ORANGE}'ComicInfo.xml'{RESET} for {GREEN}'{d}'{RESET}.")

            except Exception as e:
                print(f"{BLUE}Error processing 'ComicInfo.xml' for '{d}': {e}{RESET}")
        else:
            print(f"{BLUE}Error: 'ComicInfo.xml' not found in folder '{d}'. Skipping update.{RESET}")


# Function to create or rename directories based on the manga title found in "ComicInfo.xml"
def rename_directories():
    # Walk through all directories to find the 'ComicInfo.xml' file
    info_path = None
    for root, directories, files in os.walk(CWD):
        if "ComicInfo.xml" in files:
            info_path = os.path.join(root, "ComicInfo.xml")
            break # Stop once the first info.txt is found

    if not info_path:
        print(f"{BLUE}Error: 'ComicInfo.xml' file not found in any folder.{RESET}")
        return # Exit if no ComicInfo.xml is found

    manga_title = ""

    try:
        # Open 'ComicInfo.xml' and extract the original title
        with open(info_path, 'r') as info_file:
            for line in info_file:
                match = re.search(r'<Title>(.*?)</Title>', line)
                if match:
                    manga_title = match.group(1).strip()
                    break

        if not manga_title:
            print(f"{BLUE}Error: '<Title>' not found in ComicInfo.xml.{RESET}")
            return # Exit if no original title is found

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
                print(f"Renamed folder {GREEN}'{os.path.relpath(directory_current, CWD)}'{RESET} to {GREEN}'{os.path.relpath(directory_renamed, CWD)}'{RESET}.")
            else:
                print(f"Folder: {GREEN}'{os.path.relpath(directory_renamed, CWD)}'{RESET} already exists. Skipping renaming folder.")

    except Exception as e:
        print(f"{BLUE}Error processing 'ComicInfo.xml': {e}{RESET}")


# Function to update ComicInfo.xml fields like <Number> and <Count>
def update_comicinfo_number_and_count():
    directories_states = {}


    # List all directories in the current directory and sort them
    dirs = [d for d in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, d))]
    dirs.sort()

    count_directory = len(dirs)

    # Iterate through the directories and process ComicInfo.xml
    for d in dirs:
        directory_path = os.path.join(CWD, d)
        comicinfo_path = os.path.join(directory_path, "ComicInfo.xml")

        # Check if ComicInfo.xml exists in the current directory
        if os.path.exists(comicinfo_path):
            try:
                with open(comicinfo_path, 'r') as comicinfo_file:
                    lines = comicinfo_file.readlines()

                # Directory number is extracted from the last two characters of the directory name
                directory_number = d [-2:]
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

                print(f"Updated <Number> and <Count> in {ORANGE}'ComicInfo.xml'{RESET} for {GREEN}'{d}'{RESET}")
            except Exception as e:
                print(f"{RED}Error updating 'ComicInfo.xml' for '{d}': {e}{RESET}")
        else:
            print(f"{ORANGE}'ComicInfo.xml'{RESET} not found in folder {GREEN}'{d}'{RESET}. Skipping update.")


def synchronize_titles():
    # List all subdirectories
    dirs = [d for d in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, d))]
    dirs.sort()

    if len(dirs) < 2:
        print(f"Only one folder found. No synchronization needed.{RESET}")
        return

    # Get reference ComicInfo.xml
    comicinfo_path_main = os.path.join(CWD, dirs[0], "ComicInfo.xml")
    if not os.path.exists(comicinfo_path_main):
        print(f"{RED}ComicInfo.xml not found in '{dirs[0]}'. Cannot sync titles.{RESET}")
        return

    # Extract reference title and localized series
    reference_title = ""
    reference_localized = ""

    try:
        with open(comicinfo_path_main, 'r', encoding='utf-8') as file:
            content = file.read()
            title_match = re.search(r"<Title>(.*?)</Title>", content)
            localized_match = re.search(r"<LocalizedSeries>(.*?)</LocalizedSeries>", content)

            reference_title = title_match.group(1).strip() if title_match else ""
            reference_localized = localized_match.group(1).strip() if localized_match else ""

    except Exception as e:
        print(f"{RED}Error reading ComicInfo.xml in '{dirs[0]}': {e}{RESET}")
        return

    print(f"Using reference Title: {reference_title}{RESET}")
    print(f"Using reference LocalizedSeries: {reference_localized}{RESET}")

    # Loop through remaining directories
    for d in dirs[1:]:
        comicinfo_path = os.path.join(CWD, d, "ComicInfo.xml")

        if not os.path.exists(comicinfo_path):
            print(f"ComicInfo.xml not found in {GREEN}'{d}'. Skipping.{RESET}")
            continue

        try:
            with open(comicinfo_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            modified = False
            for i, line in enumerate(lines):
                if "<Title>" in line:
                    current_title = re.search(r"<Title>(.*?)</Title>", line).group(1).strip()
                    if current_title != reference_title:
                        lines[i] = re.sub(r"<Title>.*?</Title>", f"<Title>{reference_title}</Title>", line)
                        modified = True
                elif "<LocalizedSeries>" in line:
                    current_localized = re.search(r"<LocalizedSeries>(.*?)</LocalizedSeries>", line).group(1).strip()
                    if current_localized != reference_localized:
                        lines[i] = re.sub(r"<LocalizedSeries>.*?</LocalizedSeries>", f"<LocalizedSeries>{reference_localized}</LocalizedSeries>", line)
                        modified = True

            if modified:
                with open(comicinfo_path, 'w', encoding='utf-8') as file:
                    file.writelines(lines)
                print(f"{GREEN}'{d}'{RESET}: Titles synchronized.")
            else:
                print(f"{GREEN}'{d}'{RESET}: Titles already match. No changes needed.")

        except Exception as e:
            print(f"{BLUE}Error processing ComicInfo.xml in '{d}': {e}{RESET}")


# Function to delete all "info.txt" files from directories
def delete_info():
    for root, dirs, files in os.walk(CWD):
        for f in files:
            if f == "info.txt":
                try:
                    os.remove(os.path.join(root, f))
                    print(f"Deleted {ORANGE}'{f}'{RESET} from {GREEN}'{os.path.basename(root)}'{RESET}")
                except Exception as e:
                    print(f"{BLUE}Error deleting file {file}: {e}{RESET}")


# Function to zip each directory and rename the zip file to .cbz
def zip_and_rename():
    for dirs in os.listdir(CWD):
        directory_path = os.path.join(CWD, dirs)
        if os.path.isdir(directory_path):
            zip_name = os.path.basename(directory_path)
            try:
                zip_file = shutil.make_archive(zip_name, format='zip', root_dir=directory_path)
                cbz_file = os.path.join(CWD, f"{zip_name}.cbz")
                os.rename(zip_file, cbz_file)
                print(f"Zipped and renamed: {GREEN}'{zip_name}'{RESET} -> {ORANGE}'{os.path.basename(cbz_file)}'{RESET}")
            except Exception as e:
                print(f"{BLUE}Error zipping and renaming {directory_path}: {e}{RESET}")


# Main execution flow
def process_manga():
    move_files_to_new_folder()
    directories_states = check_comicinfo()
    convert_images(directories_states)
    rename_images(directories_states)
    metadata()
    rename_directories()
    update_comicinfo_number_and_count()
    synchronize_titles()
    delete_info()
    zip_and_rename()


process_manga()