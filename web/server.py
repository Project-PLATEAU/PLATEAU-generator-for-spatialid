import glob
import json
import logging
import math
import os
import typing
import uuid
import zipfile

import flask
from flask import request
import mapbox_vector_tile as mvt
import numpy as np
import pyproj as proj

import cleanup

app = flask.Flask(__name__)

Any = typing.Any
Dict = typing.Dict
List = typing.List
Tuple = typing.Tuple
Callable = typing.Callable

MAX_VOXELS = 200000
CSV_CODE = 'PLATEAU_3D-Spatial-ID_CSV'

ROOT_DIR = os.path.dirname(__file__)
TEMP_DIR = os.environ.get('VIEWER_TEMP', os.path.join(ROOT_DIR, 'temp'))

logger = logging.getLogger(__name__)


@app.route('/')
def index():
    return flask.send_file('./static/index.html')


@app.route('/temp/<path:path>')
def temp(path):
    return flask.send_file(os.path.join(TEMP_DIR, path))


@app.route('/upload/tiles', methods=['POST'])
def upload_tiles():
    if not request.files or 'file' not in request.files:
        return {
            'status': 'ERROR',
            'message': 'Invalid file',
        }
    uploaded_file = request.files['file']
    if not uploaded_file:
        return {
            'status': 'ERROR',
            'message': 'Empty file',
        }
    filename = uploaded_file.filename
    stem, ext = os.path.splitext(filename)
    temp_id = uuid.uuid4().hex
    temp_dir = os.path.join(TEMP_DIR, temp_id)
    os.makedirs(temp_dir)
    org_file = os.path.join(temp_dir, filename)
    uploaded_file.save(org_file)

    if ext != '.zip':
        return {
            'status': 'ERROR',
            'message': 'Invalid extension',
        }

    # viewing data
    try:
        tiles_name = stem
        tiles_dir = os.path.join(temp_dir, tiles_name)
        rel_url, bbox = build_tiles(org_file, tiles_dir)
        result = {
            'status': 'OK',
            'url': f'temp/{temp_id}/{tiles_name}/{rel_url}',
            'bbox': bbox,
        }
    except Exception as e:
        result = {
            'status': 'ERROR',
            'message': f'Failed to build tiles: {e}',
        }

    return result


def build_tiles(zip_file: str, tiles_dir: str) -> Tuple[str, List[float]]:
    """build 2D / 3D tiles

    Args:
        zip_file (str): zip archive of the tiles
        tiles_dir (str): directory to extract tile files

    Raises:
        ValueError: invalid parameter

    Returns:
        Tuple[str, List[float]]: url, bbox
    """
    os.makedirs(tiles_dir, exist_ok=True)
    with zipfile.ZipFile(zip_file) as z:
        z.extractall(tiles_dir)
    tile_files, is_3d = find_tiles(tiles_dir)
    if is_3d:
        tile_file, bbox = _build_tiles_3d(tiles_dir, tile_files)
    else:
        tile_file, bbox = _build_tiles_2d(tiles_dir, tile_files)
    abs_dir = os.path.abspath(os.path.normpath(tiles_dir))
    rel_url = os.path.abspath(os.path.normpath(tile_file))[len(abs_dir)+1:]
    rel_url = rel_url.replace(os.path.sep, '/')
    return rel_url, bbox


def find_tiles(tiles_dir: str) -> Tuple[List[str], bool]:
    """find 2D / 3D tiles file

    Args:
        tiles_dir (str): directory to find

    Raises:
        ValueError: invalid parameter

    Returns:
        Tuple[List[str], bool]: found tiles, 3D Tiles or not
    """
    pattern = os.path.join(tiles_dir, '**', '*.*')
    tiles = [
        entry.replace(os.path.sep, '/')
        for entry in glob.glob(pattern, recursive=True)
        if entry.endswith('tileset.json') or entry.endswith('.mvt')
    ]
    tiles.sort(key=lambda x: len(x.split('/')))
    if len(tiles) == 0:
        raise ValueError('Tile data not found')
    is_3d = tiles[0].endswith('tileset.json')
    return tiles, is_3d


