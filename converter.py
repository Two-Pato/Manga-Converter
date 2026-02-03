#!/usr/bin/env python3
import logging
import shutil
import subprocess
import re
from pathlib import Path
from lxml import etree as ET

# ANSI escape codes
GREEN = '\033[32m'
BLUE = '\033[34m'
ORANGE = '\033[38;5;214m'
YELLOW = '\033[33m'
RED = '\033[31m'
RESET = '\033[0m'

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
CWD = Path.cwd()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def move_files_to_new_folder():
    def check_cbz_files():
        cbz_files = sorted([f for f in CWD.iterdir() if f.is_file() and f.suffix.lower() == ".cbz"],
                           key=lambda x: x.name.lower())
        if cbz_files:
            logger.info(f"Found {len(cbz_files)} .cbz file(s) in {GREEN}{CWD.name}{RESET}:")
            for f in cbz_files:
                logger.info(f" - {BLUE}{f.name}{RESET}")
        else:
            logger.info(f"No .cbz files found in {GREEN}{CWD.name}{RESET}.")
        return cbz_files

    def unpack_cbz_files(cbz_files):
        for f in cbz_files:
            extract_dir = CWD / f.stem
            extract_dir.mkdir(exist_ok=True)
            try:
                shutil.unpack_archive(str(f), str(extract_dir), format="zip")
                logger.info(f"Extracted {BLUE}{f.name}{RESET} -> {GREEN}{extract_dir.name}{RESET}")
                f.unlink()
                logger.info(f"Deleted {BLUE}{f.name}{RESET}")
            except (shutil.ReadError, ValueError):
                logger.error(f"{ORANGE}Failed to extract {f.name}{RESET}")
                continue

    def get_or_create_target_directory(default_target="temp"):
        dirs = sorted([d for d in CWD.iterdir() if d.is_dir()], key=lambda x: x.name.lower())
        if dirs:
            logger.info(f"Existing directories in {GREEN}{CWD.name}{RESET}:")
            for d in dirs:
                logger.info(f" - {GREEN}{d.name}{RESET}")
            target_dir = CWD / default_target
        else:
            target_dir = CWD / default_target
            if not target_dir.exists():
                target_dir.mkdir()
                logger.info(f"Created directory {GREEN}{target_dir.name}{RESET}")
        return target_dir

    def move_remaining_files(target_dir):
        files_to_move = sorted([f for f in CWD.iterdir() if f.is_file() and f.suffix.lower() != ".cbz"],
                               key=lambda x: x.name.lower())
        if not files_to_move:
            logger.info(f"{ORANGE}No files to move to {target_dir.name}{RESET}")
            return
        for f in files_to_move:
            dest = target_dir / f.name
            shutil.move(str(f), str(dest))
            logger.info(f"Moved {BLUE}{f.name}{RESET} -> {GREEN}{target_dir.name}{RESET}")

    cbz_files = check_cbz_files()
    if cbz_files:
        unpack_cbz_files(cbz_files)

    target_dir = get_or_create_target_directory()
    move_remaining_files(target_dir)


def convert_images(dirs):
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".avif", ".gif"}
    for d in dirs:
        images = sorted([i for i in d.iterdir() if i.is_file() and i.suffix.lower() in image_extensions],
                        key=lambda x: x.name.lower())
        for i in images:
            command = [
                "magick", "mogrify",
                "-format", "jpg",
                "-quality", "100",
                "-resize", "x2500",
                str(i)
            ]
            try:
                subprocess.run(command, check=True)
                logger.info(f"Processed {BLUE}{i.name}{RESET} in {GREEN}{d.name}{RESET}")
            except Exception as e:
                logger.error(f"{ORANGE}Failed to process {i.name} in {GREEN}{d.name}{RESET}: {e}{RESET}")


