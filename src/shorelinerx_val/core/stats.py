import numpy as np
import pandas as pd


def validation_metrics(ls_df_dbw: list[pd.DataFrame]):
    '''
    computation of validation metrics by transect, and globally, for each satellited derived intersections dataset
    '''

    ls_df_stats = []

    for df_dbw in ls_df_dbw:

        transects = np.append(np.unique(df_dbw['transect_id']), 'ALL')

        # initialize stats variables
        min = []
        max = []
        mean = []
        std = []
        mae = []
        rmse = []
        corr = []
        n_samples = []

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
            n_samples.append(len(d))

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
            'corr': corr,
            'n_samples': n_samples
        })

        ls_df_stats.append(df_stats)

    return ls_df_stats


def box_stats(arr, label):
    q1, median, q3 = np.percentile(arr, [25, 50, 75])
    iqr = q3 - q1
    # upper = min(arr.max(), q3 + 1.5 * iqr)
    # lower = max(arr.min(), q1 - 1.5 * iqr)
    lower, upper = np.percentile(arr, [10, 90])
    lower = max(arr.min(), q1 - 1.5 * iqr)
    return dict(label=label, q1=q1, q2=median, q3=q3,
                upper=upper, lower=lower)