def _build_tiles_2d(tiles_dir: str, tile_files: List[str]) -> Tuple[str, List[float]]:
    """build GeoJSON from Mapbox Vector Tile

    Args:
        tiles_dir (str): tiles directory
        tile_files (List[str]): tile file paths

    Returns:
        Tuple[str, List[float]]: JSON file path, bounding box
    """
    json_file = os.path.join(tiles_dir, 'tile.json')
    min_zoom_level = 9999
    max_zoom_level = -1
    for mvt_file in tile_files:
        iz, ix, iy = [
            int(s)
            for s in mvt_file.replace('.mvt', '').replace(os.path.sep, '/').split('/')[-3:]
        ]
        min_zoom_level = min(min_zoom_level, iz)
        max_zoom_level = max(max_zoom_level, iz)
    transformer = proj.Transformer.from_crs(3857, 4326, always_xy=True)
    # select appropriate zoom level
    zoom_level = max_zoom_level
    min_x = math.inf
    max_x = -math.inf
    min_y = math.inf
    max_y = -math.inf
    with open(json_file, 'a', encoding='utf-8') as fo:
        count = 0
        fo.write('{"type":"FeatureCollection","features":[')
        fo.write('\n')
        for mvt_file in tile_files:
            iz, ix, iy = [
                int(s)
                for s in mvt_file.replace('.mvt', '').replace(os.path.sep, '/').split('/')[-3:]
            ]
            if iz != zoom_level:
                continue
            with open(mvt_file, 'rb') as fi:
                data = fi.read()
            decoded_data = mvt.decode(data)
            feature_collections = decoded_data.values()
            for feature_collection in feature_collections:
                extent = feature_collection.get('extent')
                features = feature_collection.get('features', [])
                num_features = len(features)
                if num_features > 0:
                    if count > 0:
                        fo.write(',')
                        fo.write('\n')
                    for index, feature in enumerate(features):
                        arranged_feature, bbox = _arrange_feature_2d(
                            feature,
                            iz,
                            ix,
                            iy,
                            extent,
                            transformer
                        )
                        min_x = min(min_x, bbox[0])
                        min_y = min(min_y, bbox[1])
                        max_x = max(max_x, bbox[2])
                        max_y = max(max_y, bbox[3])
                        json.dump(arranged_feature, fo, ensure_ascii=False)
                        if index < num_features - 1:
                            fo.write(',')
                            fo.write('\n')
                count += num_features
        fo.write('\n')
        fo.write(']}')
        fo.write('\n')
    bbox = [min_x, min_y, max_x, max_y]
    return json_file, bbox


def _arrange_feature_2d(feature: Dict[str, Any], z: int, x: int, y: int,
                        extent: int, transformer: proj.Transformer
                        ) -> Tuple[Dict[str, Any], List[float]]:
    """arrange properties and geometries of the feature

    Args:
        feature (Dict[str, Any]): GeoJSON Feature
        z (int): tile index
        x (int): tile index
        y (int): tile index
        extent (int): tile extent
        transformer (proj.Transformer): coordinate transformer

    Returns:
        Tuple[Dict[str, Any], List[float]]: arranged GeoJSON Feature, bounding box
    """
    arranged_geometry, bbox = _arrange_geometry_2d(
        feature.get('geometry', {}),
        z,
        x,
        y,
        extent,
        transformer
    )
    arranged_feature = {
        'type': 'Feature',
        'properties': {},
        'geometry': arranged_geometry,
    }
    for name, value in feature.get('properties', {}).items():
        if name == 'attributes':
            attributes = json.loads(value)
            for _name, _value in attributes.items():
                arranged_feature['properties'][_name] = _value
        else:
            arranged_feature['properties'][name] = value
    return arranged_feature, bbox


