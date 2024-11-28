import os
import shutil

CWD = os.getcwd()


# Function to move files to a new folder if they're directly in the root
def move_files_to_new_folder():
    # List all directories in the current directory (excluding files)
    existing_folders = [f for f in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, f))]

    if existing_folders:
        print(f"At least one folder exists. Skipping folder creation.")
        new_folder = os.path.join(CWD, existing_folders[0])  # Use the first existing folder
    else:
        # If no folders exist, create a new folder named "files"
        new_folder = os.path.join(CWD, "files")
        os.makedirs(new_folder)
        print(f"Created new folder: {new_folder}")

    # List all files in the current directory (no directories)
    all_files = [f for f in os.listdir(CWD) if os.path.isfile(os.path.join(CWD, f))]

    if not all_files:
        print("No files found to move.")
        return

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
            print(f"Moved '{file}' to '{new_folder}'")
        except Exception as e:
            print(f"Error moving file '{file}': {e}")

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
                    print(f"Renamed folder '{folder}' to '{folder_renamed}'.")
                else:
                    print(f"Folder '{folder_renamed}' already exists, skipping.")

        except Exception as e:
            print(f"Error processing 'info.txt': {e}")
    else:
        print("Error: 'info.txt' file not found.")

# Function to copy the "ComicInfo.xml" from a data directory to each subfolder
def copy_comicinfo():
    folder_comicinfo_old = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "ComicInfo.xml")
    
    # Check if "ComicInfo.xml" exists in the "data" directory
    if not os.path.exists(folder_comicinfo_old):
        print("ComicInfo.xml not found in the 'data' directory.")
        return

    for root, dirs, files in os.walk(CWD):
        for folder in dirs:
            # Construct the path for the new location of ComicInfo.xml in each subfolder
            folder_comicinfo_new = os.path.join(root, folder, "ComicInfo.xml")
            
            # Check if "ComicInfo.xml" already exists in the subfolder
            if not os.path.exists(folder_comicinfo_new):
                try:
                    # Copy the ComicInfo.xml from the source to the subfolder
                    shutil.copy(folder_comicinfo_old, folder_comicinfo_new)
                    print(f"Copied ComicInfo.xml to {folder_comicinfo_new}")
                except Exception as e:
                    # Handle any errors during the copy operation
                    print(f"Error copying file to {folder_comicinfo_new}: {e}")

# Function to update metadata in "ComicInfo.xml" based on the folder content and "info.txt"
def metadata(folder_path):
    metadata_dict = {}
    count_all = 0

    for file_name in os.listdir(folder_path):
        if not (file_name.endswith(".txt") or file_name.endswith(".xml")):
            count_all += 1

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

            # Update <Title>
            for i, line in enumerate(lines):
                if "<Title>" in line:
                    lines[i] = f"  <Title>{metadata_dict.get('Original_Title', '')}</Title>\n"
                # Update <LocalizedSeries> if it's not the same as <Title>
                elif "<LocalizedSeries>" in line:
                    if metadata_dict.get('Original_Title', '') == metadata_dict.get('Title', ''):
                        lines[i] = "  <LocalizedSeries></LocalizedSeries>\n"  # Empty if both titles are the same
                    else:
                        lines[i] = f"  <LocalizedSeries>{metadata_dict.get('Title', '')}</LocalizedSeries>\n"
                # Update <Writer> (Artist)
                elif "<Writer>" in line:
                    lines[i] = f"  <Writer>{metadata_dict.get('Artist', '')}</Writer>\n"
                # Update <Number> with the folder number
                elif "<Number>" in line:
                    folder_number = folder_path[-2:]  # Extract the last two characters of folder name
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

        # Save the updated ComicInfo.xml
        with open(comicinfo_path, 'w') as comic_info_file:
            comic_info_file.writelines(lines)

    except Exception as e:
        print(f"Error updating metadata for {folder_path}: {e}")

# Function to convert image files (PNG, AVIF, JPG) to JPG and resize them
def convert():
    for foldername, subfolders, filenames in os.walk(CWD):
        for filename in filenames:
            filepath = os.path.join(foldername, filename)
            if filename.lower().endswith((".png", ".avif", ".jpg", ".webp")):
                try:
                    os.system(f'magick mogrify -format jpg -quality 100 -resize x2500 "{filepath}"')  # Convert and resize image
                    if filename.lower().endswith(".png"):
                        os.remove(filepath)
                    elif filename.lower().endswith(".avif"):
                        os.remove(filepath)
                    elif filename.lower().endswith(".webp"):
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
    move_files_to_new_folder()
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
