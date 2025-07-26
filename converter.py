import os
import subprocess
import shutil
import re

# ANSI escape codes for colors
BLUE = '\033[34m'
ORANGE = '\033[38;5;214m'
YELLOW = '\033[33m'
GREEN = '\033[32m'
RED = '\033[31m'
RESET = '\033[0m'

CWD = os.getcwd()


def move_files_to_new_folder():
    def get_or_create_target_directory():
        dirs = sorted([d for d in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, d))])
        if dirs:
            print(f'At least one folder exists. Skipping folder creation. Existing folders:')
            for d in dirs:
                print(f'- {GREEN}{d}{RESET}')
            return os.path.join(CWD, dirs[0])
        else:
            new_dir = os.path.join(CWD, 'temp')
            os.makedirs(new_dir)
            print(f'Created new folder: {GREEN}\'temp\'{RESET} in {GREEN}\'{os.path.basename(CWD)}\'{RESET}')
            return new_dir

    def unique_destination(path, name):
        base, ext = os.path.splitext(name)
        counter = 1
        new_path = os.path.join(path, name)
        while os.path.exists(new_path):
            new_path = os.path.join(path, f'{base}_{counter}{ext}')
            counter += 1
        return new_path

    target_dir = get_or_create_target_directory()
    files = sorted(f for f in os.listdir(CWD) if os.path.isfile(os.path.join(CWD, f)))

    if not files:
        print('No files found to move.')
        return

    for f in files:
        source = os.path.join(CWD, f)
        destination = unique_destination(target_dir, f)
        try:
            shutil.move(source, destination)
            print(f'Moved {ORANGE}\'{f}\'{RESET} to {GREEN}\'{os.path.basename(target_dir)}\'{RESET}')
        except Exception as e:
            print(f'{BLUE}Error moving file \'{f}\': {e}{RESET}')


def check_comicinfo():
    def get_comicinfo_template():
        comicinfo_source_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'ComicInfo.xml')
        if not os.path.exists(comicinfo_source_path):
            print(f'{BLUE}ComicInfo.xml not found in the \'data\' directory.{RESET}')
            return None
        return comicinfo_source_path

    def analyze_directory(base_dir, template_path):
        states = {}
        for root, dirs, _ in os.walk(base_dir):
            dirs.sort()
            for d in dirs:
                dir_path = os.path.join(root, d)
                comicinfo_path = os.path.join(dir_path, 'ComicInfo.xml')
                info_txt_path = os.path.join(dir_path, 'info.txt')

                comicinfo_exists = os.path.exists(comicinfo_path)
                info_exists = os.path.exists(info_txt_path)
                status = 'Complete' if comicinfo_exists else 'Incomplete'

                states[d] = status

                status_color = RED if status == 'Complete' else BLUE
                info_color = RED if info_exists else BLUE
                print(f'Folder: {GREEN}\'{d}\'{RESET} - Status: {status_color}{status}{RESET} - info.txt: {info_color}{"Found" if info_exists else "Not Found"}{RESET}')

                if not comicinfo_exists and template_path:
                    try:
                        shutil.copy(template_path, comicinfo_path)
                        print(f'{GREEN}\'{d}\'{RESET} was {BLUE}incomplete{RESET}. Copied {ORANGE}\'ComicInfo.xml\'{RESET}.')
                    except Exception as e:
                        print(f'{BLUE}Error copying ComicInfo.xml to \'{d}\': {e}{RESET}')
                else:
                    print(f'  No action needed for {GREEN}\'{d}\'{RESET}.')
        return states

    comicinfo_template = get_comicinfo_template()
    if not comicinfo_template:
        return {}

    return analyze_directory(CWD, comicinfo_template)


def convert_images(directories_states):
    dirs = sorted(d for d in directories_states.keys() if os.path.isdir(os.path.join(CWD, d)))

    print('Folder statuses:')
    for d in dirs:
        status = directories_states.get(d, 'Unknown')
        status_color = RED if status == 'Complete' else BLUE
        print(f'Folder: {GREEN}\'{d}\'{RESET} - Status: {status_color}{status}{RESET}')

    for d in dirs:
        if directories_states.get(d) != 'Incomplete':
            continue

        dir_path = os.path.join(CWD, d)
        print(f'\nStarting image conversion in folder: {GREEN}\'{d}\'{RESET} (Status: {BLUE}Incomplete{RESET})')

        files = sorted(f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f)))

        for image in files:
            if not image.lower().endswith(('.png', '.avif', '.jpg', '.webp')):
                continue

            image_path = os.path.join(dir_path, image)
            print(f'Processing image: {GREEN}{d}{RESET}/{ORANGE}{image}{RESET}')

            try:
                command = ['magick', 'mogrify', '-format', 'jpg', '-quality', '100', '-resize', 'x2500', image_path]
                subprocess.run(command, check=True)

                print(f'Converted {ORANGE}\'{image}\'{RESET} to JPG and resized it.')

                image_path_new = os.path.splitext(image_path)[0] + '.jpg'
                if os.path.exists(image_path_new):
                    if image.lower().endswith(('.png', '.avif', '.webp')):
                        os.remove(image_path)
                        print(f'Removed original file: {ORANGE}\'{image}\'{RESET}')
                else:
                    print(f'{BLUE}JPG conversion failed for {ORANGE}\'{image}\'{RESET}. Original file kept.{RESET}')

            except subprocess.CalledProcessError as e:
                print(f'{BLUE}Error converting image {ORANGE}\'{image}\'{RESET}: {e}{RESET}')
            except Exception as e:
                print(f'{BLUE}Unexpected error processing file {ORANGE}\'{image}\'{RESET}: {e}{RESET}')


