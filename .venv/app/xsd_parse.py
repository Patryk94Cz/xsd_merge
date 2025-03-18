import os
import re
from pathlib import Path
from lxml import etree


def process_xsd_file(input_path, output_path):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(input_path, parser)
    root = tree.getroot()

    # Find namespace prefix for xs
    ns_map = root.nsmap
    xs_prefix = None
    for prefix, uri in ns_map.items():
        if uri == "http://www.w3.org/2001/XMLSchema":
            xs_prefix = prefix
            break

    if xs_prefix is None:
        # If no prefix found, it might be the default namespace
        for prefix, uri in ns_map.items():
            if prefix is None and uri == "http://www.w3.org/2001/XMLSchema":
                xs_prefix = ""
                break

    if xs_prefix is None:
        print(f"Warning: XSD namespace not found in {input_path}, skipping file.")
        return

    # Create XPath with correct namespace
    ns = {xs_prefix if xs_prefix else "xs": "http://www.w3.org/2001/XMLSchema"}
    xpath_prefix = f"{xs_prefix}:" if xs_prefix else ""

    # Find the getCommencementsData complex type
    gc_elements = root.xpath(f".//{xpath_prefix}complexType[@name='getCommencementsData']", namespaces=ns)

    if gc_elements:
        # First, identify all complex types that are referenced within getCommencementsData
        nested_types = set()

        for gc in gc_elements:
            # Find all element nodes directly within getCommencementsData
            if xs_prefix:
                elements = gc.xpath(f".//{xs_prefix}:element", namespaces=ns)
            else:
                elements = gc.xpath(".//element", namespaces=ns)

            # Collect all complex type references
            for elem in elements:
                type_attr = elem.get('type')
                if type_attr and not type_attr.startswith(f"{xs_prefix}:"):
                    nested_types.add(type_attr)

        # Find all complex types that need to be modified
        complex_types_to_process = list(nested_types)
        processed_types = set()

        # Process complex types recursively
        while complex_types_to_process:
            current_type = complex_types_to_process.pop(0)
            if current_type in processed_types:
                continue

            processed_types.add(current_type)

            # Find the complex type definition
            complex_type_elem = root.xpath(f".//{xpath_prefix}complexType[@name='{current_type}']", namespaces=ns)
            if complex_type_elem:
                # Find all elements within this complex type
                if xs_prefix:
                    nested_elements = complex_type_elem[0].xpath(f".//{xs_prefix}:element", namespaces=ns)
                else:
                    nested_elements = complex_type_elem[0].xpath(".//element", namespaces=ns)

                # Check for further nested types
                for nested_elem in nested_elements:
                    nested_type = nested_elem.get('type')
                    if nested_type and not nested_type.startswith(
                            f"{xs_prefix}:") and nested_type not in processed_types:
                        complex_types_to_process.append(nested_type)

                    # Convert integer, boolean, dateTime, and date to string
                    if nested_type in [f"{xs_prefix}:integer", f"{xs_prefix}:boolean", f"{xs_prefix}:dateTime",
                                       f"{xs_prefix}:date"]:
                        nested_elem.set('type', f"{xs_prefix}:string")

        # Process elements directly within getCommencementsData
        for gc in gc_elements:
            if xs_prefix:
                direct_elements = gc.xpath(f".//{xs_prefix}:element", namespaces=ns)
            else:
                direct_elements = gc.xpath(".//element", namespaces=ns)

            for elem in direct_elements:
                type_attr = elem.get('type')
                if type_attr:
                    # Check if the type is integer, boolean, dateTime, or date
                    if type_attr in [f"{xs_prefix}:integer", f"{xs_prefix}:boolean", f"{xs_prefix}:dateTime",
                                     f"{xs_prefix}:date"]:
                        # Replace with string type while keeping the namespace prefix
                        elem.set('type', f"{xs_prefix}:string")

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write the modified XML tree to the output file
    tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)


def process_directory():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, '..', '..', 'xsd')
    output_dir = os.path.join(script_dir, '..', '..', 'xsd_parsed_output')

    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        return

    xsd_files_found = False

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.xsd'):
                xsd_files_found = True
                input_path = os.path.join(root, file)
                rel_path = os.path.relpath(input_path, input_dir)
                output_path = os.path.join(output_dir, rel_path)
                output_subdir = os.path.dirname(output_path)
                os.makedirs(output_subdir, exist_ok=True)
                try:
                    process_xsd_file(input_path, output_path)
                    print(f"Processed: {input_path} -> {output_path}")
                except Exception as e:
                    print(f"Error processing {input_path}: {str(e)}")

    if not xsd_files_found:
        print(f"No XSD files found in '{input_dir}'.")


if __name__ == "__main__":
    process_directory()