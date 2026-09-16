from pathlib import Path
import pandas as pd
import numpy as np

from shorelinerx_val.core import insitu, sx, stats, plot


def bracket_indices(times: pd.Series, target: pd.Timestamp):
    """
    times: sorted array of datetime64
    target: a single datetime64 value
    Returns (i_before, i_after) such that times[i_before] <= target <= times[i_after]
    """
    idx = np.searchsorted(times, target)

    if idx == 0 or idx == len(times):# target before array start, or target after array end
        return None, None
    else:
        return idx - 1, idx


import pandas as pd
from functools import reduce

import pandas as pd


def sync_t_ls_df_dbw(ls_df_dbw, tol_hours=6, transect_col='transect_id',
                      date_col='datetime_utc', value_col='beach_width_m'):
    '''
    Filter all dataframes in ls_df_dbw to keep only dates that have a
    unique, mutual match (within `tol_hours`) across all dataframes,
    matched separately within each transect_id group. Rows where
    `value_col` is NaN are dropped before matching.

    Each df is assumed to have a `date_col` column (default 'datetime_utc'),
    a `transect_col` column, and a `value_col` column (default 'beach_width_m').
    A match is only valid if timestamps agree within tolerance AND
    transect_id is the same.
    '''
    tol = pd.Timedelta(hours=tol_hours)

    def to_naive_ns(s):
        s = pd.to_datetime(s)
        if getattr(s.dt, 'tz', None) is not None:
            s = s.dt.tz_convert('UTC').dt.tz_localize(None)
        return s.astype('datetime64[ns]')

    def add_sync_date(df):
        '''Return a copy of df with a clean naive-ns '_sync_date' column,
        restricted to rows where value_col is not NaN.'''
        df2 = df[df[value_col].notna()].copy()
        df2['_sync_date'] = to_naive_ns(df2[date_col]).values
        return df2

    def dedup_by_date(df):
        '''Deduplicate on _sync_date (keep first), within a single transect group.'''
        n_dupes = df['_sync_date'].duplicated().sum()
        if n_dupes:
            print(f"Warning: dropping {n_dupes} duplicate-timestamp rows "
                  f"(keeping first) for transect {df[transect_col].iloc[0]!r}")
        df2 = df.drop_duplicates(subset='_sync_date', keep='first')
        return df2.sort_values('_sync_date').reset_index(drop=True)

    def sync_group(dfs_group):
        '''Run the date-matching logic on a list of dfs already restricted
        to a single transect_id.'''
        n = len(dfs_group)
        clean = [dedup_by_date(df) for df in dfs_group]

        ref = pd.DataFrame({'date_0': clean[0]['_sync_date'].values})

        for i in range(1, n):
            di = pd.DataFrame({f'date_{i}': clean[i]['_sync_date'].values})
            merged = pd.merge_asof(
                ref.sort_values('date_0'),
                di.sort_values(f'date_{i}'),
                left_on='date_0',
                right_on=f'date_{i}',
                direction='nearest',
                tolerance=tol,
            )

            merged['_diff'] = (merged['date_0'] - merged[f'date_{i}']).abs()
            is_dup = merged.duplicated(subset=[f'date_{i}'], keep=False) & merged[f'date_{i}'].notna()
            if is_dup.any():
                merged['_rank'] = merged.groupby(f'date_{i}')['_diff'].rank(method='first')
                merged.loc[is_dup & (merged['_rank'] != 1), f'date_{i}'] = pd.NaT
                merged = merged.drop(columns=['_rank'])

            ref = merged.drop(columns=['_diff'])

        ref = ref.dropna().reset_index(drop=True)

        out = []
        for i, df in enumerate(clean):
            matched = ref[f'date_{i}'].values
            filtered = df[df['_sync_date'].isin(matched)].reset_index(drop=True)
            out.append(filtered)

        lengths = [len(d) for d in out]
        assert len(set(lengths)) == 1, f"row counts differ within transect group: {lengths}"

        return out

    n = len(ls_df_dbw)
    if n == 0:
        return ls_df_dbw

    dfs_with_date = [add_sync_date(df) for df in ls_df_dbw]

    # only keep transect_ids present in every dataframe (after the NaN filter)
    common_transects = set(dfs_with_date[0][transect_col].unique())
    for df in dfs_with_date[1:]:
        common_transects &= set(df[transect_col].unique())
    common_transects = sorted(common_transects)

    # accumulate matched rows per dataframe, across all transect groups
    out_per_df = [[] for _ in range(n)]
    for tid in common_transects:
        group = [df[df[transect_col] == tid] for df in dfs_with_date]
        if any(len(g) == 0 for g in group):
            continue
        matched_group = sync_group(group)
        for i, mg in enumerate(matched_group):
            out_per_df[i].append(mg)

    out = []
    for i in range(n):
        if out_per_df[i]:
            combined = pd.concat(out_per_df[i], ignore_index=True).drop(columns='_sync_date')
        else:
            combined = ls_df_dbw[i].iloc[0:0]  # empty, same columns
        out.append(combined)

    lengths = [len(d) for d in out]
    assert len(set(lengths)) == 1, f"row counts still differ: {lengths}"

    return out


