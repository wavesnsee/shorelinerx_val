import os
import numpy as np
import pandas as pd
from datetime import datetime
import verde as vd
from netCDF4 import Dataset
from pathlib import Path
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point, LineString
from datetime import datetime, timedelta


def read_grid(f_grid):

    # read grid of alongshore coordinates
    grid = Dataset(f_grid)
    longshore = np.array(grid.variables['ylg'][:])

    # # get indices alongshore corresponding to validation transects
    # i_transects = [np.where(longshore[0, :] == transects[i])[0][0] for i in range(len(transects))]

    # read grid lat, lon
    latg_raw = np.array(grid.variables['latg'][:])
    long_raw = np.array(grid.variables['long'][:])

    return long_raw, latg_raw, longshore


def get_csd(long_raw, latg_raw, longshore, transects):

    # get indices alongshore corresponding to validation transects
    i_transects = [np.where(longshore[0, :] == transects[i])[0][0] for i in range(len(transects))]

    # get transects' points from grid
    transect_pts = [LineString(np.column_stack((long_raw[:, i], latg_raw[:, i]))) for i in i_transects]

    sc_data = {
        'id': np.array(transects),
        'geometry': transect_pts
    }

    # create gedataframe
    gdf = gpd.GeoDataFrame(sc_data, geometry='geometry', crs="EPSG:4326")
    # change crs of gdf to convert to projected utm coordinates
    gdf = gdf.to_crs(epsg=32630)

    # get cross-shore distance along every transect
    csd = []
    for i in range(len(gdf)):
        first_point = Point(gdf.iloc[i].geometry.coords[0])
        csd.append([Point(coord).distance(first_point) for coord in gdf.iloc[i].geometry.coords])

    gdf['csd'] = csd

    return gdf, i_transects


def read_dems(filenames, transects, i_transects, gdf):

    # output variables
    dates = []
    elevation = []
    profile_id = []
    csd = []
    masks = []

    # loop through the .nc files
    for i, f in enumerate(filenames):
        print(f)
        data = Dataset(f)
        date_str = f.name[-13:].split('.nc')[0]
        date = datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=0.5)
        date_str += '12:00'

        for j in range(len(transects)):
            dates.append(date)
            profile_id.append(transects[j])
            zg = data.variables['zg'][:, i_transects[j]]
            mask = ~ zg.mask
            d = np.array(gdf.iloc[j]['csd'])
            if date == datetime(2004, 5, 18, 12):
                mask = np.logical_and(mask, (d > 55))
            elevation.append(zg[mask])
            csd.append(d[mask])
            masks.append(mask)


    # create a dataframe
    df = pd.DataFrame({'date': dates, 'profile_id': profile_id, 'cross_sh_d': csd, 'elevation': elevation, 'mask': masks})

    return df


def plot_profiles(gdf_transects, df_profiles, transects, odir):

    dates = np.unique(df_profiles['date'])
    gdf_transects = gdf_transects.set_index('id')

    for date in dates:

        # create fig, ax
        fig, ax = plt.subplots(1, 2, figsize=(22, 6))
        fig.suptitle(date)

        # plot transects
        ax[0].set_title('raw survey')
        for i_t, tr in enumerate(transects):
            tr_coords = np.array(gdf_transects.iloc[i_t].geometry.xy)
            ax[0].plot(tr_coords[0], tr_coords[1], label=tr, zorder=1, linewidth=1)

        # to check that transects in the benchmark are well the same than the ones from the survey grid
        # f_transects = Path(
        #     '/home/florent/Projects/Shoreliner_CNES/validation/transects/selection/TRUCVERT_transects.geojson')
        # segments = gpd.read_file(f_transects)
        # segments = segments.to_crs(32630)
        # for i_s, segment in segments.iterrows():
        #     ax[0].plot(segment.geometry.xy[0], segment.geometry.xy[1], label=segment['name'], linewidth=2)

        i_dates = np.where(df_profiles['date'] == date)[0]
        for i in i_dates:

            # plot survey data points
            ax[0].set_title('gridded survey data points')
            geom = gdf_transects.loc[gdf_transects.index == df_profiles.iloc[i]['profile_id'], 'geometry'].values[0]
            x = geom.xy[0]
            y = geom.xy[1]
            mask = df_profiles.iloc[i]['mask']
            z = df_profiles.iloc[i]['elevation']
            ax[0].scatter(np.array(x)[mask], np.array(y)[mask], c=z,
                          s=15, vmin=-10, vmax=10, cmap="terrain"
                          )
            ax[0].legend(loc='lower right')
            ax[0].set_aspect("equal")
            ax[0].set_xlabel('Esating (m)')
            ax[0].set_ylabel('Northing (m)')

            # plot beach profile
            ax[1].plot(df_profiles.iloc[i]['cross_sh_d'], df_profiles.iloc[i]['elevation'], label=df_profiles.iloc[i]['profile_id'])
            ax[1].set_title('beach profiles')
            ax[1].set_xlabel('cross-shore distance (m)')
            ax[1].set_ylabel('elevation (m)')
            ax[1].set_xlim([25, 300])
            ax[1].set_ylim([-2, 12])
            ax[1].legend(loc='upper right')
            ax[1].grid(True)
        plt.show()
        f_jpg = odir / f'bp_trucvert/bp_{pd.Timestamp(date).strftime('%Y-%m-%d')}.jpg'

        plt.savefig(f_jpg, bbox_inches='tight')

    return



# output file
f_parquet = '/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/beach_profiles_trucvert.parquet'

# output dir for plots
odir = Path('/home/florent/Projects/Shoreliner_CNES/validation/groundtruth')

# input files
filenames = sorted(Path('/home/florent/dev/SDS_Benchmark/datasets/TRUCVERT/raw/').glob('Monitoring*.nc'))
f_grid = Path('/home/florent/dev/SDS_Benchmark/datasets/TRUCVERT/raw/Grids.nc')

# crs
epsg_wl = 32630

#
transects = [-400, -300, -200, -100]

# read grid
long_raw, latg_raw, longshore = read_grid(f_grid)

# cross_shore distance of every transect from grid
gdf_transects, i_transects = get_csd(long_raw, latg_raw, longshore, transects)

# read survey data
df_profiles = read_dems(filenames, transects, i_transects, gdf_transects)

# plot beach profiles
plot_profiles(gdf_transects, df_profiles, transects, odir)

# save dataframe to parquet
df_profiles.to_parquet(f_parquet)