def _arrange_geometry_2d(geometry: Dict[str, Any], z: int, x: int, y: int,
                         extent: int, transformer: proj.Transformer
                         ) -> Tuple[Dict[str, Any], List[float]]:
    """arrange geometries of the feature

    Args:
        geometry (Dict[str, Any]): GeoJSON geometry
        z (int): tile index
        x (int): tile index
        y (int): tile index
        extent (int): tile extent
        transformer (proj.Transformer): coordinate transformer

    Raises:
        ValueError: invalid parameter

    Returns:
        Tuple[Dict[str, Any], List[float]]: arranged GeoJSON geometry, bounding box
    """
    # size, offset
    l0 = 2 * math.pi * 6378137.0
    size = l0 / 2 ** z
    ix = x - int(2 ** (z - 1))
    iy = (1 << max(z - 1, 0)) - y - 1
    offset_x = size * ix
    offset_y = size * iy

    geom_type = geometry['type']
    arranged_geometry = {
        'type': geom_type,
    }
    coordinates = geometry['coordinates']
    if geom_type == 'MultiPolygon':
        coordinates = coordinates
    elif geom_type == 'Polygon':
        coordinates = [coordinates]
    elif geom_type == 'MultiLineString':
        coordinates = [coordinates]
    elif geom_type == 'LineString':
        coordinates == [[coordinates]]
    else:
        raise ValueError(f'Invalid geometry type: {geom_type}')
    ar_coordinates = []
    min_x = math.inf
    max_x = -math.inf
    min_y = math.inf
    max_y = -math.inf
    for polygon in coordinates:
        ar_polygon = []
        for ring in polygon:
            ar_ring = np.array(ring, dtype=np.float64)
            ar_ring = ar_ring / float(extent) * size
            ar_ring[:, 0] += offset_x
            ar_ring[:, 1] += offset_y
            # transform 3857 -> 4326
            ar_x, ar_y = transformer.transform(ar_ring[:, 0], ar_ring[:, 1])
            min_x = min(min_x, np.min(ar_x))
            min_y = min(min_y, np.min(ar_y))
            max_x = max(max_x, np.max(ar_x))
            max_y = max(max_y, np.max(ar_y))
            ar_ring = np.stack((ar_x, ar_y), axis=1)
            ar_polygon.append(ar_ring)
        ar_coordinates.append(ar_polygon)
    arranged_coordinates = [
        [
            ar_ring.tolist()
            for ar_ring in ar_polygon
        ]
        for ar_polygon in ar_coordinates
    ]
    if geom_type == 'MultiPolygon':
        arranged_coordinates = arranged_coordinates
    elif geom_type == 'Polygon':
        arranged_coordinates = arranged_coordinates[0]
    elif geom_type == 'MultiLineString':
        arranged_coordinates = arranged_coordinates[0]
    elif geom_type == 'LineString':
        arranged_coordinates = arranged_coordinates[0][0]
    arranged_geometry['coordinates'] = arranged_coordinates
    bbox = [min_x, min_y, max_x, max_y]
    return arranged_geometry, bbox


def _build_tiles_3d(tiles_dir: str, tile_files: List[str]) -> Tuple[str, List[float]]:
    """build 3D Tiles

    Args:
        tiles_dir (str): tiles directory
        tile_files (List[str]): tile file paths

    Returns:
        Tuple[str, List[float]]: JSON file path, bounding box
    """
    tile_file = tile_files[0]
    bbox = None
    if os.path.isfile(tile_file):
        with open(tile_file, encoding='utf-8') as f:
            tileset_info = json.load(f)
            bounding_volume = tileset_info.get('root', {}).get('boundingVolume', {})
            if bounding_volume:
                region = bounding_volume.get('region', [])
                if region:
                    bbox = [
                        math.degrees(region[0]),
                        math.degrees(region[1]),
                        math.degrees(region[2]),
                        math.degrees(region[3]),
                        region[4],
                        region[5],
                    ]
                else:
                    raise ValueError(f'Invalid bounding volume: {list(bounding_volume.keys())[0]}')
    return tile_file, bbox


@app.route('/upload/csv', methods=['POST'])
def upload_csv():
    if not request.files or 'file' not in request.files:
        return {
            'status': 'ERROR',
            'message': 'Invalid file',
        }
    uploaded_file = request.files['file']
    if not uploaded_file:
        return {
            'status': 'ERROR',
            'message': 'Empty file',
        }
    filename = uploaded_file.filename
    stem, ext = os.path.splitext(filename)
    temp_id = uuid.uuid4().hex
    temp_dir = os.path.join(TEMP_DIR, temp_id)
    os.makedirs(temp_dir)
    org_file = os.path.join(temp_dir, filename)
    uploaded_file.save(org_file)

    if ext != '.csv':
        return {
            'status': 'ERROR',
            'message': 'Invalid extension',
        }

    # viewing data
    try:
        box_name = f'{stem}.json'
        box_file = os.path.join(temp_dir, box_name)
        data, bbox, total, loaded = build_box(org_file, box_file)
        result = {
            'status': 'OK',
            'bbox': bbox,
            'data': data,
            'total': total,
            'loaded': loaded,
        }
    except Exception as e:
        logger.exception(e)
        result = {
            'status': 'ERROR',
            'message': 'Failed to build Boxes',
        }
    return result


