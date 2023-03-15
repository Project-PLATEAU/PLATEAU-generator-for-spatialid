import argparse
import os
import re
import typing

from lxml import etree

import constants
import inputs
import outputs

Any = typing.Any
Set = typing.Set
Dict = typing.Dict
List = typing.List
Tuple = typing.Tuple

OUTPUT_ELEMENT_INFO = None


def main(citygml_file_or_dir: str, id_file_or_dir: str, output_file_or_dir: str, output_form: str) -> None:
    """ID pair list 2 CityGML with spatial IDs

    Args:
        citygml_file_or_dir (str): path to the CityGML file (*.gml) or directory
        id_file_or_dir (str): path to the ID pair list file (*.csv) or directory
        output_file_or_dir (str): path to the output CityGML file (*.gml) or directory
        output_form (str): form of SpatialIDs
    """
    # batch
    output_ext = os.path.splitext(output_file_or_dir)[-1]
    if os.path.isdir(citygml_file_or_dir) and os.path.isdir(id_file_or_dir) and output_ext == '':
        if citygml_file_or_dir != id_file_or_dir:
            raise ValueError(f'Different input directories are not supported')
        citygml_files = inputs.get_target_gml_files(citygml_file_or_dir)
        id_files = inputs.get_target_id_files(id_file_or_dir)
        output_files = outputs.build_output_paths(
            None,
            citygml_file_or_dir,
            citygml_files,
            output_file_or_dir,
            output_ext='.gml'
        )
        # check citygml_files, id_files
        actual_citygml_files = []
        actual_id_files = []
        for citygml_file in citygml_files:
            id_file = find_id_file(citygml_file, id_files)
            if id_file:
                actual_citygml_files.append(citygml_file)
                actual_id_files.append(id_file)
        citygml_files = actual_citygml_files
        id_files = actual_id_files
    elif os.path.isfile(citygml_file_or_dir) and os.path.isfile(id_file_or_dir) and output_ext == '.gml':
        citygml_files = [citygml_file_or_dir]
        id_files = [id_file_or_dir]
        output_files = [output_file_or_dir]
    else:
        raise ValueError(f'Invalid path: {citygml_file_or_dir} {id_file_or_dir} {output_file_or_dir}')

    # main
    for citygml_file, id_file, output_file in zip(citygml_files, id_files, output_files):
        elem_info = get_output_element_info_file(citygml_file)
        if elem_info:
            ns_prefix = elem_info[0]
        else:
            ns_prefix = None
        xml = inputs.load_xml(citygml_file, ns_prefix=ns_prefix)
        ids, max_zoom_level, merged = load_ids(id_file)
        update_xml(xml, ids, id_file, output_form, max_zoom_level, merged)
        output_xml(xml, output_file)


def find_id_file(citygml_file: str, id_files: List[str]) -> str:
    """find corresponding CSV file

    Args:
        citygml_file (str): .gml file path
        id_files (List[str]): .csv file paths

    Returns:
        str: corresponding .csv file path
    """
    id_file_pattern = '/spatialid/'.join(os.path.split(citygml_file)).replace('.gml', '_zl[0-9]+(_merged)?.csv')
    for id_file in reversed(sorted(id_files)):
        if re.match(id_file_pattern, id_file):
            return id_file
    return None


def load_ids(id_file: str) -> Tuple[Dict[str, Set[str]], int, bool]:
    """load ID pair list

    Args:
        id_file (str): path to the ID pair list file (*.csv)

    Returns:
        Tuple[Dict[str, Set[str]], int, bool]: ID pair dict, max_zoom_level, merged
    """
    data = {}
    max_zoom_level = None
    merged = None
    for tokens in inputs.load_ids(id_file):
        gml_id, spatial_id, props, max_zoom_level, merged = tokens
        data.setdefault(gml_id, set()).add(spatial_id)
    return data, max_zoom_level, merged


