import os
import shutil

CWD = os.getcwd()  # Current Working Directory

# Search for "info.txt" file in the current directory or its first subdirectory
def find_info_file():
    # Iterate through directories
    for root, dirs, files in os.walk(CWD):
        if "info.txt" in files:
            return os.path.join(root, "info.txt")
    return None

# Creates a new folder with the name as the manga with the number of the volume
def create_folder():
    info_file_path = find_info_file()
    if info_file_path:
        manga_name = ""
        with open(info_file_path, 'r') as info_file:
            for line in info_file:
                if "ORIGINAL TITLE:" in line:
                    manga_name = line.split("ORIGINAL TITLE: ", maxsplit=1)[-1].rstrip()
                    break

        folders = [folder for folder in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, folder))]
        folder_count = len(folders)

        volume_number = 1
        if folder_count == 0:
            folder_new = os.path.join(CWD, f"{manga_name} v{volume_number:02d}")
            os.mkdir(folder_new)
            for file in os.listdir(CWD):
                shutil.move(os.path.join(CWD, file), folder_new)

        for i, folder in enumerate(folders, start=1):
            volume_number = i
            folder_renamed = os.path.join(CWD, f"{manga_name} v{volume_number:02d}")
            os.rename(os.path.join(CWD, folder), folder_renamed)
    else:
        print("Error: 'info.txt' file not found.")

# Copies the ComicInfo.xml from /data to the current folder
def copy_comicinfo():
    folder_comicinfo_old = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "ComicInfo.xml")
    for root, dirs, files in os.walk(CWD):
        for folder in dirs:
            folder_comicinfo_new = os.path.join(root, folder, "ComicInfo.xml")
            if not os.path.exists(folder_comicinfo_new):
                shutil.copy(folder_comicinfo_old, folder_comicinfo_new)

# Copies Metadata from info.txt and pastes Metadata to ComicInfo.xml
def metadata(folder_path):
    metadata_dict = {}
    count_png = 0
    count_jpg = 0
    count_avif = 0

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".png"):
            count_png += 1
        elif file_name.endswith(".jpg"):
            count_jpg += 1
        elif file_name.endswith(".avif"):
            count_avif += 1

    count_all = count_png + count_jpg + count_avif

    folder_count = sum(os.path.isdir(os.path.join(CWD, item)) for item in os.listdir(CWD))

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

    with open(os.path.join(folder_path, "ComicInfo.xml"), 'r') as comic_info_file:
        lines = comic_info_file.readlines()

        if len(lines) > 2:
            lines[2] = f"  <Title>{metadata_dict.get('Original_Title', '')}</Title>\n"
        if len(lines) > 3:
            lines[3] = f"  <LocalizedSeries>{metadata_dict.get('Title', '')}</LocalizedSeries>\n"
        if len(lines) > 4:
            lines[4] = f"  <Writer>{metadata_dict.get('Artist', '')}</Writer>\n"
        if len(lines) > 6:
            folder_number = folder_path[-2:]
            if folder_number.startswith("0") and len(folder_number) == 2:
                folder_number = folder_number[1]  # Remove leading zero
            lines[6] = f"  <Number>{folder_number}</Number>\n"
        if len(lines) > 7:
            lines[7] = f"  <Count>{folder_count}</Count>\n"
        if len(lines) > 8:
            lines[8] = f"  <PageCount>{count_all}</PageCount>\n"
        if len(lines) > 10:
            lines[10] = f"  <Tags>{metadata_dict.get('Tags', '')}</Tags>\n"

    with open(os.path.join(folder_path, "ComicInfo.xml"), 'w') as comic_info_file:
        comic_info_file.writelines(lines)

# Processes metadata for all subfolders
def metadata_subfolders():
    subfolders = [entry.path for entry in os.scandir(CWD) if entry.is_dir()]
    for folder in subfolders:
        metadata(folder)

# Converts PNGs and AVIFs to JPGs, resizes images
def convert():
    for foldername, subfolders, filenames in os.walk(CWD):
        for filename in filenames:
            filepath = os.path.join(foldername, filename)
            if filename.lower().endswith((".png", ".avif", ".jpg")):
                os.system(f'magick mogrify -format jpg -quality 100 -resize x2500 "{filepath}"')
                if filename.lower().endswith(".png"):
                    os.remove(filepath)
                if filename.lower().endswith(".avif"):
                    os.remove(filepath)

# Renames the files
def rename():
    for foldername, _, filenames in os.walk(CWD):
        # Get a list of .jpg files and sort them in lexicographical order (which works for numeric filenames)
        jpg_files = [file for file in filenames if file.lower().endswith(".jpg")]
        jpg_files.sort()

        for i, image in enumerate(jpg_files):
            old_filepath = os.path.join(foldername, image)
            new_filename = f"{i:03d}.jpg"
            new_filepath = os.path.join(foldername, new_filename)

            os.rename(old_filepath, new_filepath)
            print(f"Renamed: {old_filepath} -> {new_filepath}")

# Deletes the info.txt file from subfolders
def delete_info():
    for root, _, files in os.walk(CWD):
        for file in files:
            if file == "info.txt":
                os.remove(os.path.join(root, file))

# Zips the folders and renames them to .cbz
def zip_and_rename():
    for sub_folder in os.listdir(CWD):
        folder_path = os.path.join(CWD, sub_folder)
        if os.path.isdir(folder_path):
            zip_name = os.path.basename(folder_path)
            zip_file = shutil.make_archive(zip_name, format='zip', root_dir=folder_path)
            cbz_file = os.path.join(CWD, zip_name + ".cbz")
            os.rename(zip_file, cbz_file)

# Main Execution
create_folder()
copy_comicinfo()
metadata_subfolders()
convert()
rename()
delete_info()
zip_and_rename()