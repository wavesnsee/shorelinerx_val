from pathlib import Path
import pandas as pd
import numpy as np


def read_bp(f_insitu_bp: Path):
    '''
    read insitu beach profile
    :param f_insitu_bp: geoparquet file of beach profile
    :return: dataframe
    '''

    df = pd.read_parquet(f_insitu_bp)
    df = df[df['elevation'].apply(lambda x: len(x) > 0)].reset_index(drop=True)

    return df


def cross_shore_at_elevation(x, y, target_elev):
    '''
    assess from beach profile the cross shore distance corresponding to a given height
    '''
    d = y - target_elev
    sign_change = np.where(np.diff(np.sign(d)) != 0)[0]

    crossings = []
    for i in sign_change:
        # linear interpolation between point i and i+1
        x_cross = x[i] + (x[i + 1] - x[i]) * (0 - d[i]) / (d[i + 1] - d[i])
        crossings.append(x_cross)
    # keep most seaward crossing
    if len(crossings) > 0:
        csd = crossings[-1]
    else:
        csd = None
    return csd