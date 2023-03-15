import argparse
import copy
import json
import logging
import os
import re
import tempfile
import typing

import lxml.etree as etree
import pyproj as proj

import constants

Any = typing.Any
Set = typing.Set
Dict = typing.Dict
List = typing.List
Tuple = typing.Tuple
Iterator = typing.Iterator

logger = logging.getLogger(__name__)

GEOMETRY_PATHS = None


def main(input_file: str, output_file: str, lod: int = 3, crs: int = None,
         ids: Tuple[str] = None, debug: bool = False) -> None:
    """prepare to load CityGML

    Args:
        input_file (str): path to the CityGML file (*.gml)
        output_file (str): path to the temporary GeoJSON file (*.json)
        lod (int, optional): maximum LOD of target geometries. Defaults to 3.
        crs (int, optional): coordinate reference system of the output features. Defaults to None.
        ids (Tuple[str], optional): gml:ids which will be filtered. Defaults to None.
        debug (bool, optional): whether output debug messages and retain temporary files or not. Defaults to False.

    Raises:
        ValueError: parameter error
    """
    input_ext = os.path.splitext(input_file)[-1]
    if input_ext.lower() not in {'.gml'}:
        raise ValueError(f'Not a CityGML file: {input_file}')
    output_ext = os.path.splitext(output_file)[-1]
    if output_ext.lower() not in {'.json', '.geojson'}:
        raise ValueError(f'Not a GeoJSON file: {input_file}')

    fd, resolved_file = tempfile.mkstemp('.gml')
    os.close(fd)

    resolve_xlink(input_file, resolved_file)
    extract_geometry(resolved_file, output_file, lod, crs, ids)

    logger.debug(f'resolved file: {resolved_file}')
    if not debug:
        os.remove(resolved_file)


def resolve_xlink(input_file: str, output_file: str) -> None:
    """resolve and expand xlink in CityGML

    Args:
        input_file (str): path to the original CityGML file (*.gml)
        output_file (str): path to the resolved CityGML file (*.gml)
    """
    doc = etree.parse(input_file)
    id_elms = doc.findall(
        '//*[@gml:id]',
        namespaces={
            'gml': 'http://www.opengis.net/gml',
        }
    )
    id_map = {}
    for id_elm in id_elms:
        gml_id = id_elm.attrib['{http://www.opengis.net/gml}id']
        elm_copy = copy.deepcopy(id_elm)
        del elm_copy.attrib['{http://www.opengis.net/gml}id']
        id_elms_copy = elm_copy.findall(
            './/*[@gml:id]',
            namespaces={
                'gml': 'http://www.opengis.net/gml',
            }
        )
        for id_elm_copy in id_elms_copy:
            del id_elm_copy.attrib['{http://www.opengis.net/gml}id']
        id_map[gml_id] = elm_copy
    ref_elms = doc.findall(
        '//*[@xlink:href]',
        namespaces={
            'xlink': 'http://www.w3.org/1999/xlink',
        }
    )
    for elm in ref_elms:
        href = elm.attrib['{http://www.w3.org/1999/xlink}href']
        if href[0] != '#':
            continue
        href_id = href[1:]
        if href_id in id_map:
            child = copy.deepcopy(id_map[href_id])
            elm.append(child)
            del elm.attrib['{http://www.w3.org/1999/xlink}href']

    doc.write(
        output_file,
        encoding='UTF-8',
        pretty_print=True,
        xml_declaration=False,
        doctype='<?xml version="1.0" encoding="UTF-8"?>'
    )


def extract_geometry(input_file: str, output_file: str, lod: int, crs: int,
                     ids: Tuple[str]) -> None:
    """extract geometries from the specified CityGML and write to GeoJSON file

    Args:
        input_file (str): path to the resolved CityGML file (*.gml)
        output_file (str): path to the temporary GeoJSON file (*.json)
        lod (int): maximum LOD of target geometries
        crs (int): coordinate reference system of the output features
        ids (Tuple[str]): gml:ids which will be filtered
    """
    id_set = set(ids or [])
    doc = etree.parse(input_file)
    root = doc.getroot()
    id_elms = root.findall(
        './*/*[@gml:id]',
        namespaces={
            'gml': 'http://www.opengis.net/gml',
        }
    )
    features = []
    feature_collection = {
        'type': 'FeatureCollection',
        'features': features,
    }
    crs_from = proj.CRS.from_epsg(4326)
    crs_to = proj.CRS.from_epsg(crs)
    transformer = proj.Transformer.from_crs(crs_from, crs_to, always_xy=True)
    for id_elm in id_elms:
        fc_name = etree.QName(id_elm.tag).localname
        geom_paths = get_geometry_paths(fc_name)
        if not geom_paths:
            continue
        gml_id = id_elm.attrib['{http://www.opengis.net/gml}id']
        if id_set and gml_id not in id_set:
            continue
        geoms = []
        geom_dim = None
        default_geom_paths = geom_paths.get(None, [])
        for _lod in range(lod, -1, -1):
            found = False
            actual_geom_paths = default_geom_paths or geom_paths.get(_lod, [])
            for geom_path, _dim in actual_geom_paths:
                geom_elms = id_elm.findall(geom_path)
                if len(geom_elms) > 0:
                    geoms.extend(geom_elms)
                    geom_dim = _dim
                    logging.debug(geom_path)
                    found = True
            if found:
                break
        for geom in geoms:
            local_name = etree.QName(geom.tag).localname
            is_surface = (
                'surface' in local_name or
                'triangle' in local_name
            )
            geom_type = 'Polygon' if is_surface else 'LineString'
            geom_line = not is_surface
            pos_list = geom.findall(
                './/gml:posList',
                namespaces={
                    'gml': 'http://www.opengis.net/gml',
                }
            )
            exterior = []
            interiors = []
            for pos in pos_list:
                is_interior= etree.QName(pos.getparent().getparent().tag).localname == 'interior'
                if exterior and not is_interior:
                    features.append({
                        'type': 'Feature',
                        'properties': {
                            'gml_id': gml_id,
                            'fc_name': fc_name,
                            'geom_dim': geom_dim,
                            'geom_line': geom_line,
                        },
                        'geometry': {
                            'type': geom_type,
                            'coordinates': [exterior, *interiors],
                        }
                    })
                    exterior = []
                    interiors = []
                interior = []
                coordinates = [float(p) for p in pos.text.split(' ')]
                while coordinates:
                    lat = coordinates.pop(0)
                    lon = coordinates.pop(0)
                    z = coordinates.pop(0)
                    x, y = transformer.transform(lon, lat)
                    if is_interior:
                        interior.append([x, y, z])
                    else:
                        exterior.append([x, y, z])
                if is_interior and interior:
                    interiors.append(interior)
            if exterior or interiors:
                features.append({
                    'type': 'Feature',
                    'properties': {
                        'gml_id': gml_id,
                        'fc_name': fc_name,
                        'geom_dim': geom_dim,
                        'geom_line': geom_line,
                    },
                    'geometry': {
                        'type': geom_type,
                        'coordinates': [exterior, *interiors],
                    }
                })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(feature_collection, f)