def compute_d_bw(ls_df_bw: list[pd.DataFrame], df_bp: pd.DataFrame, table_tr_id: dict):
    '''
    compute difference of waterline position between each satellite derived waterline dataset and insitu
    :return:
    '''

    ls_df_dbw = []

    for df_bw in ls_df_bw:

        # loop through transects
        for tr in list(table_tr_id.values()):

            # filter df_bp and df_bw for given transect
            df_bp_tr = df_bp[(df_bp.profile_id) == tr]
            df_bw_tr = df_bw[(df_bw.transect_id) == tr]

            # initialize d_insitu
            bw_insitu = []
            d_insitu = []
            dt_insitu = []

            # loop through shorelinerx waterlines
            for _, wl in df_bw_tr.iterrows():

                # date difference with insitu beach profiles
                dt = wl['datetime_utc'] - df_bp_tr['datetime_utc']

                # masks 3days, 10days
                mask_3days = dt.abs() < pd.Timedelta(days=3)
                mask_10days = dt.abs() < pd.Timedelta(days=10)

                # continue if no insitu beach profile is within 10 days
                if mask_10days.sum() == 0:
                    bw_insitu.append(None)
                    d_insitu.append(None)
                    dt_insitu.append(None)
                    continue
                else:

                    # waterline tide
                    z = wl['tide_z'] / 100  # conversion cm to m

                    # keep the closest beach profile as it is if there is an situ beach profile within 3 days
                    if mask_3days.sum() > 0:
                        # get unique closest date indice
                        i = np.where(dt.abs() == dt.abs().min())[0]
                        bp = df_bp_tr.iloc[i]
                        csd_from_bp = insitu.cross_shore_at_elevation(bp['cross_sh_d'].squeeze(), bp['elevation'].squeeze(),
                                                                      z)
                        dt_i = np.around((dt.iloc[i] / pd.Timedelta(days=1)).squeeze(), 3)

                    # use the 2 neareast beach profiles to find csd of waterline if there is an situ beach profile between 3 and 10 days
                    else:
                        # get the bp date indices surrounding waterline date
                        i1, i2 = bracket_indices(df_bp_tr['datetime_utc'], wl['datetime_utc'])
                        bp1 = df_bp_tr.iloc[i1]
                        bp2 = df_bp_tr.iloc[i2]
                        csd_from_bp1 = insitu.cross_shore_at_elevation(bp1['cross_sh_d'].squeeze(),
                                                                       bp1['elevation'].squeeze(), z)
                        csd_from_bp2 = insitu.cross_shore_at_elevation(bp2['cross_sh_d'].squeeze(),
                                                                       bp2['elevation'].squeeze(), z)

                        # linear interpolation between csd from bp1 and bp2
                        if (csd_from_bp1 is not None) and (csd_from_bp2 is not None):
                            csd_from_bp = csd_from_bp1 + (csd_from_bp2 - csd_from_bp1) * (- dt.iloc[i1]) / (
                                        dt.iloc[i2] - dt.iloc[i1])
                            dt_i = np.array(
                                [dt.iloc[i1] / np.timedelta64(1, 'D'), dt.iloc[i2] / np.timedelta64(1, 'D')]).round(1)
                        else:
                            csd_from_bp = None

                    # compute beach width difference between shorelinerx and insitu
                    if csd_from_bp is None:
                        bw_insitu.append(None)
                        d_insitu.append(None)
                        dt_insitu.append(None)
                    else:
                        bw_insitu.append(csd_from_bp)
                        d_insitu.append(wl['beach_width_m'] - csd_from_bp)
                        dt_insitu.append(dt_i)

            df_bw.loc[(df_bw.transect_id) == tr, 'bw_insitu_m'] = bw_insitu
            df_bw.loc[(df_bw.transect_id) == tr, 'd_bw_insitu_m'] = d_insitu

            mask = (df_bw.transect_id) == tr
            df_bw.loc[mask, 'dt_insitu_days'] = pd.Series(dt_insitu, index=df_bw_tr.index, dtype=object)

        ls_df_dbw.append(df_bw)

    if len(ls_df_dbw) > 1:
        ls_df_dbw = sync_t_ls_df_dbw(ls_df_dbw)

    # keep only rows where both waterline positions exist (sat and insitu)
    mask_valid = np.ones(len(ls_df_dbw[0])).astype(bool)
    for i, df_dbw in enumerate(ls_df_dbw):
        mask_nonan = df_dbw[['beach_width_m', 'bw_insitu_m']].notna().all(axis=1)
        mask_valid = np.logical_and(mask_valid, mask_nonan)
    ls_df_dbw = [ls_df_dbw[i][mask_valid] for i in range(len(ls_df_dbw))]

    return ls_df_dbw


def run(sdi_path: list[Path], sdi_id: list[str], sdi_color: list[str], f_insitu_bp: Path, f_tr: Path, table_tr_id: dict,
        site: str, odir: Path):
    '''

    :param f_sx_bw: intersections file (geoparquet) from shorelinerx
    :param f_insitu_bp: file (geoparquet) of insitu  beach profile
    :param d_tr: file (geoparquet) of transects, where waterline position has been computed, and groundtruth
    beach profile extracted
    :param table_tr_id: dictionnary of correspondance for transect ids betwen sx and groundtruth
    :param odir: path for output directory
    :return: statistics waterline position at transects (shorelinerx vs groundtruth)
    '''

    # read transects
    df_tr = sx.read_transects(f_tr)

    # read insitu beach profiles
    df_bp = insitu.read_bp(f_insitu_bp)

    # read results of sat derived waterlines' intersections with transects
    ls_df_bw = sx.read_bw(sdi_path, table_tr_id)

    # compute difference of waterline position between sat and insitu
    ls_df_dbw = compute_d_bw(ls_df_bw, df_bp, table_tr_id)

    # compute validation metrics
    ls_df_stats = stats.validation_metrics(ls_df_dbw)

    # plot validation stats
    plot.make(df_tr, table_tr_id, ls_df_dbw, ls_df_stats, site, sdi_id, sdi_color, odir)

    return