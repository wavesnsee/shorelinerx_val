from pathlib import Path
from shorelinerx_val.core import insitu, sx


def run(f_sx_bw: Path, f_insitu_bp: Path, table_tr_id: dict, odir: Path):
    '''

    :param f_sx_bw: intersections file (geoparquet) from shorelinerx
    :param f_insitu_bp: file (geoparquet) of insitu  beach profile
    :param table_tr_id: dictionnary of correspondance for transect ids betwen sx and groundtruth
    :param odir: path for output directory
    :return: statistics waterline position at transects (shorelinerx vs groundtruth)
    '''

    # read insitu beach profiles
    df_bp = insitu.read_bp(f_insitu_bp)

    # read results of shorelinerx intersections with transects
    df_bw = sx.read_bw(f_sx_bw, table_tr_id)

    # loop through transects

    # loop through insitu beach profiles

    # keep beach profile or interpolate beach profile


    return