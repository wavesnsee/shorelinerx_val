import numpy as np
import pandas as pd


def validation_metrics(df_dbw: pd.DataFrame):
    '''
    computation of validation metrics by transect, and globally
    '''

    transects = np.append(np.unique(df_dbw['transect_id']), 'ALL')

    # initialize stats variables
    min = []
    max = []
    mean = []
    std = []
    mae = []
    rmse = []
    corr = []

    # keep only rows where both beach widhts exist (shorelinerx and insitu)
    mask_valid = df_dbw[['beach_width_m', 'bw_insitu_m']].notna().all(axis=1)
    df_dbw = df_dbw[mask_valid]

    # compute stats by transect, and globally
    for tr in transects:

        # filter beach width difference between shorelinerx and insitu
        if tr != 'ALL':
            d = df_dbw[(df_dbw.transect_id) == tr]['d_bw_insitu_m']
        else:
            d = df_dbw['d_bw_insitu_m']

        # filter respective beach widths
        if tr != 'ALL':
            bw_sx = df_dbw[(df_dbw.transect_id) == tr]['beach_width_m']
            bw_insitu = df_dbw[(df_dbw.transect_id) == tr]['bw_insitu_m']
        else:
            bw_sx = df_dbw['beach_width_m']
            bw_insitu = df_dbw['bw_insitu_m']

        # statistics
        min.append(d.min())
        max.append(d.max())
        mean.append(d.mean())
        std.append(d.std())
        mae.append(d.abs().mean())
        rmse.append(np.sqrt((d ** 2).mean()))
        if len(bw_sx) > 1:
            corr.append(np.corrcoef(bw_sx.to_numpy(dtype=float), bw_insitu.to_numpy(dtype=float))[0, 1])
        else:
            corr.append(np.nan)

    df_stats = pd.DataFrame({
        'transect': transects,
        'min': min,
        'max': max,
        'mean': mean,
        'std': std,
        'mae': mae,
        'rmse': rmse,
        'corr': corr
    })

    return df_stats