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


def read_dems(filenames, transects):

    # output variables
    dates = []
    elevation = []
    profile_id = []
    csd = []
    masks = []
    easting = []
    northing = []

    # loop through the .nc files
    for i, f in enumerate(filenames):
        print(f)
        data = Dataset(f)
        date_str = f.name.split('_')[0].split('map')[1]
        date = datetime.strptime(date_str, '%Y%m%d') + timedelta(days=0.5)
        date_str += '12:00'

        # read grid of profile names alongshore
        alg = np.array(data.variables['alg'][:])

        # get grid indices of validation profiles
        i_transects = [np.where(alg[0, :] == transects[i])[0][0] for i in range(len(transects))]

        # read grid
        xg = np.array(data.variables['xc'][:])
        yg = np.array(data.variables['yc'][:])


        for j in range(len(transects)):

            # append date
            dates.append(date)

            # append profile id
            profile_id.append(transects[j])

            # read ncdf
            zg = data.variables['mapz'][:]
            x = xg[:, i_transects[j]]
            y = yg[:, i_transects[j]]
            z = zg[:, i_transects[j]]

            # distance cross-shore
            # transects are defined from sea to laand. So to get the cross-shore distance of every grid point at a given
            # alongshore distance, we have to compute the distance from the last transect's point
            transect_extremity = Point(x[-1], y[-1])
            d = np.array([Point(x[i], y[i]).distance(transect_extremity) for i in range(len(x))])

            # mask
            mask = ~ z.mask
            el = z[mask]
            d = d[mask]
            e = x[mask]
            n = y[mask]

            # reverse order of csd and elevation, so as to use a transect from land to shore
            d = np.flip(d)
            el = np.flip(el)
            mask = np.flip(mask)
            n = np.flip(n)
            e = np.flip(e)

            # append elevation, csd, masks, easting, northing
            elevation.append(el)
            csd.append(d)
            masks.append(mask)
            easting.append(e)
            northing.append(n)


    # create a dataframe
    df = pd.DataFrame({'date': dates, 'profile_id': profile_id, 'cross_sh_d': csd, 'elevation': elevation,
                       'mask': masks, 'northing': northing, 'easting': easting})

    return df


def plot_profiles(df_profiles, transects, odir):

    dates = np.unique(df_profiles['date'])

    for date in dates:

        # create fig, ax
        fig, ax = plt.subplots(1, 2, figsize=(22, 6))
        fig.suptitle(date)

        # plot transects
        # ax[0].set_title('raw survey')
        # for i_t, tr in enumerate(transects):
        #     tr_coords = np.array(gdf_transects.iloc[i_t].geometry.xy)
        #     ax[0].plot(tr_coords[0], tr_coords[1], label=tr, zorder=1, linewidth=1)

        # to check that transects in the benchmark are well the same than the ones from the survey grid
        f_transects = Path(
            '/home/florent/Projects/Shoreliner_CNES/validation/transects/selection/TORREYPINES_transects.geojson')
        segments = gpd.read_file(f_transects)
        segments = segments.to_crs(32611)
        for i_s, segment in segments.iterrows():
            ax[0].plot(segment.geometry.xy[0], segment.geometry.xy[1], label=segment['name'], linewidth=1)

        i_dates = np.where(df_profiles['date'] == date)[0]
        for i in i_dates:

            # plot survey data points
            ax[0].set_title('gridded survey data points')
            x = df_profiles.iloc[i]['easting']
            y = df_profiles.iloc[i]['northing']
            z = df_profiles.iloc[i]['elevation']
            ax[0].scatter(x, y, c=z,
                          s=25, vmin=-10, vmax=5, cmap="terrain"
                          )
            ax[0].legend(loc='center right')
            ax[0].set_aspect("equal")
            ax[0].set_xlabel('Easting (m)')
            ax[0].set_ylabel('Northing (m)')
            # ax[0].set_xlim([])

            # plot beach profile
            ax[1].plot(df_profiles.iloc[i]['cross_sh_d'], df_profiles.iloc[i]['elevation'], label=df_profiles.iloc[i]['profile_id'])
            ax[1].set_title('beach profiles')
            ax[1].set_xlabel('cross-shore distance (m)')
            ax[1].set_ylabel('elevation (m)')
            ax[1].set_xlim([50, 500])
            ax[1].set_ylim([-10, 5])
            ax[1].legend(loc='upper right')
            ax[1].grid(True)
        # plt.show()
        f_jpg = odir / f'bp_torrey/bp_{pd.Timestamp(date).strftime('%Y-%m-%d')}.jpg'

        plt.savefig(f_jpg, bbox_inches='tight')

    return



# output file
f_parquet = '/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/beach_profiles_torreypines.parquet'

# output dir for plots
odir = Path('/home/florent/Projects/Shoreliner_CNES/validation/groundtruth')

# input files
filenames = sorted(Path('/home/florent/dev/SDS_Benchmark/datasets/TORREYPINES/raw/torrey_mapped_sand_elevations/').glob('map*.nc'))
# f_transects = Path('/home/florent/Projects/Shoreliner_CNES/validation/transects/selection/TORREYPINES_transects.geojson')

# crs
epsg_wl = 32611

#
# transects = ['PF525', 'PF535', 'PF585', 'PF595']
transects = [525, 535, 585, 595]

# cross_shore distance of every transect from grid
# gdf_transects, i_transects = get_csd(long_raw, latg_raw, longshore, transects)

# read survey data
df_profiles = read_dems(filenames, transects)

# plot beach profiles
plot_profiles(df_profiles, transects, odir)

# save dataframe to parquet
df_profiles.to_parquet(f_parquet)

