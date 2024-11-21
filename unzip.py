import os
import shutil

# Unzips the archives
def unzip():
    for filename in os.listdir(os.getcwd()):
        if filename.endswith(".zip"):
            # Create a new folder with the same name as the zip file (without the extension)
            folder_name = os.path.splitext(filename)[0]
            os.makedirs(folder_name, exist_ok=True)

            # Extract the contents of the zip file into the new folder
            extract_dir = os.path.join(os.getcwd(), folder_name)
            shutil.unpack_archive(filename, extract_dir)

unzip()