def build_box(csv_file: str, box_file: str) -> Tuple[List[Dict[str, Any]], List[float], int, int]:
    """build 2D / 3D boxes

    Args:
        csv_file (str): input .csv file path
        box_file (str): output .json file path

    Raises:
        ValueError: invalid parameter

    Returns:
        Tuple[List[Dict[str, Any]], List[float], int, int]: boxes, bounding box, number of total records, number of loaded records
    """
    id_dict = {}
    total = 0
    loaded = 0
    with open(csv_file, encoding='utf-8') as f:
        # skip header
        header1 = f.readline()
        if header1.startswith(CSV_CODE):
            header2 = f.readline()
        else:
            header2 = header1
        if not header2.startswith('gml_id'):
            raise ValueError(f'Invalid header: {header2}')
        for line in f:
            total += 1
            if loaded >= MAX_VOXELS:
                continue
            loaded += 1
            line = line.strip()
            tokens = line.split(',')
            if len(tokens) != 2:
                raise ValueError(f'Invalid line: {line}')
            gml_id, spatial_id = tokens
            id_dict.setdefault(spatial_id, set()).add(gml_id)
    l0_x = 2 * math.pi * 6378137.0
    l0_y = l0_x
    l0_z = 2 ** 25
    nodes_3d = []
    nodes_2d = []
    sizes_3d = []
    sizes_2d = []
    sids_3d = []
    sids_2d = []
    gidss_3d = []
    gidss_2d = []
    for sid, gids in id_dict.items():
        lv, iz, ix, iy = decode_sid(sid)
        sz_x = l0_x / 2 ** lv
        sz_y = l0_y / 2 ** lv
        sz_z = l0_z / 2 ** lv
        if iz is None:
            # 2D
            node = [
                ix * sz_x + sz_x / 2,
                iy * sz_y + sz_y / 2,
            ]
            size = [sz_x, sz_y]
            nodes_2d.append(node)
            sizes_2d.append(size)
            sids_2d.append(sid)
            gidss_2d.append(list(gids))
        else:
            # 3D
            node = [
                ix * sz_x + sz_x / 2,
                iy * sz_y + sz_y / 2,
                iz * sz_z + sz_z / 2,
            ]
            size = [sz_x, sz_y, sz_z]
            nodes_3d.append(node)
            sizes_3d.append(size)
            sids_3d.append(sid)
            gidss_3d.append(list(gids))
    # 2D
    boxes_2d, bbox_2d = _build_box_2d(nodes_2d, sizes_2d, sids_2d, gidss_2d)
    # 3D
    boxes_3d, bbox_3d = _build_box_3d(nodes_3d, sizes_3d, sids_3d, gidss_3d)

    # 2D / 3D
    bbox = [
        min(bbox_2d[0], bbox_3d[0]),
        min(bbox_2d[1], bbox_3d[1]),
        max(bbox_2d[2], bbox_3d[2]),
        max(bbox_2d[3], bbox_3d[3]),
    ]
    if not math.isinf(bbox_3d[4]) and not math.isinf(bbox_3d[5]):
        bbox.extend([
            bbox_3d[4],
            bbox_3d[5],
        ])
    boxes = {
        'rectangles': boxes_2d,
        'boxes': boxes_3d,
    }
    with open(box_file, 'w', encoding='utf-8') as f:
        json.dump(boxes, f)
    return boxes, bbox, total, loaded


