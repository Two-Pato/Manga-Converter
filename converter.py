#!/usr/bin/env python3
import logging
import re
import shutil
import subprocess
from pathlib import Path

from lxml import etree as ET


# ANSI colour codes.
GREEN  = "\033[32m"
BLUE   = "\033[34m"
ORANGE = "\033[38;5;214m"
RED    = "\033[31m"
RESET  = "\033[0m"

# Directory paths.
SCRIPT_DIR = Path(__file__).parent
DATA_DIR   = SCRIPT_DIR / "data"
CWD        = Path.cwd()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".avif", ".gif"}

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


# Helper functions.

def _sorted_dirs(root: Path = CWD) -> list[Path]:
    return sorted((d for d in root.iterdir() if d.is_dir()), key=lambda x: x.name.lower())


def _sorted_files(root: Path, suffixes: set[str]) -> list[Path]:
    return sorted(
        (f for f in root.iterdir() if f.is_file() and f.suffix.lower() in suffixes),
        key=lambda x: x.name.lower(),
    )


def _has_sequence_gaps(files: list[Path]) -> bool:
    # Check whether the sorted JPGs form a gap-free zero-padded sequence.
    return any(f.stem != f"{idx:03}" for idx, f in enumerate(files))


# Step 1: Unpack CBZ files and collect loose files.

def move_files_to_new_folder() -> None:
    cbz_files = _sorted_files(CWD, {".cbz"})

    if cbz_files:
        log.info(f"Found {len(cbz_files)} .cbz file(s) in {GREEN}{CWD.name}{RESET}:")
        for f in cbz_files:
            log.info(f"  - {BLUE}{f.name}{RESET}")
        _unpack_cbz_files(cbz_files)
    else:
        log.info(f"No .cbz files found in {GREEN}{CWD.name}{RESET}.")

    _move_remaining_files()


def _unpack_cbz_files(cbz_files: list[Path]) -> None:
    for f in cbz_files:
        extract_dir = CWD / f.stem
        extract_dir.mkdir(exist_ok=True)
        try:
            shutil.unpack_archive(f, extract_dir, format="zip")
            log.info(f"Extracted {BLUE}{f.name}{RESET} -> {GREEN}{extract_dir.name}{RESET}")
            f.unlink()
            log.info(f"Deleted {BLUE}{f.name}{RESET}")
        except (shutil.ReadError, ValueError):
            log.error(f"{ORANGE}Failed to extract {f.name}{RESET}")


def _move_remaining_files(name: str = "temp") -> None:
    files = sorted(
        (f for f in CWD.iterdir() if f.is_file() and f.suffix.lower() != ".cbz"),
        key=lambda x: x.name.lower(),
    )

    if not files:
        return

    target = CWD / name
    target.mkdir(exist_ok=True)
    log.info(f"Created directory {GREEN}{target.name}{RESET}")

    for f in files:
        shutil.move(f, target / f.name)
        log.info(f"Moved {BLUE}{f.name}{RESET} -> {GREEN}{target.name}{RESET}")


# Step 2: Convert images to JPG.

def convert_images(dirs: list[Path]) -> None:
    for d in dirs:
        for img in _sorted_files(d, IMAGE_EXTENSIONS):
            cmd = [
                "magick", "mogrify",
                "-format", "jpg",
                "-quality", "100",
                "-resize", "x2500",
                str(img),
            ]
            try:
                subprocess.run(cmd, check=True)
                log.info(f"Processed {BLUE}{img.name}{RESET} in {GREEN}{d.name}{RESET}")
            except Exception as e:
                log.error(f"{ORANGE}Failed to process {img.name} in {GREEN}{d.name}{RESET}: {e}{RESET}")


# Step 3: Rename images to a zero-padded sequence.