def rename_images(directories_states):
    dirs = sorted(d for d in directories_states.keys() if os.path.isdir(os.path.join(CWD, d)))

    print('Starting image renaming process:')
    for d in dirs:
        status = directories_states.get(d)
        if status == 'Complete':
            print(f'Folder: {GREEN}\'{d}\'{RESET} is {RED}complete{RESET}. Skipping renaming images.')
            continue
        elif status == 'Incomplete':
            print(f'Folder: {GREEN}\'{d}\'{RESET} is {BLUE}incomplete{RESET}. Starting to rename images.')

            dir_path = os.path.join(CWD, d)
            files_jpg = sorted(f for f in os.listdir(dir_path) if f.lower().endswith('.jpg'))

            for i, image in enumerate(files_jpg, start=0):
                old_path = os.path.join(dir_path, image)
                new_name = f'{i:03d}.jpg'
                new_path = os.path.join(dir_path, new_name)

                if old_path != new_path:
                    try:
                        os.rename(old_path, new_path)
                        print(f'Renamed: {GREEN}{os.path.relpath(os.path.dirname(old_path), CWD)}{RESET}/'
                              f'{ORANGE}{os.path.basename(old_path)}{RESET} -> '
                              f'{GREEN}{os.path.relpath(os.path.dirname(new_path), CWD)}{RESET}/'
                              f'{ORANGE}{os.path.basename(new_path)}{RESET}')
                    except Exception as e:
                        print(f'{BLUE}Error renaming file {GREEN}{os.path.relpath(os.path.dirname(old_path), CWD)}{RESET}/'
                              f'{ORANGE}{os.path.basename(old_path)}{RESET}: {e}{RESET}')


