import pdb
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
    for tr in list(table_tr_id.values()):

        # filter df_bp and df_bw for given transect
        df_bp_tr = df_bp[(df_bp.profile_id) == tr]
        df_bw_tr = df_bw[(df_bw.transect_id) == tr]

        # loop through insitu beach profiles
        for _, bp in df_bp_tr.iterrows():

            # date difference with shorelinerx waterlines
            dt = bp['date'] - df_bw_tr['datetime_utc']
            mask_3days = dt.abs() < pd.Timedelta(days=3)
            mask_10days = dt.abs() < pd.Timedelta(days=3)

            if mask_3days.sum() == 0:
                continue
            else:
                print(bp['date'])
                print(df_bw_tr['datetime_utc'][mask_3days])
                print(df_bw_tr['tide_z'][mask_3days])
                # csd_from_bp = np.interp(df_bw_tr['tide_z'][mask_3days], y, x)
                csd_from_bp = insitu.cross_shore_at_elevation(bp['cross_sh_d'], bp['elevation'], df_bw_tr['tide_z'][mask_3days])

                # get insitu cross-shore distance corresponding to waterline tide
                plt.plot(bp['cross_sh_d'], bp['elevation'], '+-')
                plt.scatter(csd_from_bp, df_bw_tr['tide_z'][mask_3days], c='r')
                plt.show()

                pdb.set_trace()



        # keep beach profile, interpolate beach profile, or reject


    return