def rename_images(dirs):
    for d in dirs:
        images = sorted([f for f in d.iterdir() if f.is_file() and f.suffix.lower() == ".jpg"], key=lambda x: x.name.lower())
        for idx, f in enumerate(images, start=0):
            new_name = f"{idx:03}.jpg"
            new_path = d / new_name
            if f.name != new_name:
                try:
                    f.rename(new_path)
                    logger.info(f"Renamed {BLUE}{f.name}{RESET} -> {BLUE}{new_name}{RESET}")
                except Exception as e:
                    logger.error(f"{ORANGE}Failed to rename {f.name} in {GREEN}{d.name}{RESET}: {e}{RESET}")


def read_info_txt(info_txt_file: Path):
    info_data = {}
    if not info_txt_file.exists():
        logger.warning(f"{ORANGE}No info.txt found in {info_txt_file.parent}{RESET}")
        return info_data
    with info_txt_file.open("r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                key, value = line.split(":", 1)
                info_data[key.strip().upper()] = value.strip()
    return info_data


def load_excluded_tags():
    excluded_file = DATA_DIR / "excluded_tags.txt"
    if not excluded_file.exists():
        return set()
    excluded = set()
    with excluded_file.open("r", encoding="utf-8") as f:
        for line in f:
            tag = line.strip().lower()
            if tag:
                excluded.add(tag)
    return excluded


def write_xml_with_tags_whitespace(tree, out_path, expand_tags=None):
    if expand_tags is None:
        expand_tags = ["LocalizedSeries"]

    tree.write(str(out_path), encoding="utf-8", xml_declaration=True, pretty_print=True)

    with open(out_path, "r", encoding="utf-8") as f:
        xml_text = f.read()

    xml_text = re.sub(
        r"<\?xml version=['\"]1\.0['\"] encoding=['\"]UTF-8['\"]\s*\?>",
        '<?xml version="1.0" encoding="utf-8"?>',
        xml_text,
        count=1
    )

    for tag in expand_tags:
        xml_text = re.sub(
            rf'(\n\s*)<({tag})\s*/\s*>',
            rf'\1<\2></\2>',
            xml_text
        )
        xml_text = re.sub(
            rf'<({tag})\s*/\s*>',
            rf'<\1></\1>',
            xml_text
        )

    xml_text = re.sub(
        r'\n\s*(<Tags>.*?</Tags>)\s*\n',
        r'\n\n  \1\n\n',
        xml_text,
        flags=re.DOTALL
    )

    xml_text = re.sub(r'\n{3,}', r'\n\n', xml_text)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml_text)


def update_comicinfo_metadata(comicinfo_file: Path, info_data: dict, number: int, count: int, page_count: int):
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse(str(comicinfo_file), parser)
    root = tree.getroot()

    excluded_tags = load_excluded_tags()
    exclude_pattern = re.compile(r'^(C\d{2,3}|Comic.*)$', re.IGNORECASE)

    def normalize_tag(tag: str) -> str:
        tag = re.sub(r'[♀♂]', '', tag)
        tag = " ".join(tag.split())

        words = []
        for word in tag.split():
            if "-" in word:
                words.append("-".join(w.capitalize() for w in word.split("-")))
            else:
                words.append(word.capitalize())

        return " ".join(words)

    if info_data:
        original_tags = str(info_data.get("TAGS", "") or "")
        filtered_tags = []
        seen = set()

        if original_tags:
            cleaned = re.sub(r'[♀♂]', '', original_tags)

            raw_tags = re.split(r',|\s{2,}', cleaned)

            for raw in raw_tags:
                raw = raw.strip()
                if not raw:
                    continue

                normalized = normalize_tag(raw)
                key = normalized.lower()

                if key in excluded_tags:
                    continue
                if exclude_pattern.match(normalized):
                    continue

                if key in seen:
                    continue

                seen.add(key)
                filtered_tags.append(normalized)

        fields = {
            "Title": info_data.get("ORIGINAL TITLE", ""),
            "LocalizedSeries": info_data.get("TITLE", ""),
            "Writer": info_data.get("ARTIST", ""),
            "Tags": ", ".join(filtered_tags),
        }

        for tag_name, value in fields.items():
            elem = root.find(tag_name)
            if elem is None:
                elem = ET.SubElement(root, tag_name)
            elem.text = value if value is not None else ""

    counts_fields = {
        "Number": str(number),
        "Count": str(count),
        "PageCount": str(page_count),
    }

    for tag_name, value in counts_fields.items():
        elem = root.find(tag_name)
        if elem is None:
            elem = ET.SubElement(root, tag_name)
        elem.text = value

    # Preserve empty-tag form and tag whitespace
    write_xml_with_tags_whitespace(tree, str(comicinfo_file), expand_tags=["LocalizedSeries"])


