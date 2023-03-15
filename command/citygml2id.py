import argparse
import logging
import os
import typing

import grids
import inputs
import outputs

Any = typing.Any
Dict = typing.Dict
List = typing.List
Tuple = typing.Tuple
Iterator = typing.Iterator

logger = logging.getLogger(__name__)


def main(input_file_or_dir: str, output_file_or_dir: str, lod: int,
         grid_type: str, grid_level: int, grid_size: List[float], grid_crs: int,
         ids: Tuple[str], extract: bool = False, extrude: List[float] = [],
         interpolate: bool = False, merge: bool = False, debug: bool = False
         ) -> None:
    """CityGML 2 ID pair list

    Args:
        input_file_or_dir (str): path to the CityGML file (*.gml) or directory
        output_file_or_dir (str): path to the ID pair list file (*.csv) or directory
        lod (int): maximum LOD of target geometries
        grid_type (str): type of the output voxel grid
        grid_level (int): zoom level of the output voxel grid
        grid_size (List[float]): size of the output voxel grid
        grid_crs (int): coordinate reference system of the output voxel grid
        ids (Tuple[str]): gml:ids which will be filtered
        extract (bool, optional): whether extract spatial ids from CityGML or not. Defaults to False.
        extrude (List[float], optional): min extrude and max extrude (unit: m). Defaults to [].
        interpolate (bool, optional): whether interpolate inner voxels of solids or not. Defaults to False.
        merge (bool, optional): whether merge 8 adjacent voxels into 1 large voxel or not. Defaults to False.
        debug (bool, optional): whether output debug messages and retain temporary files or not. Defaults to False.

    Raises:
        ValueError: Invalid parameters
    """
    extrude = extrude or []
    if extrude and len(extrude) != 2:
        raise ValueError(f'Invalid extrude: {extrude}')

    # grid
    grid = grids.get(
        grid_type,
        level=grid_level,
        size=grid_size,
        crs=grid_crs
    )

    # batch
    output_ext = os.path.splitext(output_file_or_dir)[-1]
    if os.path.isdir(input_file_or_dir) and output_ext == '':
        input_files = inputs.get_target_gml_files(input_file_or_dir)
        output_files = outputs.build_output_paths(
            grid,
            input_file_or_dir,
            input_files,
            output_file_or_dir,
            merge=merge
        )
    elif os.path.isfile(input_file_or_dir) and output_ext == '.csv':
        input_files = [input_file_or_dir]
        output_files = [output_file_or_dir]
    else:
        raise ValueError(f'Invalid path: {input_file_or_dir} {output_file_or_dir}')

    # main
    for input_file, output_file in zip(input_files, output_files):
        grid.clear()
        if extract:
            xml2id(
                input_file,
                output_file,
                lod,
                grid,
                ids,
                extrude=extrude,
                interpolate=interpolate,
                merge=merge,
                debug=debug
            )
        else:
            geom2id(
                input_file,
                output_file,
                lod,
                grid,
                ids,
                interpolate=interpolate,
                merge=merge,
                debug=debug
            )


def xml2id(input_file: str, output_file: str, lod: int, grid: grids.Grid,
           ids: Tuple[str], extrude: List[float] = [], interpolate: bool = False,
           merge: bool = False, debug: bool = False) -> None:
    """CityGML with spatial IDs 2 ID pair list

    Args:
        input_file (str): path to the CityGML file (*.gml)
        output_file (str): path to the ID pair list file (*.csv)
        lod (int): maximum LOD of target geometries
        grid (grids.Grid): voxel grid instance
        ids (Tuple[str]): gml:ids which will be filtered
        extrude (List[float], optional): min extrude and max extrude (unit: m). Defaults to [].
        interpolate (bool, optional): whether interpolate inner voxels of solids or not. Defaults to False.
        merge (bool, optional): whether merge 8 adjacent voxels into 1 large voxel or not. Defaults to False.
        debug (bool, optional): whether output debug messages and retain temporary files or not. Defaults to False.
    """
    xml = inputs.load_xml(
        input_file
    )

    # extract ids
    grid.extract_ids(
        xml
    )

    # extrude
    grid.extrude(*extrude[:2])

    # merge
    if merge:
        grid.merge()

    # output
    outputs.export_csv(
        grid,
        output_file,
        merge=merge
    )


def geom2id(input_file: str, output_file: str, lod: int, grid: grids.Grid,
            ids: Tuple[str], interpolate: bool = False, merge: bool = False,
            debug: bool = False) -> None:
    """CityGML without spatial IDs 2 ID pair list

    Args:
        input_file (str): path to the CityGML file (*.gml)
        output_file (str): path to the ID pair list file (*.csv)
        lod (int): maximum LOD of target geometries
        grid (grids.Grid): voxel grid instance
        ids (Tuple[str]): gml:ids which will be filtered
        interpolate (bool, optional): whether interpolate inner voxels of solids or not. Defaults to False.
        merge (bool, optional): whether merge 8 adjacent voxels into 1 large voxel or not. Defaults to False.
        debug (bool, optional): whether output debug messages and retain temporary files or not. Defaults to False.
    """
    # input
    data = inputs.load_features(
        input_file,
        ids,
        lod,
        grid.crs,
        debug=debug
    )

    # build voxel grid
    grid.load_geom_data(
        data,
        interpolate=interpolate,
        merge=merge
    )

    # output
    outputs.export_csv(
        grid,
        output_file,
        merge=merge
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file_or_dir', help='path to the CityGML file (*.gml) or directory')
    parser.add_argument('output_file_or_dir', help='path to the ID pair list file (*.csv) or directory')
    parser.add_argument('--lod', type=int, choices=(1, 2, 3), default=3, help='maximum LOD of target geometries')
    parser.add_argument('--grid-type', choices=('zfxy',), default='zfxy', help='type of the output voxel grid')
    parser.add_argument('--grid-level', type=int, help='zoom level of the output voxel grid')
    parser.add_argument('--grid-size', type=float, nargs='*', help='size of the output voxel grid')
    parser.add_argument('--grid-crs', type=int, help='coordinate reference system of the output voxel grid')
    parser.add_argument('--id', nargs='*', help='gml:ids which will be filtered')
    parser.add_argument('--extract', action='store_true', help='whether extract spatial ids from CityGML or not')
    parser.add_argument('--extrude', type=float, nargs='*', help='min extrude and max extrude (unit: m)')
    parser.add_argument('--interpolate', action='store_true', help='whether interpolate inner voxels of solids or not')
    parser.add_argument('--merge', action='store_true', help='whether merge 8 adjacent voxels into 1 large voxel or not')
    parser.add_argument('--debug', action='store_true', help='whether output debug messages and retain temporary files or not')
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    main(
        input_file_or_dir=args.input_file_or_dir,
        output_file_or_dir=args.output_file_or_dir,
        lod=args.lod,
        grid_type=args.grid_type,
        grid_level=args.grid_level,
        grid_size=args.grid_size,
        grid_crs=args.grid_crs,
        ids=args.id,
        extract=args.extract,
        extrude=args.extrude,
        interpolate=args.interpolate,
        merge=args.merge,
        debug=args.debug
    )
