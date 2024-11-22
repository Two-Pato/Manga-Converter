import os
import shutil

CWD = os.getcwd()

# Function to search for the "info.txt" file in the current directory or its subdirectories
def find_info_file():
    for root, dirs, files in os.walk(CWD):
        if "info.txt" in files:
            return os.path.join(root, "info.txt")
    return None

# Function to process all subfolders in the current working directory
def metadata_subfolders():
    subfolders = [entry.path for entry in os.scandir(CWD) if entry.is_dir()]
    for folder in subfolders:
        metadata(folder)

# Function to create or rename folders based on the manga title found in "info.txt"
def create_folder():
    info_file_path = find_info_file()
    if info_file_path:
        manga_name = ""

        try:
            # Open "info.txt" and extract the original title
            with open(info_file_path, 'r') as info_file:
                for line in info_file:
                    if "ORIGINAL TITLE:" in line:
                        manga_name = line.split("ORIGINAL TITLE: ", maxsplit=1)[-1].rstrip()  # Extract the title
                        break

            if not manga_name:
                print("Error: 'ORIGINAL TITLE' not found in info.txt.")
                return

            # List all folders in the current directory and sort them alphabetically
            folders = [folder for folder in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, folder))]
            folders.sort()

            # Create or rename folders based on manga title
            for i, folder in enumerate(folders, start=1):
                folder_renamed = os.path.join(CWD, f"{manga_name} v{i:02d}")

                # Check if the folder already exists before renaming
                if not os.path.exists(folder_renamed):
                    os.rename(os.path.join(CWD, folder), folder_renamed)
                else:
                    print(f"Folder '{folder_renamed}' already exists.")

        except Exception as e:
            print(f"Error processing 'info.txt': {e}")
    else:
        print("Error: 'info.txt' file not found.")

# Function to copy the "ComicInfo.xml" from a data directory to each subfolder
def copy_comicinfo():
    folder_comicinfo_old = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "ComicInfo.xml")
    
    if not os.path.exists(folder_comicinfo_old):
        print("ComicInfo.xml not found in the 'data' directory.")
        return

    for root, dirs, files in os.walk(CWD):
        for folder in dirs:
            folder_comicinfo_new = os.path.join(root, folder, "ComicInfo.xml")
            if not os.path.exists(folder_comicinfo_new):
                shutil.copy(folder_comicinfo_old, folder_comicinfo_new)

# Function to update metadata in "ComicInfo.xml" based on the folder content and "info.txt"
def metadata(folder_path):
    metadata_dict = {}
    count_png, count_jpg, count_avif = 0, 0, 0
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".png"):
            count_png += 1
        elif file_name.endswith(".jpg"):
            count_jpg += 1
        elif file_name.endswith(".avif"):
            count_avif += 1

    count_all = count_png + count_jpg + count_avif

    folder_count = sum(os.path.isdir(os.path.join(CWD, item)) for item in os.listdir(CWD))

    try:
        # Open "info.txt" and extract metadata information
        with open(os.path.join(folder_path, "info.txt"), 'r') as info_file:
            for line in info_file:
                if "ORIGINAL TITLE:" in line:
                    metadata_dict["Original_Title"] = line.split("ORIGINAL TITLE: ", maxsplit=1)[-1].rstrip()
                elif "TITLE:" in line:
                    metadata_dict["Title"] = line.split("TITLE: ", maxsplit=1)[-1].rstrip()
                elif "ARTIST:" in line:
                    metadata_dict["Artist"] = line.split("ARTIST: ", maxsplit=1)[-1].rstrip()
                elif "TAGS:" in line:
                    metadata_dict["Tags"] = line.split("TAGS: ", maxsplit=1)[-1].rstrip()

        # Open "ComicInfo.xml" and update the metadata fields
        comicinfo_path = os.path.join(folder_path, "ComicInfo.xml")
        with open(comicinfo_path, 'r') as comic_info_file:
            lines = comic_info_file.readlines()

            # Update the fields in the "ComicInfo.xml" file
            if len(lines) > 2:
                lines[2] = f"  <Title>{metadata_dict.get('Original_Title', '')}</Title>\n"
            if len(lines) > 3:
                lines[3] = f"  <LocalizedSeries>{metadata_dict.get('Title', '')}</LocalizedSeries>\n"
            if len(lines) > 4:
                lines[4] = f"  <Writer>{metadata_dict.get('Artist', '')}</Writer>\n"
            if len(lines) > 6:
                folder_number = folder_path[-2:]  # Extract the folder number from the folder name
                if folder_number.startswith("0") and len(folder_number) == 2:
                    folder_number = folder_number[1]  # Remove leading zero
                lines[6] = f"  <Number>{folder_number}</Number>\n"
            if len(lines) > 7:
                lines[7] = f"  <Count>{folder_count}</Count>\n"
            if len(lines) > 8:
                lines[8] = f"  <PageCount>{count_all}</PageCount>\n"
            if len(lines) > 10:
                lines[10] = f"  <Tags>{metadata_dict.get('Tags', '')}</Tags>\n"

        with open(comicinfo_path, 'w') as comic_info_file:
            comic_info_file.writelines(lines)

    except Exception as e:
        print(f"Error updating metadata for {folder_path}: {e}")

