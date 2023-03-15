import os
import typing

import constants
import grids

List = typing.List


def export_csv(grid: grids.Grid, output_file: str, merge: bool = False) -> None:
    """export voxel grid to ID pair list file

    Args:
        grid (grids.Grid): voxel grid instance
        output_file (str): path to the ID pair list file (*.csv)
        merge (bool, optional): whether merge 8 adjacent voxels into 1 large voxel or not. Defaults to False.
    """
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        max_zoom_level = getattr(grid, 'level', -1)
        merge_flag = 1 if merge else 0
        f.write(f'{constants.CSV_CODE},{constants.CSV_VERSION},{max_zoom_level},{merge_flag}')
        f.write('\n')
        f.write('gml_id,spatial_id')
        f.write('\n')
        for gml_id, data in grid.data.items():
            for spatial_id in data:
                f.write(f'{gml_id},{spatial_id}')
                f.write('\n')


def build_output_paths(grid: grids.Grid, input_dir: str, input_files: str,
                       output_dir: str, output_ext: str = '.csv',
                       merge: bool = False) -> List[str]:
    """build batch output file paths

    Args:
        grid (grids.Grid): voxel grid instance
        input_dir (str): input directory path
        input_files (str): input file paths
        output_dir (str): output directory path
        output_ext (str, optional): output files' extension. Defaults to '.csv'.
        merge (bool, optional): whether merge 8 adjacent voxels into 1 large voxel or not. Defaults to False.

    Returns:
        List[str]: output file paths
    """
    input_dir = os.path.normpath(os.path.abspath(input_dir))
    output_files = []
    for input_file in input_files:
        input_file_rel = os.path.normpath(os.path.abspath(input_file))[len(input_dir)+1:]
        input_dir_rel, input_name = os.path.split(input_file_rel)
        input_stem, input_ext = os.path.splitext(input_name)
        if hasattr(grid, 'level'):
            output_suffix = f'_zl{grid.level}'
        else:
            output_suffix = ''
        if merge:
            output_suffix = f'{output_suffix}_merged'
        output_stem = f'{input_stem}{output_suffix}'
        if output_ext == '.csv':
            output_sub_dir = constants.CSV_DIRECTORY
        else:
            output_sub_dir = ''
        output_dir_rel = os.path.join(input_dir_rel, output_sub_dir)
        output_file_rel = os.path.join(output_dir_rel, f'{output_stem}{output_ext}')
        output_file = os.path.join(output_dir, output_file_rel)
        output_files.append(output_file)
    return output_files