def _build_box_2d(nodes_2d: List[List[float]], sizes_2d: List[List[float]],
                  sids_2d: List[str], gidss_2d: List[List[str]]
                  ) -> Tuple[List[Dict[str, Any]], List[float]]:
    """build 2D boxes

    Args:
        nodes_2d (List[List[float]]): coordinates
        sizes_2d (List[List[float]]): box sizes
        sids_2d (List[str]): list of Spatial ID
        gidss_2d (List[List[str]]): list of list of gml:id

    Returns:
        Tuple[List[Dict[str, Any]], List[float]]: boxes, bounding box
    """
    if len(nodes_2d) == 0 or len(sizes_2d) == 0:
        boxes = None
        bbox = [
            +math.inf,
            +math.inf,
            -math.inf,
            -math.inf,
        ]
    else:
        a_nodes = np.array(nodes_2d, dtype=np.float64)
        a_sizes = np.array(sizes_2d, dtype=np.float64)
        rectangles, bbox = transform_2d(a_nodes, a_sizes)
        boxes = [
            {
                'rectangle': rectangle,
                'sid': sid,
                'gids': gids,
            }
            for rectangle, sid, gids
            in zip(rectangles.tolist(), sids_2d, gidss_2d)
        ]
    return boxes, bbox


def _build_box_3d(nodes_3d: List[List[float]], sizes_3d: List[List[float]],
                  sids_3d: List[str], gidss_3d: List[List[str]]
                  ) -> Tuple[List[Dict[str, Any]], List[float]]:
    """build 3D boxes

    Args:
        nodes_3d (List[List[float]]): coordinates
        sizes_3d (List[List[float]]): box sizes
        sids_3d (List[str]): list of Spatial ID
        gidss_3d (List[List[str]]): list of list of gml:id

    Returns:
        Tuple[List[Dict[str, Any]], List[float]]: boxes, bounding box
    """
    if len(nodes_3d) == 0 or len(sizes_3d) == 0:
        boxes = None
        bbox = [
            +math.inf,
            +math.inf,
            -math.inf,
            -math.inf,
            +math.inf,
            -math.inf,
        ]
    else:
        a_nodes = np.array(nodes_3d, dtype=np.float64)
        a_sizes = np.array(sizes_3d, dtype=np.float64)
        centers, bbox = transform_3d(a_nodes)
        box_sizes = get_box_size(a_nodes, a_sizes)
        boxes = [
            {
                'center': center,
                'size': size,
                'sid': sid,
                'gids': gids,
            }
            for center, size, sid, gids
            in zip(centers.tolist(), box_sizes.tolist(), sids_3d, gidss_3d)
        ]
    return boxes, bbox


def decode_sid(sid: str) -> List[int]:
    """decode Spatial ID

    Args:
        sid (str): Spatial ID

    Returns:
        List[int]: coordinate index
    """
    tokens = sid.split('/')
    if len(tokens) == 3:
        lv, gix, giy = [int(t) for t in tokens]
        giz = None
    elif len(tokens) == 4:
        lv, giz, gix, giy = [int(t) for t in tokens]
    else:
        raise ValueError(f'Invalid 3D Spatial ID: {sid}')
    ix = gix - int(2 ** (lv - 1))
    iy = (1 << max(lv - 1, 0)) - giy - 1
    iz = giz
    return [lv, iz, ix, iy]


def transform_2d(nodes: np.ndarray, sizes: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[float]]:
    """2D coordinate transformation

    Args:
        nodes (np.ndarray): coordinates (EPSG:3857)
        sizes (np.ndarray): box sizes in meters

    Returns:
        Tuple[np.ndarray, np.ndarray, List[float]]: rectangles (radian), bounding box
    """
    # corner: 3857 -> 4326
    transformer = proj.Transformer.from_crs(3857, 4326, always_xy=True)
    min_xy = nodes - sizes / 2
    max_xy = nodes + sizes / 2
    min_lons, min_lats = transformer.transform(min_xy[:, 0], min_xy[:, 1])
    max_lons, max_lats = transformer.transform(max_xy[:, 0], max_xy[:, 1])

    bbox = [
        np.min(min_lons),
        np.min(min_lats),
        np.max(max_lons),
        np.max(max_lats),
    ]

    min_lons_radian = np.radians(min_lons)
    min_lats_radian = np.radians(min_lats)
    max_lons_radian = np.radians(max_lons)
    max_lats_radian = np.radians(max_lats)

    rectangles = np.stack([
        min_lons_radian,
        min_lats_radian,
        max_lons_radian,
        max_lats_radian,
    ], axis=1)

    return rectangles, bbox