def update_xml(xml: etree.ElementTree, ids: Dict[str, Set[str]], id_file: str,
               output_form: str, max_zoom_level: int = None,
               merged: bool = None) -> None:
    """append spatial ID elements to CityGML

    Args:
        xml (etree.ElementTree): CityGML
        ids (Dict[str, Set[str]]): ID pair dict
        id_file (str): path to the ID pair list file (*.csv)
        output_form (str): form of SpatialIDs
        max_zoom_level (int, optional): max zoom level. Defaults to None.
        merged (bool, optional): whether merge option is specified or not. Defaults to None.

    Raises:
        ValueError: parameter error
    """
    if output_form in {constants.SPATIALID_EMBEDDING, constants.SPATIALID_BOTH}:
        update_xml_embedding(xml, ids, max_zoom_level, merged)
    if output_form in {constants.SPATIALID_REFERENCE, constants.SPATIALID_BOTH}:
        update_xml_reference(xml, id_file)


def update_xml_embedding(xml: etree.ElementTree, ids: Dict[str, Set[str]],
                         max_zoom_level: int = None, merged: bool = None) -> None:
    """append spatial ID elements to CityGML

    Args:
        xml (etree.ElementTree): CityGML
        ids (Dict[str, Set[str]]): ID pair dict
        max_zoom_level (int, optional): max zoom level. Defaults to None.
        merged (bool, optional): whether merge option is specified or not. Defaults to None.

    Raises:
        ValueError: parameter error
    """
    id_elms = xml.findall(
        '//*[@gml:id]',
        namespaces={
            'gml': 'http://www.opengis.net/gml',
        }
    )
    elm_map = {}
    for id_elm in id_elms:
        gml_id = id_elm.attrib['{http://www.opengis.net/gml}id']
        elm_map[gml_id] = id_elm
    for gml_id, id_set in ids.items():
        elm = elm_map.get(gml_id)
        if elm is None:
            raise ValueError(f'Invalid id: {gml_id}')
        # feature class name
        fc_name = etree.QName(elm.tag).localname
        elem_info = get_output_element_info(fc_name)
        if elem_info:
            ns_prefix, attr_prefix1, insert_afters = elem_info
            attr_prefix2 = f'{attr_prefix1[0].upper()}{attr_prefix1[1:]}'
        else:
            ns_prefix = 'uro'
            attr_prefix1 = f'{fc_name[0].lower()}{fc_name[1:]}'
            attr_prefix2 = fc_name
            insert_afters = None
        ns_info = constants.NAMESPACES.get(ns_prefix)
        ns_uri = ns_info['uri']
        attr_name1 = f'{attr_prefix1}SpatialIDAttribute'
        attr_name2 = f'{attr_prefix2}SpatialIDAttribute'
        # remove old ids
        attr_elms = elm.findall(f'./{{*}}{attr_name1}')
        for attr_elm in attr_elms:
            elm.remove(attr_elm)
        attr_elm1 = etree.Element(
            f'{{{ns_uri}}}{attr_name1}'
        )
        attr_elm2 = etree.Element(
            f'{{{ns_uri}}}{attr_name2}'
        )
        attr_elm1.append(attr_elm2)
        if max_zoom_level is not None:
            zoom_elm = etree.Element(
                f'{{{ns_uri}}}maxZoomLevel'
            )
            zoom_elm.text = str(max_zoom_level)
            attr_elm2.append(zoom_elm)
        if merged is not None:
            merge_elm = etree.Element(
                f'{{{ns_uri}}}merge'
            )
            merge_elm.text = str(merged).lower()
            attr_elm2.append(merge_elm)
        for spatial_id in id_set:
            id_elm = etree.Element(
                f'{{{ns_uri}}}spatialID'
            )
            id_elm.text = spatial_id
            attr_elm2.append(id_elm)
        if insert_afters is None:
            elm.append(attr_elm1)
        else:
            for insert_after in reversed(insert_afters):
                insert_after_elm = elm.find(f'{{*}}{insert_after}')
                if insert_after_elm is not None:
                    insert_after_elm.addnext(attr_elm1)
                    break