def metadata():
    dirs = sorted(d for d in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, d)))

    print('Folder statuses for metadata update:')
    dir_statuses = {}

    for d in dirs:
        dir_path = os.path.join(CWD, d)
        info_txt_path = os.path.join(dir_path, 'info.txt')
        comicinfo_path = os.path.join(dir_path, 'ComicInfo.xml')

        has_info = os.path.exists(info_txt_path)
        has_comicinfo = os.path.exists(comicinfo_path)

        if not has_info and not has_comicinfo:
            print(f'{BLUE}Error: Both \'info.txt\' and \'ComicInfo.xml\' are missing in folder: \'{d}\'. Skipping metadata update.{RESET}')
            dir_statuses[d] = 'Invalid'
            continue

        status = 'Incomplete' if has_info else 'Complete'
        dir_statuses[d] = status
        status_color = RED if status == 'Complete' else BLUE
        print(f'Folder: {GREEN}\'{d}\'{RESET} - Status: {status_color}{status}{RESET}')

        if status == 'Complete':
            print(f'  Skipping metadata update for {GREEN}\'{d}\'{RESET}.')

    for d in dirs:
        if dir_statuses.get(d) != 'Incomplete':
            continue

        dir_path = os.path.join(CWD, d)
        comicinfo_path = os.path.join(dir_path, 'ComicInfo.xml')
        info_path = os.path.join(dir_path, 'info.txt')

        count_all = sum(1 for f in os.listdir(dir_path)
                        if os.path.isfile(os.path.join(dir_path, f)) and
                        not f.endswith(('.txt', '.xml')))

        metadata_dict = {}
        try:
            with open(info_path, 'r') as info_file:
                for line in info_file:
                    if 'ORIGINAL TITLE:' in line:
                        metadata_dict['Original_Title'] = line.split('ORIGINAL TITLE: ', 1)[-1].strip()
                    elif 'TITLE:' in line:
                        metadata_dict['Title'] = line.split('TITLE: ', 1)[-1].strip()
                    elif 'ARTIST:' in line:
                        metadata_dict['Artist'] = line.split('ARTIST: ', 1)[-1].strip()
                    elif 'TAGS:' in line:
                        metadata_dict['Tags'] = line.split('TAGS: ', 1)[-1].strip()
        except Exception as e:
            print(f'{BLUE}Error reading \'info.txt\' for \'{d}\': {e}{RESET}')
            continue

        if os.path.exists(comicinfo_path):
            try:
                with open(comicinfo_path, 'r') as comicinfo_file:
                    lines = comicinfo_file.readlines()

                for i, line in enumerate(lines):
                    if '<Title>' in line:
                        lines[i] = f'  <Title>{metadata_dict.get("Original_Title", "")}</Title>\n'
                    elif '<LocalizedSeries>' in line:
                        if metadata_dict.get('Original_Title') == metadata_dict.get('Title'):
                            lines[i] = '  <LocalizedSeries></LocalizedSeries>\n'
                        else:
                            lines[i] = f'  <LocalizedSeries>{metadata_dict.get("Title", "")}</LocalizedSeries>\n'
                    elif '<Writer>' in line:
                        lines[i] = f'  <Writer>{metadata_dict.get("Artist", "")}</Writer>\n'
                    elif '<PageCount>' in line:
                        lines[i] = f'  <PageCount>{count_all}</PageCount>\n'
                    elif '<Tags>' in line:
                        original_tags = metadata_dict.get('Tags', '')
                        if not original_tags:
                            continue

                        excluded_tags = {'digital', 'rough grammar', 'rough translation'}
                        pattern = re.compile(r'^(C\d{2,3}|Comic.*)$', re.IGNORECASE)
                        tags_list = [tag.strip() for tag in original_tags.split(',')]

                        for tag in tags_list:
                            if pattern.match(tag):
                                excluded_tags.add(tag.lower())

                        filtered_tags = ', '.join(tag for tag in tags_list if tag.lower() not in excluded_tags)
                        lines[i] = f'  <Tags>{filtered_tags}</Tags>\n'

                with open(comicinfo_path, 'w') as comicinfo_file:
                    comicinfo_file.writelines(lines)

                print(f'Updated metadata in {ORANGE}\'ComicInfo.xml\'{RESET} for {GREEN}\'{d}\'{RESET}.')

            except Exception as e:
                print(f'{BLUE}Error processing \'ComicInfo.xml\' for \'{d}\': {e}{RESET}')
        else:
            print(f'{BLUE}Error: \'ComicInfo.xml\' not found in folder \'{d}\'. Skipping update.{RESET}')


def rename_directories():
    dirs = sorted(d for d in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, d)) and not d.startswith('.'))

    if not dirs:
        print(f'{BLUE}No subdirectories found to rename.{RESET}')
        return

    ref_dir = dirs[0]
    ref_info_path = os.path.join(CWD, ref_dir, 'ComicInfo.xml')

    if not os.path.exists(ref_info_path):
        print(f'{RED}ComicInfo.xml not found in the first folder: \'{ref_dir}\'{RESET}')
        return

    manga_title = ''
    try:
        with open(ref_info_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'<Title>(.*?)</Title>', content)
            if match:
                manga_title = match.group(1).strip()

        if not manga_title:
            print(f'{BLUE}Error: <Title> tag not found in ComicInfo.xml of \'{ref_dir}\'.{RESET}')
            return

    except Exception as e:
        print(f'{RED}Error reading ComicInfo.xml from \'{ref_dir}\': {e}{RESET}')
        return

    for i, directory in enumerate(dirs, start=1):
        old_path = os.path.join(CWD, directory)
        new_name = f'{manga_title} v{i:02d}'
        new_path = os.path.join(CWD, new_name)

        if old_path == new_path:
            print(f'{GREEN}\'{directory}\'{RESET} already named correctly. Skipping.')
            continue

        if os.path.exists(new_path):
            print(f'{RED}Target folder \'{new_name}\' already exists. Skipping rename of \'{directory}\'.{RESET}')
            continue

        try:
            os.rename(old_path, new_path)
            print(f'Renamed {GREEN}\'{directory}\'{RESET} to {GREEN}\'{new_name}\'{RESET}.')
        except Exception as e:
            print(f'{RED}Failed to rename \'{directory}\' to \'{new_name}\': {e}{RESET}')



def update_comicinfo_number_and_count():
    dirs = sorted(d for d in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, d)))
    total_count = len(dirs)

    for index, d in enumerate(dirs, start=1):
        path = os.path.join(CWD, d)
        comicinfo = os.path.join(path, 'ComicInfo.xml')

        if os.path.exists(comicinfo):
            try:
                with open(comicinfo, 'r') as f:
                    lines = f.readlines()

                for i, line in enumerate(lines):
                    if '<Number>' in line:
                        lines[i] = f'  <Number>{index}</Number>\n'
                    elif '<Count>' in line:
                        lines[i] = f'  <Count>{total_count}</Count>\n'

                with open(comicinfo, 'w') as f:
                    f.writelines(lines)

                print(f'Updated <Number> and <Count> in {ORANGE}\'ComicInfo.xml\'{RESET} for {GREEN}\'{d}\'{RESET}')
            except Exception as e:
                print(f'{RED}Error updating \'ComicInfo.xml\' for \'{d}\': {e}{RESET}')
        else:
            print(f'{ORANGE}\'ComicInfo.xml\'{RESET} not found in folder {GREEN}\'{d}\'{RESET}. Skipping update.')