def process_comicinfo():
    dirs = sorted([d for d in CWD.iterdir() if d.is_dir()], key=lambda x: x.name.lower())
    total_dirs = len(dirs)
    default_comicinfo = DATA_DIR / "ComicInfo.xml"

    if not default_comicinfo.exists():
        logger.error(f"{ORANGE}Default ComicInfo.xml missing in {DATA_DIR}{RESET}")
        return

    for idx, d in enumerate(dirs, start=1):
        info_txt_file = d / "info.txt"
        comicinfo_file = d / "ComicInfo.xml"

        if not comicinfo_file.exists():
            shutil.copy(default_comicinfo, comicinfo_file)
            logger.info(f"Copied default {BLUE}ComicInfo.xml{RESET} to {GREEN}{d.name}{RESET}")

        page_count = len([f for f in d.iterdir() if f.is_file() and f.suffix.lower() == ".jpg"])
        info_data = read_info_txt(info_txt_file)
        update_comicinfo_metadata(comicinfo_file, info_data, number=idx, count=total_dirs, page_count=page_count)


def synchronize_titles_and_clear_duplicates():
    dirs = sorted([d for d in CWD.iterdir() if d.is_dir()], key=lambda x: x.name.lower())
    first_title = ""
    first_localized = ""
    first_dir = None

    for d in dirs:
        comicinfo_file = d / "ComicInfo.xml"
        if not comicinfo_file.exists():
            continue
        try:
            tree = ET.parse(str(comicinfo_file))
            root = tree.getroot()
            number_elem = root.find("Number")
            if number_elem is not None and (number_elem.text or "").strip() == "1":
                first_dir = d
                title_elem = root.find("Title")
                localized_elem = root.find("LocalizedSeries")
                first_title = (title_elem.text or "").strip() if title_elem is not None else ""
                first_localized = (localized_elem.text or "").strip() if localized_elem is not None else ""
                break
        except ET.XMLSyntaxError:
            continue

    if not first_dir:
        logger.warning(f"{ORANGE}No directory with Number=1 found, skipping title synchronization{RESET}")
        return

    for d in dirs:
        comicinfo_file = d / "ComicInfo.xml"
        if not comicinfo_file.exists():
            continue
        try:
            tree = ET.parse(str(comicinfo_file))
            root = tree.getroot()

            for tag_name, value in [("Title", first_title), ("LocalizedSeries", first_localized)]:
                elem = root.find(tag_name)
                if elem is None:
                    elem = ET.SubElement(root, tag_name)
                # Ensure explicit empty string when value is empty
                elem.text = value if value is not None else ""

                if (elem.text or "").strip() != (value or "").strip():
                    logger.info(f"Updated {tag_name} in {GREEN}{d.name}{RESET} -> {BLUE}{value}{RESET}")

            # If Title and LocalizedSeries are the same, clear LocalizedSeries explicitly to empty string
            title_elem = root.find("Title")
            localized_elem = root.find("LocalizedSeries")
            if title_elem is not None and localized_elem is not None:
                title_text = (title_elem.text or "").strip()
                localized_text = (localized_elem.text or "").strip()
                if title_text and title_text.lower() == localized_text.lower():
                    localized_elem.text = ""  # explicit empty string to avoid self-closing
                    logger.info(f"Cleared duplicate LocalizedSeries for {GREEN}{d.name}{RESET} (was '{RED}{localized_text}{RESET}')")

            # Write back with our writer to preserve empty element form and whitespace
            write_xml_with_tags_whitespace(tree, str(comicinfo_file), expand_tags=["LocalizedSeries"])

        except ET.XMLSyntaxError as e:
            logger.error(f"{ORANGE}Failed to parse ComicInfo.xml in {d.name}: {e}{RESET}")