def get_geometry_paths(fc_name: str) -> Dict[int, Set[Tuple[str, int]]]:
    """get XPaths of the geometry elements of the specified feature class

    Args:
        fc_name (str): name of the feature class

    Returns:
        Dict[int, Set[Tuple[str, int]]]: set of XPaths
    """
    global GEOMETRY_PATHS
    if GEOMETRY_PATHS is None:
        GEOMETRY_PATHS = {}
        geom_file = os.path.join(
            os.path.dirname(__file__),
            'resources',
            'geometry.csv'
        )
        with open(geom_file, encoding='utf-8') as f:
            for line in f:
                _fc, _geom, _dim = (line.strip().split(',') + [None])[:3]
                _lod, _geom = arrange_path(_geom)
                _dim = _dim and int(_dim)
                lods = GEOMETRY_PATHS.setdefault(_fc, {})
                paths = lods.setdefault(_lod, set())
                paths.add((_geom, _dim))
    return GEOMETRY_PATHS.get(fc_name)


def arrange_path(path: str) -> Tuple[int, str]:
    """extract a lod info from an XPath

    Args:
        path (str): XPath

    Returns:
        Tuple[int, str]: (lod, XPath)
    """
    if path[:3] != './/':
        path = './/' + path
    path = re.sub(r'/(\w)', r'/{*}\1', path)
    m = re.search(r'lod([0-3])', path)
    if m:
        lod = int(m.group(1))
    else:
        lod = None
    return lod, path


def arrange_namespace(doc: str, ns_prefix: str) -> str:
    """arrange namespace declaration

    Args:
        doc (str): XML string
        ns_prefix (str): namespace prefix (`uro` or `urf`)

    Returns:
        str: arranged XML string
    """
    pattern = r'<(\S+)(\s+)(.+)(\s+)(\S+schemaLocation=")(.+)">'
    root_match = re.search(pattern, doc, flags=re.MULTILINE)
    if not root_match:
        return doc
    tag, spaces1, ns_decls_str, spaces2, locations_attr, locations_str = root_match.groups()
    ns_decls = re.split(r'\s+', ns_decls_str)
    locations = re.split(r'\s+', locations_str)

    ns_info = constants.NAMESPACES.get(ns_prefix)
    if not ns_info:
        return doc
    ns_uri = ns_info['uri']
    ns_loc = ns_info['location']

    if not any(ns_decl.endswith(f'="{ns_uri}"') for ns_decl in ns_decls):
        ns_decls.append(f'xmlns:{ns_prefix}="{ns_uri}"')

    if not any(location == ns_uri for location in locations):
        locations.insert(0, ns_uri)
        locations.insert(1, ns_loc)

    new_ns_decls_str = ' '.join(ns_decls)
    new_locations_str = ' '.join(locations)
    new_str = f'<{tag}{spaces1}{new_ns_decls_str}{spaces2}{locations_attr}{new_locations_str}">'
    new_doc = re.sub(pattern, new_str, doc, flags=re.MULTILINE)

    return new_doc


def arrange_namespace_file(xml_file: str, ns_prefix: str) -> str:
    """arrange namespace declaration

    Args:
        xml_file (str): path to the XML file
        ns_prefix (str): namespace prefix (`uro` or `urf`)

    Returns:
        str: arranged XML string
    """
    with open(xml_file, encoding='utf-8') as f:
        org_doc = f.read()
    new_doc = arrange_namespace(org_doc, ns_prefix)
    return new_doc


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('output_file')
    parser.add_argument('--crs', type=int, default=None)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    main(
        args.input_file,
        args.output_file,
        args.crs,
        args.debug
    )