def synchronize_titles():
    dirs = sorted(d for d in os.listdir(CWD) if os.path.isdir(os.path.join(CWD, d)))

    if len(dirs) < 2:
        print(f'Only one folder found. No synchronization needed.{RESET}')
        return

    ref_path = os.path.join(CWD, dirs[0], 'ComicInfo.xml')
    if not os.path.exists(ref_path):
        print(f'{RED}ComicInfo.xml not found in \'{dirs[0]}\'. Cannot sync titles.{RESET}')
        return

    try:
        with open(ref_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ref_title_match = re.search(r'<Title>(.*?)</Title>', content)
        ref_local_match = re.search(r'<LocalizedSeries>(.*?)</LocalizedSeries>', content)

        if not ref_title_match or not ref_local_match:
            print(f'{RED}Missing required tags in reference ComicInfo.xml{RESET}')
            return

        ref_title = ref_title_match.group(1).strip()
        ref_local = ref_local_match.group(1).strip()

    except Exception as e:
        print(f'{RED}Error reading ComicInfo.xml in \'{dirs[0]}\': {e}{RESET}')
        return

    print(f'Using reference Title: {ref_title}{RESET}')
    print(f'Using reference LocalizedSeries: {ref_local}{RESET}')

    for d in dirs[1:]:
        path = os.path.join(CWD, d, 'ComicInfo.xml')

        if not os.path.exists(path):
            print(f'ComicInfo.xml not found in {GREEN}\'{d}\'{RESET}. Skipping.')
            continue

        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            modified = False
            title_found = False
            local_found = False

            for i, line in enumerate(lines):
                # Handle <Title>
                title_match = re.match(r'^(\s*)<Title>(.*?)</Title>', line)
                if title_match:
                    title_found = True
                    indent, current_title = title_match.groups()
                    if current_title.strip() != ref_title:
                        lines[i] = f'{indent}<Title>{ref_title}</Title>\n'
                        modified = True
                    continue

                # Handle <LocalizedSeries>
                local_match = re.match(r'^(\s*)<LocalizedSeries>(.*?)</LocalizedSeries>', line)
                if local_match:
                    local_found = True
                    indent, current_local = local_match.groups()
                    if current_local.strip() != ref_local:
                        lines[i] = f'{indent}<LocalizedSeries>{ref_local}</LocalizedSeries>\n'
                        modified = True
                    continue

            if not title_found or not local_found:
                print(f'{BLUE}\'{d}\' is missing <Title> or <LocalizedSeries>. Skipping.{RESET}')
                continue

            if modified:
                with open(path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f'{GREEN}\'{d}\'{RESET}: Titles synchronized.')
            else:
                print(f'{GREEN}\'{d}\'{RESET}: Titles already match. No changes needed.')

        except Exception as e:
            print(f'{BLUE}Error processing ComicInfo.xml in \'{d}\': {e}{RESET}')


def delete_info():
    for root, _, files in os.walk(CWD):
        for f in files:
            if f == 'info.txt':
                try:
                    os.remove(os.path.join(root, f))
                    print(f'Deleted {ORANGE}\'{f}\'{RESET} from {GREEN}\'{os.path.basename(root)}\'{RESET}')
                except Exception as e:
                    print(f'{BLUE}Error deleting file {f}: {e}{RESET}')


def zip_and_rename():
    for d in os.listdir(CWD):
        path = os.path.join(CWD, d)
        if os.path.isdir(path):
            try:
                zip_path = shutil.make_archive(d, 'zip', root_dir=path)
                cbz_path = os.path.join(CWD, f'{d}.cbz')
                os.rename(zip_path, cbz_path)
                print(f'Zipped and renamed: {GREEN}\'{d}\'{RESET} -> {ORANGE}\'{os.path.basename(cbz_path)}\'{RESET}')
            except Exception as e:
                print(f'{BLUE}Error zipping and renaming {path}: {e}{RESET}')


def process_manga():
    move_files_to_new_folder()
    states = check_comicinfo()
    convert_images(states)
    rename_images(states)
    metadata()
    rename_directories()
    update_comicinfo_number_and_count()
    synchronize_titles()
    delete_info()
    zip_and_rename()


process_manga()