def transform_3d(nodes: np.ndarray) -> Tuple[np.ndarray, List[float]]:
    """3D coordinate transformation

    Args:
        nodes (np.ndarray): coordinates (EPSG:3857)

    Returns:
        Tuple[np.ndarray, List[float]]: transformed coordinates (EPSG:4978), bounding box
    """
    # 3857 -> 4978
    (xs, ys, zs), bbox = _transform_3d(
        nodes[:, 0],
        nodes[:, 1],
        nodes[:, 2]
    )
    points = np.stack((xs, ys, zs), axis=1)

    return points, bbox


def _transform_3d(xs: np.ndarray, ys: np.ndarray, zs: np.ndarray
                  ) -> Tuple[Tuple[np.ndarray, np.ndarray, np.ndarray], List[float]]:
    """3D coordinate transformation

    Args:
        nodes (np.ndarray): coordinates (EPSG:3857)

    Returns:
        Tuple[Tuple[np.ndarray, np.ndarray, np.ndarray], List[float]]: transformed coordinates (EPSG:4978)
    """
    # 3857 -> 5773
    transformer = proj.Transformer.from_crs(3857, 5773, always_xy=True)
    lats, lons, geoid_height_diffs = transformer.transform(
        xs,
        ys,
        np.zeros(xs.shape[0])
    )
    alts = zs - geoid_height_diffs

    # 4326 + geoid height -> 4978
    transformer = proj.Transformer.from_crs(4326, 4978, always_xy=True)
    new_xs, new_ys, new_zs = transformer.transform(lons, lats, alts)

    bbox = [
        np.min(lons),
        np.min(lats),
        np.max(lons),
        np.max(lats),
        np.min(alts),
        np.max(alts),
    ]

    return (new_xs, new_ys, new_zs), bbox


def get_box_size(centers_3857: np.ndarray, sizes_3857: np.ndarray) -> np.ndarray:
    """get sizes (EPSG:4978) from centers and sizes (EPSG:3857)

    Args:
        centers_3857 (np.ndarray): centers (EPSG:3857)
        sizes_3857 (np.ndarray): sizes (EPSG:3857)

    Returns:
        np.ndarray: sizes (EPSG:4978)
    """
    min_points_3857 = centers_3857 - sizes_3857 / 2
    (min_points_x_4978, min_points_y_4978, min_points_z_4978), _ = _transform_3d(
        min_points_3857[:, 0],
        min_points_3857[:, 1],
        min_points_3857[:, 2],
    )
    (max_points_xx_4978, max_points_xy_4978, max_points_xz_4978), _ = _transform_3d(
        min_points_3857[:, 0] + sizes_3857[:, 0],
        min_points_3857[:, 1],
        min_points_3857[:, 2],
    )
    (max_points_yx_4978, max_points_yy_4978, max_points_yz_4978), _ = _transform_3d(
        min_points_3857[:, 0],
        min_points_3857[:, 1] + sizes_3857[:, 1],
        min_points_3857[:, 2],
    )
    (max_points_zx_4978, max_points_zy_4978, max_points_zz_4978), _ = _transform_3d(
        min_points_3857[:, 0],
        min_points_3857[:, 1],
        min_points_3857[:, 2] + sizes_3857[:, 2],
    )
    diff_x_4978 = np.stack((
        max_points_xx_4978 - min_points_x_4978,
        max_points_xy_4978 - min_points_y_4978,
        max_points_xz_4978 - min_points_z_4978,
    ), axis=1)
    diff_y_4978 = np.stack((
        max_points_yx_4978 - min_points_x_4978,
        max_points_yy_4978 - min_points_y_4978,
        max_points_yz_4978 - min_points_z_4978,
    ), axis=1)
    diff_z_4978 = np.stack((
        max_points_zx_4978 - min_points_x_4978,
        max_points_zy_4978 - min_points_y_4978,
        max_points_zz_4978 - min_points_z_4978,
    ), axis=1)
    sizes_x_4978 = np.linalg.norm(diff_x_4978, axis=1)
    sizes_y_4978 = np.linalg.norm(diff_y_4978, axis=1)
    sizes_z_4978 = np.linalg.norm(diff_z_4978, axis=1)
    sizes_4978 = np.stack((
        sizes_x_4978,
        sizes_y_4978,
        sizes_z_4978
    ), axis=1)
    return sizes_4978


cleanup.main()
