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