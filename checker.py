import os
import zipfile
import re

CWD = os.getcwd()  # Current Working Directory

# Rename .cbz files to .zip
def rename_files_in_directory():
    for sub_folder in os.listdir(CWD):
        sub_folder_path = os.path.join(CWD, sub_folder)
        if os.path.isdir(sub_folder_path):
            for file_name in os.listdir(sub_folder_path):
                if file_name.endswith('.cbz'):
                    original_file = os.path.join(sub_folder_path, file_name)
                    new_file = os.path.join(sub_folder_path, file_name.replace('.cbz', '.zip'))
                    try:
                        os.rename(original_file, new_file)
                    except OSError as e:
                        print(f"Error renaming file {original_file}: {e}")

# Count images in a zip file
def count_images_in_zip(zip_path):
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
    count = 0

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file in zip_ref.namelist():
                if os.path.splitext(file)[1].lower() in image_extensions:
                    count += 1
    except zipfile.BadZipFile as e:
        print(f"Error reading zip file {zip_path}: {e}")
    return count

# Read line 8 in ComicInfo.xml
def read_line_in_xml(zip_path):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Iterate through all files in the zip
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith('ComicInfo.xml'):
                    with zip_ref.open(file_info) as file:
                        lines = file.readlines()
                        if len(lines) > 8:
                            specific_line = lines[8].decode('utf-8')
                            number = re.findall(r'\d+', specific_line)
                            if number:
                                return int(number[0])
    except (zipfile.BadZipFile, KeyError, IndexError) as e:
        print(f"Error reading ComicInfo.xml in {zip_path}: {e}")
    return None
# Process directory and print results
def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.zip'):
                zip_path = os.path.join(root, file)
                image_count = count_images_in_zip(zip_path)
                count_page = read_line_in_xml(zip_path)
                if image_count != count_page:
                    print(f"File: {file}")
                    print(f"Images: {image_count}")
                    print(f"CountPage: {count_page}")
                    print(image_count == count_page)

rename_files_in_directory()
process_directory(CWD)