def rename_images(dirs: list[Path]) -> None:
    for d in dirs:
        files = _sorted_files(d, {".jpg"})

        # Phase 1: Rename to temporary names to avoid collisions.
        tmp_paths: list[tuple[Path, str]] = []
        for idx, f in enumerate(files):
            tmp = d / f"tmp_{idx:03}.jpg"
            try:
                f.rename(tmp)
                tmp_paths.append((tmp, f"{idx:03}.jpg"))
            except Exception as e:
                log.error(f"{ORANGE}Failed to rename {f.name} in {GREEN}{d.name}{RESET}: {e}{RESET}")

        # Phase 2: Rename from temporary names to final names.
        for tmp, final_name in tmp_paths:
            try:
                tmp.rename(d / final_name)
                log.info(f"Renamed {BLUE}{tmp.name}{RESET} -> {BLUE}{final_name}{RESET}")
            except Exception as e:
                log.error(f"{ORANGE}Failed to finalise {tmp.name} in {GREEN}{d.name}{RESET}: {e}{RESET}")


# Step 4: ComicInfo.xml helpers.

def read_info_txt(path: Path) -> dict[str, str]:
    if not path.exists():
        log.warning(f"{ORANGE}No info.txt found in {path.parent}{RESET}")
        return {}
    data: dict[str, str] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                key, _, value = line.partition(":")
                data[key.strip().upper()] = value.strip()
    return data


def load_excluded_tags() -> set[str]:
    path = DATA_DIR / "excluded_tags.txt"
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}


def write_xml_with_tags_whitespace(
    tree: ET._ElementTree,
    out_path: Path,
) -> None:
    # Write the XML tree, then post-process to normalise formatting quirks.
    tree.write(out_path, encoding="utf-8", xml_declaration=True, pretty_print=True)

    text = out_path.read_text(encoding="utf-8")

    # Normalise the XML declaration quote style.
    text = re.sub(
        r"<\?xml version=['\"]1\.0['\"] encoding=['\"]UTF-8['\"]\s*\?>",
        '<?xml version="1.0" encoding="utf-8"?>',
        text,
        count=1,
    )

    # Expand all self-closing tags to explicit open/close pairs.
    text = re.sub(r'<([A-Za-z][A-Za-z0-9]*)\s*/>', r'<\1></\1>', text)

    # Ensure a blank line around <Tags>.
    text = re.sub(
        r'\n\s*(<Tags>.*?</Tags>)\s*\n',
        r'\n\n  \1\n\n',
        text,
        flags=re.DOTALL,
    )

    # Collapse runs of three or more newlines.
    text = re.sub(r'\n{3,}', '\n\n', text)

    out_path.write_text(text, encoding="utf-8")


# Step 5: Populate or update ComicInfo.xml.

_EXCLUDE_PATTERN = re.compile(r'^(C\d{2,3}|Comic.*)$', re.IGNORECASE)


def _normalize_tag(tag: str) -> str:
    tag = re.sub(r'[♀♂]', '', tag).strip()
    tag = " ".join(tag.split())  # Collapse internal whitespace.
    words = []
    for word in tag.split():
        words.append(
            "-".join(w.capitalize() for w in word.split("-"))
            if "-" in word
            else word.capitalize()
        )
    return " ".join(words)


