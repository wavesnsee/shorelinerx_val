import pandas as pd
import geopandas as gpd
from pathlib import Path
import numpy as np


def read_transects(f_tr):
    '''
    read transects
    '''

    return gpd.read_parquet(f_tr)


def read_bw(sdi_path: list[Path], table_tr_id: dict):
    '''
    read shorelinerx interctions of waterlines with transects
    :param f_sx_bw: intersections file (geoparquet) from shorelinerx
    :param table_tr_id: dictionnary for correspondance between sx transect ids and groundtruth ones
    :return: dataframe
    '''

    ls_df = []
    for i in range(len(sdi_path)):
        df = pd.read_parquet(sdi_path[i])

        df['transect_id'] = df['transect_id'].astype(object)
        for t_id in table_tr_id.keys():
            df.loc[df['transect_id'] == t_id, 'transect_id'] = table_tr_id[t_id]
        ls_df.append(df)

    return ls_df


def read_mission_name(df: pd.DataFrame):

    mission = np.unique(df['mission'])[0]

    if mission != 'sentinel-2':
        mission = mission.split('-')[0]

    return mission
