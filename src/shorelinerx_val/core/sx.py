import pandas as pd
import geopandas as gpd


def read_transects(f_tr):
    '''
    read transects
    '''

    return gpd.read_parquet(f_tr)


def read_bw(f_sx_bw, table_tr_id: dict):
    '''
    read shorelinerx interctions of waterlines with transects
    :param f_sx_bw: intersections file (geoparquet) from shorelinerx
    :param table_tr_id: dictionnary for correspondance between sx transect ids and groundtruth ones
    :return: dataframe
    '''

    df = pd.read_parquet(f_sx_bw)

    df['transect_id'] = df['transect_id'].astype(object)
    for t_id in table_tr_id.keys():
        df.loc[df['transect_id'] == t_id, 'transect_id'] = table_tr_id[t_id]

    return df