def update_comicinfo_metadata(
    comicinfo_file: Path,
    info_data: dict[str, str],
    number: int,
    count: int,
    page_count: int,
    excluded_tags: set[str] | None = None,
) -> None:
    parser = ET.XMLParser(remove_blank_text=True)
    tree   = ET.parse(comicinfo_file, parser)
    root   = tree.getroot()

    if info_data:
        excluded = excluded_tags if excluded_tags is not None else load_excluded_tags()
        raw_tags = re.split(r',|\s{2,}', re.sub(r'[♀♂]', '', info_data.get("TAGS", "") or ""))
        seen: set[str] = set()
        filtered: list[str] = []

        for raw in raw_tags:
            normalized = _normalize_tag(raw)
            key = normalized.lower()
            if not normalized or key in excluded or _EXCLUDE_PATTERN.match(normalized) or key in seen:
                continue
            seen.add(key)
            filtered.append(normalized)

        writer = info_data.get("ARTIST") or info_data.get("CIRCLE", "")
        metadata_fields = {
            "Title":           info_data.get("ORIGINAL TITLE", ""),
            "LocalizedSeries": info_data.get("TITLE", ""),
            "Writer":          writer,
            "Tags":            ", ".join(filtered),
        }
        _set_elements(root, metadata_fields)

    _set_elements(root, {
        "Number":    str(number),
        "Count":     str(count),
        "PageCount": str(page_count),
    })

    write_xml_with_tags_whitespace(tree, comicinfo_file)


def _set_elements(root: ET._Element, fields: dict[str, str]) -> None:
    # Create or update child elements on root from a name-to-value mapping.
    for tag, value in fields.items():
        elem = root.find(tag)
        if elem is None:
            elem = ET.SubElement(root, tag)
        elem.text = value if value is not None else ""


def process_comicinfo() -> None:
    dirs         = _sorted_dirs()
    total        = len(dirs)
    default_xml  = DATA_DIR / "ComicInfo.xml"
    excluded     = load_excluded_tags()

    if not default_xml.exists():
        log.error(f"{ORANGE}Default ComicInfo.xml missing in {DATA_DIR}{RESET}")
        return

    for idx, d in enumerate(dirs, start=1):
        comicinfo = d / "ComicInfo.xml"
        if not comicinfo.exists():
            shutil.copy(default_xml, comicinfo)
            log.info(f"Copied default {BLUE}ComicInfo.xml{RESET} to {GREEN}{d.name}{RESET}")

        page_count = len(_sorted_files(d, {".jpg"}))
        info_data  = read_info_txt(d / "info.txt")
        update_comicinfo_metadata(comicinfo, info_data, number=idx, count=total, page_count=page_count, excluded_tags=excluded)


# Step 6: Synchronise titles across volumes.

def synchronize_titles_and_clear_duplicates() -> None:
    dirs = _sorted_dirs()

    # Find the entry with Number=1 to use as the title source.
    first_title, first_localized = "", ""
    found = False

    for d in dirs:
        comicinfo = d / "ComicInfo.xml"
        if not comicinfo.exists():
            continue
        try:
            root = ET.parse(comicinfo).getroot()
            num  = root.findtext("Number", "").strip()
            if num == "1":
                found           = True
                first_title     = (root.findtext("Title",           "") or "").strip()
                first_localized = (root.findtext("LocalizedSeries", "") or "").strip()
                break
        except ET.XMLSyntaxError:
            continue

    if not found:
        log.warning(f"{ORANGE}No directory with Number=1 found; skipping title sync{RESET}")
        return

    for d in dirs:
        comicinfo = d / "ComicInfo.xml"
        if not comicinfo.exists():
            continue
        try:
            tree = ET.parse(comicinfo)
            root = tree.getroot()

            _set_elements(root, {"Title": first_title, "LocalizedSeries": first_localized})

            # Clear LocalizedSeries when it duplicates Title.
            title_text     = (root.findtext("Title",           "") or "").strip()
            localized_text = (root.findtext("LocalizedSeries", "") or "").strip()
            if title_text and title_text.lower() == localized_text.lower():
                root.find("LocalizedSeries").text = ""
                log.info(
                    f"Cleared duplicate LocalizedSeries in {GREEN}{d.name}{RESET} "
                    f"(was '{RED}{localized_text}{RESET}')"
                )

            write_xml_with_tags_whitespace(tree, comicinfo)

        except ET.XMLSyntaxError as e:
            log.error(f"{ORANGE}Failed to parse ComicInfo.xml in {d.name}: {e}{RESET}")


# Step 7: Rename directories from metadata.