def update_xml_reference(xml: etree.ElementTree, id_file: str) -> None:
    """append spatial ID elements to CityGML

    Args:
        xml (etree.ElementTree): CityGML
        id_file (str): path to the ID pair list file (*.csv)

    Raises:
        ValueError: parameter error
    """
    elem_info = get_output_element_info_doc(xml)
    if elem_info is None:
        return
    ns_prefix = elem_info[0]
    ns_uri = constants.NAMESPACES[ns_prefix]['uri']
    id_file_rel = f'{constants.CSV_DIRECTORY}/{os.path.basename(id_file)}'
    root_elm = xml.getroot()
    # remove old reference
    ref_elms = root_elm.findall(f'./{{{ns_uri}}}externalReferenceOfSpatialID')
    for ref_elm in ref_elms:
        root_elm.remove(ref_elm)
    # insert reference
    ref_elm1 = etree.Element(
        f'{{{ns_uri}}}externalReferenceOfSpatialID'
    )
    ref_elm2 = etree.Element(
        f'{{{ns_uri}}}fileLocation'
    )
    ref_elm2.text = id_file_rel
    ref_elm1.append(ref_elm2)
    root_elm.append(ref_elm1)


def output_xml(xml: etree.ElementTree, output_file: str) -> None:
    """write xml file

    Args:
        xml (etree.ElementTree): CityGML
        output_file (str): path to the output CityGML file (*.gml)'
    """
    # format
    etree.indent(
        xml.getroot(),
        space='\t'
    )

    # do output
    xml.write(
        output_file,
        encoding='UTF-8',
        pretty_print=True,
        xml_declaration=False,
        doctype='<?xml version="1.0" encoding="UTF-8"?>'
    )


def get_output_element_info_file(xml_file: str) -> Tuple[str, str, str, str]:
    """get spatial ID element informations

    Args:
        xml_file (str): path to the XML file

    Returns:
        Tuple[str, str, str, str]: spatial ID element informations
    """
    xml = inputs.load_xml(xml_file)
    return get_output_element_info_doc(xml)


def get_output_element_info_doc(xml: etree.ElementTree) -> Tuple[str, str, str, str]:
    """get spatial ID element informations

    Args:
        xml (etree.ElementTree): CityGML

    Returns:
        Tuple[str, str, str, str]: spatial ID element informations
    """
    com_elm = xml.find(
        '//{*}cityObjectMember'
    )
    if com_elm is None:
        return None
    fc_elm = com_elm.getchildren()[0]
    fc_name = etree.QName(fc_elm.tag).localname
    elem_info = get_output_element_info(fc_name)
    if elem_info is None:
        return None
    return elem_info


def get_output_element_info(fc_name: str) -> Tuple[str, str, str, str]:
    """get spatial ID element informations

    Args:
        fc_name (str): feature class name

    Returns:
        Tuple[str, str, str, str]: spatial ID element informations
    """
    global OUTPUT_ELEMENT_INFO
    if OUTPUT_ELEMENT_INFO is None:
        OUTPUT_ELEMENT_INFO = {}
        info_file = os.path.join(
            os.path.dirname(__file__),
            'resources',
            'spatial_id.csv'
        )
        with open(info_file, encoding='utf-8') as f:
            for line in f:
                _fc, _prefix, _output, *_afters = line.strip().split(',')
                _afters = [_ for _ in _afters if _] or None
                OUTPUT_ELEMENT_INFO[_fc] = (_prefix, _output, _afters)
    return OUTPUT_ELEMENT_INFO.get(fc_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('citygml_file_or_dir', help='path to the CityGML file (*.gml) or directory')
    parser.add_argument('id_file_or_dir', help='path to the ID pair list file (*.csv) or directory')
    parser.add_argument('output_file_or_dir', help='path to the output CityGML file (*.gml) or directory')
    parser.add_argument('--spatialid', choices=constants.SPATIALID_LIST, default=constants.SPATIALID_BOTH, help='form of SpatialIDs')
    args = parser.parse_args()
    main(
        citygml_file_or_dir=args.citygml_file_or_dir,
        id_file_or_dir=args.id_file_or_dir,
        output_file_or_dir=args.output_file_or_dir,
        output_form=args.spatialid
    )
