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
    x = np.asarray(x)
    y = np.asarray(y)
    if y[0] > y[-1]:
        x, y = x[::-1], y[::-1]
    return np.interp(target_elev, y, x)