def rename_dirs_from_comicinfo() -> None:
    for d in _sorted_dirs():
        comicinfo = d / "ComicInfo.xml"
        if not comicinfo.exists():
            log.warning(f"{ORANGE}ComicInfo.xml missing in {d.name}; skipping rename{RESET}")
            continue
        try:
            root   = ET.parse(comicinfo).getroot()
            title  = root.find("Title")
            number = root.find("Number")

            if title is None or number is None:
                log.warning(f"{ORANGE}Title or Number missing in {d.name}; skipping rename{RESET}")
                continue

            title_text  = (title.text  or "").strip()
            number_text = (number.text or "").strip()
            if not title_text or not number_text:
                log.warning(f"{ORANGE}Empty Title or Number in {d.name}; skipping rename{RESET}")
                continue

            new_name = f"{title_text} v{int(number_text):02}"
            new_path = CWD / new_name

            if d.name != new_name:
                d.rename(new_path)
                log.info(f"Renamed {GREEN}{d.name}{RESET} -> {GREEN}{new_name}{RESET}")

        except ET.XMLSyntaxError as e:
            log.error(f"{ORANGE}Failed to parse {BLUE}ComicInfo.xml{RESET} in {d.name}: {e}{RESET}")
        except Exception as e:
            log.error(f"{ORANGE}Failed to rename {d.name}: {e}{RESET}")


# Step 8: Clean up info.txt and non-JPG images.

def delete_info_and_imgs() -> None:
    for path in CWD.rglob("info.txt"):
        try:
            path.unlink()
            log.info(f"Deleted {BLUE}{path.name}{RESET} from {GREEN}'{path.parent.name}'{RESET}")
        except Exception as e:
            log.error(f"{ORANGE}Error deleting {path.name} in {path.parent.name}: {e}{RESET}")

    non_jpg_images = IMAGE_EXTENSIONS - {".jpg"}
    for folder in (f for f in CWD.rglob("*") if f.is_dir()):
        for f in folder.iterdir():
            if f.is_file() and f.suffix.lower() in non_jpg_images:
                try:
                    f.unlink()
                    log.info(f"Deleted {BLUE}{f.name}{RESET} from {GREEN}'{folder.name}'{RESET}")
                except Exception as e:
                    log.error(f"{ORANGE}Error deleting {f.name} in {folder.name}: {e}{RESET}")


# Step 9: Zip directories to CBZ.

def zip_and_rename() -> None:
    for d in _sorted_dirs():
        try:
            zip_path = Path(shutil.make_archive(str(d), "zip", root_dir=str(d)))
            cbz_path = d.with_suffix(".cbz")
            zip_path.rename(cbz_path)
            log.info(f"Packed {GREEN}'{d.name}'{RESET} -> {BLUE}'{cbz_path.name}'{RESET}")
        except Exception as e:
            log.error(f"{ORANGE}Error packing {d.name}: {e}{RESET}")


# Entry point.

def main() -> None:
    move_files_to_new_folder()

    # Only process directories that don't already have a ComicInfo.xml.
    dirs_to_process = [
        d for d in _sorted_dirs()
        if not (d / "ComicInfo.xml").exists()
    ]
    if dirs_to_process:
        convert_images(dirs_to_process)
        rename_images(dirs_to_process)

    # Resequence images in existing dirs if a file was added or removed.
    for d in _sorted_dirs():
        if (d / "ComicInfo.xml").exists() and not (d / "info.txt").exists():
            files = _sorted_files(d, {".jpg"})
            if _has_sequence_gaps(files):
                log.info(f"Gap detected in {GREEN}{d.name}{RESET}, resequencing images.")
                rename_images([d])

    process_comicinfo()
    synchronize_titles_and_clear_duplicates()
    rename_dirs_from_comicinfo()
    delete_info_and_imgs()
    zip_and_rename()


if __name__ == "__main__":
    main()
