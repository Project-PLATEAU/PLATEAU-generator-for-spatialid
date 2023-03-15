import itertools
import math
import typing

import lxml.etree as etree
import pygeos as geos
import pyvista as vista
import pyvista._vtk as vtk

Any = typing.Any
Set = typing.Set
Dict = typing.Dict
List = typing.List
Tuple = typing.Tuple
Union = typing.Union
Iterator = typing.Iterable


def get(type: str, level: int = None, size: List[float] = None,
        crs: int = None) -> 'Grid':
    """get voxel grid instance

    Args:
        type (str): type of the voxel grid
        level (int, optional): zoom level of the voxel grid. Defaults to None.
        size (List[float], optional): size of the voxel grid. Defaults to None.
        crs (int, optional): coordinate reference system of the voxel grid. Defaults to None.

    Raises:
        ValueError: parameter error

    Returns:
        Grid: Voxel Grid instance
    """
    if type == 'zfxy':
        grid = ZFXYGrid(level=level)
    else:
        raise ValueError(f'Invalid grid type: {type}')
    return grid


class Grid(object):

    size_x: float = None
    size_y: float = None
    size_z: float = None

    crs: int = None
    output_crs: int = None

    def __init__(self, *args, **kwargs):
        self._data = {}

    @property
    def data(self) -> Dict[Tuple[float], Any]:
        return self._data

    def clear(self):
        self._data = {}

    def normalize_size(self, size: Union[float, List[float]]):
        if size is None:
            return None
        if isinstance(size, float):
            size = [size]
        normalized_size = size + (3 - len(size)) * [size[-1]]
        return normalized_size

    def encode_key(self, ix: int, iy: int, iz: int) -> str:
        return f'{ix}_{iy}_{iz}'

    def decode_key(self, key: str, full: bool = False) -> str:
        return (int(s) for s in key.split('_'))

    def load_geom_data(self,
                data: Iterator[Tuple[List[List[List[float]]], Dict[str, Any]]],
                interpolate: bool = False, merge: bool = False) -> None:
        with vista.utilities.VtkErrorCatcher(raise_errors=False, send_to_logging=False):
            for geom, props in data:
                self._update_by_geom(geom, props)

        # interpolate inner voxels
        if interpolate:
            self.interpolate()

        # merge small voxels
        if merge:
            self.merge()

    def _update_by_geom(self, geom: List[List[List[float]]],
                props: Dict[str, Any]) -> None:
        gml_id = props.get('gml_id')
        if not gml_id:
            raise ValueError('`gml_id` not found')
        if len(geom) == 0:
            raise ValueError('geometry contains no points')
        data = self._data.setdefault(gml_id, set())
        if props.get('geom_dim') == 3:
            self._update_by_geom_3d(data, geom, props)
        else:
            self._update_by_geom_2d(data, geom, props)

    def _update_by_geom_3d(self, data: Set[str],
                coordinates: List[List[List[float]]],
                props: Dict[str, Any]) -> None:
        exterior = coordinates[0]

        size_x = self.size_x
        size_y = self.size_y
        size_z = self.size_z

        # target
        abs_geom_vtk = self.build_geom_3d(exterior)

        bounds = abs_geom_vtk.bounds
        ix_min = math.floor(bounds[0] / size_x)
        ix_max = math.ceil(bounds[1] / size_x)
        iy_min = math.floor(bounds[2] / size_y)
        iy_max = math.ceil(bounds[3] / size_y)
        iz_min = math.floor(bounds[4] / size_z)
        iz_max = math.ceil(bounds[5] / size_z)
        offset_x = ix_min * size_x
        offset_y = iy_min * size_y
        offset_z = iz_min * size_z
        rel_geom_vtk = self.build_geom_3d([
            [
                x - offset_x,
                y - offset_y,
                z - offset_z
            ]
            for x, y, z in exterior
        ])
        rel_bounds = rel_geom_vtk.bounds
        collision_filter = self.build_collision_filter(rel_geom_vtk)
        voxel_geom_vtk = self.build_box_3d(
            cx=size_x/2,
            cy=size_y/2,
            cz=size_z/2,
            sx=size_x,
            sy=size_y,
            sz=size_z
        )
        matrix = vtk.vtkMatrix4x4()
        collision_filter.SetInputData(1, voxel_geom_vtk)
        collision_filter.SetMatrix(1, matrix)
        for rx in range(ix_max - ix_min + 1):
            for ry in range(iy_max - iy_min + 1):
                for rz in range(iz_max - iz_min + 1):
                    matrix.SetElement(0, 3, rx * size_x)
                    matrix.SetElement(1, 3, ry * size_y)
                    matrix.SetElement(2, 3, rz * size_z)
                    collision_filter.Update()
                    n_collision = collision_filter.GetNumberOfContacts()
                    if n_collision > 0:
                        key = self.encode_key(
                            ix_min + rx,
                            iy_min + ry,
                            iz_min + rz
                        )
                        data.add(key)
                    else:
                        voxel_bounds = (
                            rx * size_x,
                            rx * size_x + size_x,
                            ry * size_y,
                            ry * size_y + size_y,
                            rz * size_z,
                            rz * size_z + size_z
                        )
                        if (rel_bounds[0] >= voxel_bounds[0] and
                            rel_bounds[1] <= voxel_bounds[1] and
                            rel_bounds[2] >= voxel_bounds[2] and
                            rel_bounds[3] <= voxel_bounds[3] and
                            rel_bounds[4] >= voxel_bounds[4] and
                            rel_bounds[5] <= voxel_bounds[5]):

                            key = self.encode_key(
                                ix_min + rx,
                                iy_min + ry,
                                iz_min + rz
                            )
                            data.add(key)

    def _update_by_geom_2d(self, data: Set[str],
                coordinates: List[List[List[float]]],
                props: Dict[str, Any]) -> None:
        size_x = self.size_x
        size_y = self.size_y

        is_line = props.get('geom_line') or False

        # target
        abs_geom_geos = self.build_geom_2d(coordinates, is_line=is_line)

        bounds = geos.bounds(abs_geom_geos)
        ix_min = math.floor(bounds[0] / size_x)
        ix_max = math.ceil(bounds[2] / size_x)
        iy_min = math.floor(bounds[1] / size_y)
        iy_max = math.ceil(bounds[3] / size_y)
        offset_x = ix_min * size_x
        offset_y = iy_min * size_y
        rel_coordinates = [
            [
                [
                    x - offset_x,
                    y - offset_y,
                ]
                for x, y, _ in part
            ]
            for part in coordinates
        ]
        rel_geom_geos = self.build_geom_2d(rel_coordinates, is_line=is_line)
        geos.prepare(rel_geom_geos)
        for rx in range(ix_max - ix_min + 1):
            for ry in range(iy_max - iy_min + 1):
                rect_geom_geos = self.build_box_2d(
                    minx=size_x * rx,
                    miny=size_y * ry,
                    maxx=size_x * (rx + 1),
                    maxy=size_y * (ry + 1)
                )
                if geos.intersects(rel_geom_geos, rect_geom_geos):
                    key = self.encode_key(
                        ix_min + rx,
                        iy_min + ry,
                        None
                    )
                    data.add(key)

    def build_collision_filter(self, geom: vista.PolyData
                              ) -> vtk.vtkCollisionDetectionFilter:
        alg = vtk.vtkCollisionDetectionFilter()
        alg.SetInputData(0, geom)
        alg.SetTransform(0, vtk.vtkTransform())
        alg.SetBoxTolerance(0.001)
        alg.SetCellTolerance(0.0)
        alg.SetNumberOfCellsPerNode(2)
        alg.SetCollisionMode(1)
        alg.SetGenerateScalars(False)
        return alg

    def build_geom_3d(self, ring: List[List[float]]) -> vista.PolyData:
        if len(ring) > 1 and ring[0] == ring[-1]:
            points = ring[:-1]
        else:
            points = ring
        faces = [len(points)] + list(range(len(points)))
        geom = vista.PolyData(points, faces)
        geom.points_to_double()
        geom.triangulate(inplace=True)
        return geom

    def build_box_3d(self, cx: float, cy: float, cz: float,
                     sx: float, sy: float, sz: float) -> vista.PolyData:
        geom = vista.Cube(
            x_length=sx,
            y_length=sy,
            z_length=sz
        )
        geom.points_to_double()
        geom.translate((cx, cy, cz), inplace=True)
        geom.triangulate(inplace=True)
        return geom

    def build_geom_2d(self, coordinates: List[List[List[float]]],
                      is_line: bool = False) -> geos.Geometry:
        if is_line:
            geom = geos.linestrings(coordinates[0])
        else:
            interiors = [
                geos.linearrings(c)
                for c in coordinates[1:]
            ] or None
            geom = geos.polygons(coordinates[0], holes=interiors)
        return geom

    def build_box_2d(self, minx: float, miny: float,
                     maxx: float, maxy: float) -> geos.Geometry:
        geom = geos.box(minx, miny, maxx, maxy)
        return geom

    def interpolate(self) -> None:
        for data in self._data.values():
            tmp_data = {}
            for key in data:
                ix, iy, iz = self.decode_key(key)
                if iz is None:
                    continue
                tmp_key = (ix, iy)
                tmp_data.setdefault(tmp_key, [float('inf'), float('-inf')])
                tmp_data[tmp_key][0] = min(tmp_data[tmp_key][0], iz)
                tmp_data[tmp_key][1] = max(tmp_data[tmp_key][1], iz)
            for (ix, iy), (iz_min, iz_max) in tmp_data.items():
                for iz in range(iz_min + 1, iz_max):
                    new_key = self.encode_key(ix, iy, iz)
                    data.add(new_key)

    def merge(self) -> None:
        pass

    def load_id_data(self, data: Iterator[Tuple[str, str, Any]],
                     level: int = None, decompose: bool = False) -> None:
        for gml_id, spatial_id, property in data:
            self._update_by_id(gml_id, spatial_id, property, level, decompose)

    def _update_by_id(self, gml_id: str, spatial_id: str, property: Any = None,
                      level: int = None, decompose: bool = False) -> None:
        data = self._data.setdefault(gml_id, set())
        data.add(spatial_id)

    def extract_ids(self, xml: etree.ElementTree) -> None:
        spatial_id_elms = xml.findall(
            '//{*}spatialID'
        )
        for spatial_id_elm in spatial_id_elms:
            level_elm = spatial_id_elm.getparent().find('{*}maxZoomLevel')
            if level_elm is not None:
                level = int(level_elm.text)
                decompose = True
            else:
                level = None
                decompose = False
            spatial_id = spatial_id_elm.text
            feature_elm = spatial_id_elm.getparent().getparent().getparent()
            gml_id = feature_elm.attrib['{http://www.opengis.net/gml}id']
            self._update_by_id(gml_id, spatial_id, level=level, decompose=decompose)

    def extrude(self, min_extrude: float, max_extrude: float) -> None:
        pass