def rename_dirs_from_comicinfo():
    dirs = sorted([d for d in CWD.iterdir() if d.is_dir()], key=lambda x: x.name.lower())

    for d in dirs:
        comicinfo_file = d / "ComicInfo.xml"
        if not comicinfo_file.exists():
            logger.warning(f"{ORANGE}ComicInfo.xml missing in {d.name}, skipping rename{RESET}")
            continue

        try:
            tree = ET.parse(str(comicinfo_file))
            root = tree.getroot()
            title_elem = root.find("Title")
            number_elem = root.find("Number")

            if title_elem is None or number_elem is None:
                logger.warning(f"{ORANGE}Title or Number missing in {d.name}, skipping rename{RESET}")
                continue

            number = int(number_elem.text.strip())
            number_str = f"{number:02}"
            new_dir_name = f"{title_elem.text.strip()} v{number_str}"
            new_dir_path = CWD / new_dir_name

            if d.name != new_dir_name:
                d.rename(new_dir_path)
                logger.info(f"Renamed directory {GREEN}{d.name}{RESET} -> {GREEN}{new_dir_name}{RESET}")

        except ET.XMLSyntaxError as e:
            logger.error(f"{ORANGE}Failed to parse {BLUE}ComicInfo.xml{RESET} in {d.name}: {e}{RESET}")
        except Exception as e:
            logger.error(f"{ORANGE}Failed to rename directory {d.name}: {e}{RESET}")


def delete_info_and_imgs():
    # Delete all info.txt files
    for d in CWD.rglob("info.txt"):
        try:
            d.unlink()
            logger.info(f"Deleted {BLUE}{d.name}{RESET} from {GREEN}'{d.parent.name}'{RESET}")
        except Exception as e:
            logger.error(f"{ORANGE}Error deleting file {d.name} in {d.parent.name}: {e}{RESET}")

    # Delete all images that are NOT .jpg
    valid_ext = {".jpg"}

    for folder in [i for i in CWD.rglob("*") if i.is_dir()]:
        for f in folder.iterdir():
            if f.is_file():
                ext = f.suffix.lower()
                if ext not in valid_ext and ext in {".png", ".jpeg", ".webp", ".tif", ".tiff", ".avif", ".gif"}:
                    try:
                        f.unlink()
                        logger.info(f"Deleted {BLUE}{f.name}{RESET} from {GREEN}'{folder.name}'{RESET}")
                    except Exception as e:
                        logger.error(f"{ORANGE}Error deleting non-JPG {f.name} in {folder.name}: {e}{RESET}")


def zip_and_rename():
    for d in sorted([d for d in CWD.iterdir() if d.is_dir()], key=lambda x: x.name.lower()):
        try:
            zip_path = shutil.make_archive(str(d), 'zip', root_dir=str(d))
            cbz_path = d.with_suffix('.cbz')
            Path(zip_path).rename(cbz_path)
            logger.info(f"Zipped and renamed: {GREEN}'{d.name}'{RESET} -> {BLUE}'{cbz_path.name}'{RESET}")
        except Exception as e:
            logger.error(f"{ORANGE}Error zipping and renaming {d.name}: {e}{RESET}")


def main():
    move_files_to_new_folder()

    dirs_to_process = sorted(
        [d for d in CWD.iterdir() if d.is_dir() and not (d / "ComicInfo.xml").exists()],
        key=lambda x: x.name.lower()
    )

    if dirs_to_process:
        convert_images(dirs_to_process)
        rename_images(dirs_to_process)

    process_comicinfo()
    synchronize_titles_and_clear_duplicates()
    rename_dirs_from_comicinfo()
    delete_info_and_imgs()
    zip_and_rename()


if __name__ == "__main__":
    main()