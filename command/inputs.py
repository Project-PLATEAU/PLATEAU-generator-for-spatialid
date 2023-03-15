import glob
import json
import logging
import os
import tempfile
import typing

from lxml import etree

import constants
import prepare

Any = typing.Any
Dict = typing.Dict
List = typing.List
Tuple = typing.Tuple
Iterator = typing.Iterator

logger = logging.getLogger(__name__)


def load_xml(input_file: str, ns_prefix: str = None) -> etree.ElementTree:
    """load XML file

    Args:
        input_file (str): path to the XML file
        ns_prefix (str, optional): extra namespace declaration. Defaults to None.

    Returns:
        etree.ElementTree: XML document
    """
    if ns_prefix:
        fd, tmp_file = tempfile.mkstemp('.gml')
        os.close(fd)
        with open(input_file, encoding='utf-8') as f:
            org_doc = f.read()
            new_doc = prepare.arrange_namespace(org_doc, ns_prefix)
        with open(tmp_file, 'w', encoding='utf-8') as f:
            f.write(new_doc)
        xml = etree.parse(tmp_file)
        os.remove(tmp_file)
    else:
        xml = etree.parse(input_file)
    return xml


def load_features(input_file: str, ids: Tuple[str], lod: int, crs: int,
                  debug: bool = False
                  ) -> Iterator[Tuple[List[List[List[float]]], Dict[str, Any]]]:
    """load CityGML features

    Args:
        input_file (str): path to the CityGML file (*.gml)
        ids (Tuple[str]): gml:ids which will be filtered
        lod (int): maximum LOD of target geometries
        crs (int): coordinate reference system of the output features
        debug (bool): whether output debug messages and retain temporary files or not

    Raises:
        ValueError: parameter error

    Yields:
        Iterator[Tuple[List[List[List[float]]], Dict[str, Any]]]: features
    """
    fd, geojson_file = tempfile.mkstemp('.json')
    os.close(fd)

    prepare.main(
        input_file,
        geojson_file,
        lod=lod,
        crs=crs,
        ids=ids,
        debug=debug
    )

    with open(geojson_file, encoding='utf-8') as f:
        dataset = json.load(f)
        for feature in dataset['features']:
            props = feature['properties']
            ft_geom = feature['geometry']
            geom_type = ft_geom['type']
            if geom_type == 'MultiPolygon':
                geoms = ft_geom['coordinates']
            elif geom_type == 'Polygon':
                geoms = [ft_geom['coordinates']]
            elif geom_type == 'MultiLineString':
                geoms = [[l] for l in ft_geom['coordinates']]
            elif geom_type == 'LineString':
                geoms = [[ft_geom['coordinates']]]
            else:
                raise ValueError(f'Invalid geometry type: {geom_type}')
            for geom in geoms:
                yield geom, props

    logger.debug(f'geojson file: {geojson_file}')
    if not debug:
        os.remove(geojson_file)


def load_ids(input_file: str, ids: Tuple[str] = None
            ) -> Iterator[Tuple[str, str, str, int, bool]]:
    """load ID pair list

    Args:
        input_file (str): path to the ID pair list file (*.csv)
        ids (Tuple[str], optional): gml:ids which will be filtered. Defaults to None.

    Raises:
        ValueError: parameter error

    Yields:
        Iterator[Tuple[str, str, str, int, bool]]: ID pair, property, max_zoom_level, merged
    """
    id_set = set(ids or [])
    with open(input_file, encoding='utf-8') as f:
        # skip header
        header1 = f.readline()
        max_zoom_level = None
        merged = None
        if header1.startswith(constants.CSV_CODE):
            tokens = header1.strip().split(',')
            max_zoom_level = int(tokens[2])
            merged = tokens[3] == '1'
            header2 = f.readline()
        else:
            header2 = header1
        if not header2.startswith('gml_id'):
            raise ValueError(f'Invalid header: {header2}')
        for line in f:
            line = line.strip()
            tokens = line.split(',')
            if len(tokens) < 2:
                raise ValueError(f'Invalid line: {line}')
            elif len(tokens) == 2:
                gml_id, spatial_id = tokens
                property = None
            elif len(tokens) == 3:
                gml_id, spatial_id, property = tokens
            else:
                raise ValueError(f'Invalid line: {line}')
            if id_set and gml_id not in id_set:
                continue
            yield gml_id, spatial_id, property, max_zoom_level, merged


def get_target_gml_files(input_dir: str) -> List[str]:
    """find *.gml recursively

    Args:
        input_dir (str): input directory

    Returns:
        List[str]: input files
    """
    input_pattern = os.path.join(input_dir, '**', '*.gml')
    input_files = list(sorted(glob.glob(input_pattern, recursive=True)))
    input_files = [
        input_file.replace(os.path.sep, '/')
        for input_file in input_files
    ]
    return input_files


def get_target_id_files(input_dir: str) -> List[str]:
    """find spatialid/*.csv recursively

    Args:
        input_dir (str): input directory

    Returns:
        List[str]: input files
    """
    input_pattern = os.path.join(input_dir, '**', constants.CSV_DIRECTORY, '*.csv')
    input_files = list(sorted(glob.glob(input_pattern, recursive=True)))
    input_files = [
        input_file.replace(os.path.sep, '/')
        for input_file in input_files
    ]
    return input_files