# Function to convert image files (PNG, AVIF, JPG) to JPG and resize them
def convert():
    for foldername, subfolders, filenames in os.walk(CWD):
        for filename in filenames:
            filepath = os.path.join(foldername, filename)
            if filename.lower().endswith((".png", ".avif", ".jpg")):
                try:
                    os.system(f'magick mogrify -format jpg -quality 100 -resize x2500 "{filepath}"')  # Convert and resize image
                    if filename.lower().endswith(".png"):
                        os.remove(filepath)
                    elif filename.lower().endswith(".avif"):
                        os.remove(filepath)
                except Exception as e:
                    print(f"Error converting file {filepath}: {e}")

# Function to rename image files sequentially
def rename():
    for foldername, _, filenames in os.walk(CWD):
        jpg_files = [file for file in filenames if file.lower().endswith(".jpg")]
        jpg_files.sort()

        # Rename files to a sequential format (e.g., 001.jpg, 002.jpg, etc.)
        for i, image in enumerate(jpg_files):
            old_filepath = os.path.join(foldername, image)
            new_filename = f"{i:03d}.jpg"  # New name in a 3-digit format
            new_filepath = os.path.join(foldername, new_filename)

            try:
                os.rename(old_filepath, new_filepath)
                print(f"Renamed: {old_filepath} -> {new_filepath}")
            except Exception as e:
                print(f"Error renaming file {old_filepath}: {e}")

# Function to delete all "info.txt" files from subfolders
def delete_info():
    for root, _, files in os.walk(CWD):
        for file in files:
            if file == "info.txt":
                try:
                    os.remove(os.path.join(root, file))
                    print(f"Deleted info.txt: {os.path.join(root, file)}")
                except Exception as e:
                    print(f"Error deleting info.txt {file}: {e}")

# Function to zip each folder and rename the zip file to .cbz
def zip_and_rename():
    for sub_folder in os.listdir(CWD):
        folder_path = os.path.join(CWD, sub_folder)
        if os.path.isdir(folder_path):
            zip_name = os.path.basename(folder_path)
            try:
                zip_file = shutil.make_archive(zip_name, format='zip', root_dir=folder_path)
                cbz_file = os.path.join(CWD, f"{zip_name}.cbz")
                os.rename(zip_file, cbz_file)
                print(f"Zipped and renamed: {zip_name} -> {cbz_file}")
            except Exception as e:
                print(f"Error zipping and renaming {folder_path}: {e}")

# Main process function
def process_manga():
    create_folder()
    copy_comicinfo()
    metadata_subfolders()
    convert()
    rename()
    delete_info()
    zip_and_rename()

# Execute the manga processing
if __name__ == "__main__":
    process_manga()