class ZFXYGrid(Grid):

    lv_0_x: float = 2 * math.pi * 6378137.0
    lv_0_y: float = lv_0_x
    lv_0_z: float = 2 ** 25

    crs: int = 3857
    output_crs: int = 6668

    level: int = 20

    def __init__(self, *args, level: int = None, **kwargs):
        super().__init__(*args, level=level, **kwargs)
        if level is not None:
            self.level = level
        self.size_x = self.lv_0_x / 2 ** self.level
        self.size_y = self.lv_0_y / 2 ** self.level
        self.size_z = self.lv_0_z / 2 ** self.level

    def encode_key(self, ix: int, iy: int, iz: int, level: int = None) -> str:
        if level is None:
            level = self.level
        gix, giy, giz = self._get_grid_index(ix, iy, iz=iz, level=level)
        if giz is None:
            return f'{level}/{gix}/{giy}'
        else:
            return f'{level}/{giz}/{gix}/{giy}'

    def encode_key_simple(self, gix: int, giy: int, giz: int = None, level: int = None) -> str:
        if level is None:
            level = self.level
        if giz is None:
            return f'{level}/{gix}/{giy}'
        else:
            return f'{level}/{giz}/{gix}/{giy}'

    def decode_key(self, key: str, full: bool = False) -> str:
        components = [int(s) for s in key.split('/')]
        if len(components) == 4:
            level, giz, gix, giy = components
        elif len(components) == 3:
            level, gix, giy = components
            giz = None
        else:
            raise ValueError(f'Invalid key: {key}')
        ix, iy, iz = self._get_coordinate_index(gix, giy, giz, level)
        if full:
            return (ix, iy, iz, level)
        else:
            return (ix, iy, iz)

    def decode_key_simple(self, key: str, full: bool = False) -> str:
        components = [int(s) for s in key.split('/')]
        if len(components) == 4:
            level, giz, gix, giy = components
        elif len(components) == 3:
            level, gix, giy = components
            giz = None
        else:
            raise ValueError(f'Invalid key: {key}')
        if full:
            return (gix, giy, giz, level)
        else:
            return (gix, giy, giz)

    def _get_grid_index(self, ix: int, iy: int, iz: int = 0, level: int = None) -> Tuple[int, int, int]:
        if level is None:
            level = self.level
        gix = (ix + (1 << max(level - 1, 0))) % (1 << level)
        giy = (1 << max(level - 1, 0)) - iy - 1
        giz = iz
        return gix, giy, giz

    def _get_coordinate_index(self, gix: int, giy: int, giz: int = 0, level: int = None) -> Tuple[int, int, int]:
        if level is None:
            level = self.level
        ix = gix - int(2 ** (level - 1))
        iy = (1 << max(level - 1, 0)) - giy - 1
        iz = giz
        return ix, iy, iz

    def merge(self) -> None:
        for data in self._data.values():
            self._merge_sub(data)

    def _merge_sub(self, data: Set[str]) -> None:
        normal_data = set()
        parent_data = set()
        for key1 in data:
            gix1, giy1, giz1, lv = self.decode_key_simple(key1, full=True)
            if lv == 0:
                continue
            is_3d = giz1 is not None
            if is_3d:
                # parent
                px = gix1 >> 1
                py = giy1 >> 1
                pz = giz1 >> 1
                pkey = self.encode_key_simple(px, py, pz, level=lv-1)
                if pkey in parent_data:
                    continue
                # sibling
                gix2 = gix1 ^ 1
                giy2 = giy1 ^ 1
                giz2 = giz1 ^ 1
                skeys = [
                    self.encode_key_simple(gix1, giy1, giz1, level=lv),
                    self.encode_key_simple(gix1, giy1, giz2, level=lv),
                    self.encode_key_simple(gix1, giy2, giz1, level=lv),
                    self.encode_key_simple(gix1, giy2, giz2, level=lv),
                    self.encode_key_simple(gix2, giy1, giz1, level=lv),
                    self.encode_key_simple(gix2, giy1, giz2, level=lv),
                    self.encode_key_simple(gix2, giy2, giz1, level=lv),
                    self.encode_key_simple(gix2, giy2, giz2, level=lv),
                ]
                if all(skey in data for skey in skeys):
                    parent_data.add(pkey)
                else:
                    normal_data.add(key1)
            else:
                # parent
                px = gix1 >> 1
                py = giy1 >> 1
                pkey = self.encode_key_simple(px, py, level=lv-1)
                if pkey in parent_data:
                    continue
                # sibling
                gix2 = gix1 ^ 1
                giy2 = giy1 ^ 1
                skeys = [
                    self.encode_key_simple(gix1, giy1, level=lv),
                    self.encode_key_simple(gix1, giy2, level=lv),
                    self.encode_key_simple(gix2, giy1, level=lv),
                    self.encode_key_simple(gix2, giy2, level=lv),
                ]
                if all(skey in data for skey in skeys):
                    parent_data.add(pkey)
                else:
                    normal_data.add(key1)
        data.clear()
        if parent_data:
            self._merge_sub(parent_data)
        data.update(parent_data)
        data.update(normal_data)

    def _update_by_id(self, gml_id: str, spatial_id: str, property: Any = None,
                      level: int = None, decompose: bool = False) -> None:
        key = spatial_id
        ix, iy, iz, lv = self.decode_key(key, full=True)
        is_3d = iz is not None
        temp_data = {}
        if not decompose or lv == level:
            temp_data.setdefault(key, set()).add(gml_id)
        elif lv < level:
            # decompose
            temp_list = [(ix, iy, iz, lv)]
            if is_3d:
                for _ in range(level - lv):
                    temp_list = itertools.chain.from_iterable(
                        [
                            (_ix << 1    , _iy << 1    , _iz << 1    , _lv + 1),
                            (_ix << 1    , _iy << 1    , _iz << 1 ^ 1, _lv + 1),
                            (_ix << 1    , _iy << 1 ^ 1, _iz << 1    , _lv + 1),
                            (_ix << 1    , _iy << 1 ^ 1, _iz << 1 ^ 1, _lv + 1),
                            (_ix << 1 ^ 1, _iy << 1    , _iz << 1    , _lv + 1),
                            (_ix << 1 ^ 1, _iy << 1    , _iz << 1 ^ 1, _lv + 1),
                            (_ix << 1 ^ 1, _iy << 1 ^ 1, _iz << 1    , _lv + 1),
                            (_ix << 1 ^ 1, _iy << 1 ^ 1, _iz << 1 ^ 1, _lv + 1),
                        ]
                        for _ix, _iy, _iz, _lv in temp_list
                    )
            else:
                for _ in range(level - lv):
                    temp_list = itertools.chain.from_iterable(
                        [
                            (_ix << 1    , _iy << 1    , _iz    , _lv + 1),
                            (_ix << 1    , _iy << 1 ^ 1, _iz    , _lv + 1),
                            (_ix << 1 ^ 1, _iy << 1    , _iz    , _lv + 1),
                            (_ix << 1 ^ 1, _iy << 1 ^ 1, _iz    , _lv + 1),
                        ]
                        for _ix, _iy, _iz, _lv in temp_list
                    )
            for _ix, _iy, _iz, _lv in temp_list:
                temp_key = self.encode_key(_ix, _iy, _iz, _lv)
                temp_data.setdefault(temp_key, set()).add(gml_id)
        else:
            # compose
            n = lv - level
            temp_key = self.encode_key(
                ix >> n,
                iy >> n,
                iz >> n if is_3d else None,
                level
            )
            temp_data.setdefault(temp_key, set()).add(gml_id)
        data = self._data.setdefault(gml_id, set())
        for sid in temp_data.keys():
            data.add(sid)

    def extrude(self, min_extrude: float = None, max_extrude: float = None) -> None:
        if min_extrude is None or max_extrude is None:
            return
        new_data = {}
        iz_min = math.floor(min_extrude / self.size_z)
        iz_max = math.ceil(max_extrude / self.size_z)
        iz_max_extra = 1 if float(iz_max) == (max_extrude / self.size_z) else 0
        for gml_id, sid_set in self.data.items():
            new_sid_set = new_data.setdefault(gml_id, set())
            for sid in sid_set:
                ix, iy, _iz, level = self.decode_key(sid, full=True)
                if _iz is not None:
                    # 3D
                    new_sid_set.add(sid)
                else:
                    # 2D
                    for iz in range(iz_min, iz_max + iz_max_extra):
                        new_sid = self.encode_key(ix, iy, iz, level)
                        new_sid_set.add(new_sid)
        self._data = new_data
