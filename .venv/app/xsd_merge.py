#!/usr/bin/env python3
import os
import sys
import glob
from lxml import etree
from typing import Dict, Set, List


class XSDMerger:
    def __init__(self):
        self.ns_map = {
            'xs': 'http://www.w3.org/2001/XMLSchema'
        }
        self.merged_types: Set[str] = set()
        self.merged_elements: Set[str] = set()
        self.merged_root = None
        self.target_namespace = ""

    def load_xsd(self, file_path: str) -> etree._Element:
        try:
            parser = etree.XMLParser(remove_comments=True)
            tree = etree.parse(file_path, parser)
            return tree.getroot()
        except Exception as e:
            print(f"Błąd podczas wczytywania pliku {file_path}: {e}")
            sys.exit(1)

    def initialize_merged_schema(self, root: etree._Element) -> etree._Element:
        self.target_namespace = root.get('targetNamespace', '')

        merged_schema = etree.Element('{http://www.w3.org/2001/XMLSchema}schema')

        for key, value in root.attrib.items():
            merged_schema.set(key, value)

        return merged_schema

    def get_type_name(self, elem: etree._Element) -> str:
        return elem.get('name', '')

    def merge_schemas(self, file_paths: List[str]) -> etree._Element:
        if not file_paths:
            print("Nie podano żadnych plików do połączenia.")
            sys.exit(1)

        root = self.load_xsd(file_paths[0])
        self.merged_root = self.initialize_merged_schema(root)

        self._process_schema(root)

        for file_path in file_paths[1:]:
            current_root = self.load_xsd(file_path)
            self._process_schema(current_root)

        return self.merged_root

    def _process_schema(self, schema: etree._Element) -> None:
        for child in schema:
            if child.tag.endswith('}element'):
                element_name = self.get_type_name(child)
                if element_name and element_name not in self.merged_elements:
                    self.merged_elements.add(element_name)
                    self.merged_root.append(etree.fromstring(etree.tostring(child)))

            elif child.tag.endswith('}complexType') or child.tag.endswith('}simpleType'):
                type_name = self.get_type_name(child)
                if type_name and type_name not in self.merged_types:
                    self.merged_types.add(type_name)
                    self.merged_root.append(etree.fromstring(etree.tostring(child)))

            elif child.tag.endswith('}import') or child.tag.endswith('}include'):
                self.merged_root.append(etree.fromstring(etree.tostring(child)))

    def save_merged_schema(self, output_path: str) -> None:
        if self.merged_root is None:
            print("Nie utworzono jeszcze połączonego schematu.")
            return

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        tree = etree.ElementTree(self.merged_root)

        tree.write(
            output_path,
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True
        )
        print(f"Zapisano połączony schemat do pliku: {output_path}")


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    input_dir = os.path.join(base_dir, 'xsd_merged_input')
    output_dir = os.path.join(base_dir, 'xsd_merged_output')

    if not os.path.isdir(input_dir):
        print(f"Katalog wejściowy nie istnieje: {input_dir}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    xsd_files = glob.glob(os.path.join(input_dir, '*.xsd'))

    if not xsd_files:
        print(f"Nie znaleziono plików XSD w katalogu: {input_dir}")
        sys.exit(1)

    print(f"Znaleziono {len(xsd_files)} plików XSD do połączenia.")

    merger = XSDMerger()
    merger.merge_schemas(xsd_files)

    output_file = os.path.join(output_dir, 'merged_schema.xsd')
    merger.save_merged_schema(output_file)


if __name__ == "__main__":
    main()