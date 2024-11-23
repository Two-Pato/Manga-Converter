import os
import xml.etree.ElementTree as ET

# Root folder path
root_folder = os.getcwd()  # Current Working Directory

# Function to recursively traverse subdirectories
def remove_localized_series_from_xml(parent_folder):
    # Iterate over each item in the parent folder
    for sub_folder in os.listdir(parent_folder):
        sub_folder_path = os.path.join(parent_folder, sub_folder)
        if os.path.isdir(sub_folder_path):  # If it's a directory
            # Look for the 'ComicInfo.xml' file inside the subdirectory
            xml_file = os.path.join(sub_folder_path, 'ComicInfo.xml')
            if os.path.exists(xml_file):
                remove_localized_series(xml_file)
            # Recursively check subdirectories within this subfolder
            remove_localized_series_from_xml(sub_folder_path)

# Function to remove or modify LocalizedSeries in a given XML file
def remove_localized_series(xml_file):
    try:
        # Parse the XML file
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Find the <Title> and <LocalizedSeries> elements
        title_element = root.find('.//Title')
        localized_series_element = root.find('.//LocalizedSeries')

        if title_element is not None and localized_series_element is not None:
            title_text = title_element.text.strip() if title_element.text else ""
            localized_series_text = localized_series_element.text.strip() if localized_series_element.text else ""

            # If Title and LocalizedSeries are the same, clear the content inside <LocalizedSeries>
            if title_text == localized_series_text:
                localized_series_element.text = ""  # Clear the value inside <LocalizedSeries> but keep the tag

                print(f"Cleared content of <LocalizedSeries> in {xml_file} because it matches <Title>.")

        # Serialize the tree back to a string (without XML declaration yet)
        xml_str = ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

        # Manually fix self-closing <LocalizedSeries /> to <LocalizedSeries></LocalizedSeries>
        xml_str = xml_str.replace('<LocalizedSeries />', '<LocalizedSeries></LocalizedSeries>')

        # Write the updated XML back to the file
        with open(xml_file, 'w', encoding='utf-8') as f:
            # Write the XML declaration and content back without any empty line after <ComicInfo>
            f.write("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
            f.write("<ComicInfo xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">")
            f.write(xml_str[xml_str.find('<ComicInfo>') + len('<ComicInfo>'):])  # Write content directly after <ComicInfo>

    except ET.ParseError as e:
        print(f"Error parsing XML file {xml_file}: {e}")
    except OSError as e:
        print(f"Error writing to XML file {xml_file}: {e}")

# Call the function to start from the root folder
remove_localized_series_from_xml(root_folder)
