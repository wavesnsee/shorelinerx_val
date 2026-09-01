from pathlib import Path
import pandas as pd


def read_bp(f_insitu_bp: Path):
    '''
    read insitu beach profile
    :param f_insitu_bp: geoparquet file of beach profile
    :return: dataframe
    '''

    df = pd.read_parquet(f_insitu_bp)
    df = df[df['elevation'].apply(lambda x: len(x) > 0)].reset_index(drop=True)

    return df