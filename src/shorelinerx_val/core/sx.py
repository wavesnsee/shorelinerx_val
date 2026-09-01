import pandas as pd

def read_bw(f_sx_bw):
    '''
    read shorelinerx interctions of waterlines with transects
    :param f_sx_bw: intersections file (geoparquet) from shorelinerx
    :return: dataframe
    '''

    df = pd.read_parquet(f_sx_bw)
    return df