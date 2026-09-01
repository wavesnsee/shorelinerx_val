from pathlib import Path
import pandas as pd


def read_bp(f_insitu_bp: Path):
    '''
    read insitu beach profile
    :param f_insitu_bp: geoparquet file of beach profile
    :return: dataframe
    '''
    df = pd.read_parquet(f_insitu_bp)

    return df