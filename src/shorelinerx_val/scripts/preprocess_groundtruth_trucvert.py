import os
import numpy as np
import pandas as pd
import verde as vd
from netCDF4 import Dataset
from pathlib import Path
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime, timedelta


def read_dems(filenames, f_grid):

    # read grid
    grid = Dataset(f_grid)
    grid_data = dict([])
    grid_data['lat'] = np.array(grid.variables['latg'][:])
    grid_data['lon'] = np.array(grid.variables['long'][:])
    grid_data['x'] = np.array(grid.variables['xlg'][:])
    grid_data['y'] = np.array(grid.variables['ylg'][:])

    # output variable
    grids = []
    splines = []
    dates = []

    # read the .nc files and store the date and elevation for each file

    for i, f in enumerate(filenames):
        print(f)
        data = Dataset(f)
        date_str = f.name[-13:].split('.nc')[0]
        date = datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=0.5)
        dates.append(date)
        date_str += '12:00'

        # read scatter survey points (epsg 4326)
        lon = data.variables['lon'][:]
        lat = data.variables['lat'][:]
        z = data.variables['z'][:]
        survey_pts = [Point(lon[i], lat[i], z[i]) for i in range(len(lon)) if not np.isnan(z[i])]
        sc_data = {
            'id': np.arange(len(survey_pts)),
            'geometry': survey_pts
        }
        # create gedataframe
        gdf = gpd.GeoDataFrame(sc_data, geometry='geometry', crs="EPSG:4326")
        # change crs of gdf
        gdf = gdf.to_crs(epsg=32630)

        # Fit a spline interpolator to the scattered points
        coordinates = (gdf.geometry.x.to_numpy(), gdf.geometry.y.to_numpy())
        spline = vd.Spline()
        spline.fit(coordinates, gdf.geometry.z.to_numpy())
        splines.append(spline)

        # Build a regular grid over the data's region and predict elevation on it
        region = vd.get_region(coordinates)
        grid = spline.grid(
            spacing=5,  # grid cell size, same units as x/y
            region=region,
            data_names=["elevation"],
        )
        grids.append(grid)

    df_spline_dem = pd.DataFrame({'date': dates, 'spline': splines})
        # 4. Plot
        # fig, ax = plt.subplots(figsize=(8, 5))
        # grid.elevation.plot(ax=ax, cmap="terrain", cbar_kwargs={"label": "elevation (m)"}, vmin=-10, vmax=10)
        # ax.scatter(gdf.geometry.x, gdf.geometry.y, c=gdf.geometry.z, s=10, edgecolor='k', linewidth=0.5,
        #            label="input points", vmin=-10, vmax=10, cmap="terrain")
        # ax.set_aspect("equal")
        # ax.legend()
        # plt.tight_layout()
        # plt.show()

    return df_spline_dem, grids


def seg_to_tr(segments):
    transects = {}
    for i in range(len(segments)):
        transect = segments.iloc[i]
        name = transect['name']
        transects[name] = {}
        (transects[name]['x'], transects[name]['y']), transects[name]['distance'] = vd.profile_coordinates(
            (transect.geometry.xy[0][0], transect.geometry.xy[1][0]),
            (transect.geometry.xy[0][1], transect.geometry.xy[1][1]),
            size=200)
    df_tr = pd.DataFrame.from_dict(transects, orient="index")
    return df_tr


def extract_dems_profiles(df_splines_dem, df_tr):

    bp = {}
    for tr in df_tr.index:
        bp[tr] = []

    for i, dem in df_splines_dem.iterrows():
        for tr in df_tr.index:
            # Query the fitted interpolator directly at profile coordinates
            profile = dem.spline.predict((df_tr.loc[tr]['x'], df_tr.loc[tr]['y']))
            bp[tr].append(profile)

    # save profiles in the dataframe
    df_bp = pd.DataFrame({'date': df_splines_dem['date']})
    for tr in df_tr.index:
        df_bp[tr] = bp[tr]

    return df_bp


def plot_profiles(df_bp, odir):
    for i in range(len(df_bp)):

        plot2d_range_x = [
            np.concatenate(df_tr['x'].values).min(),
            np.concatenate(df_tr['x'].values).max()
        ]
        plot2d_range_y = [
            np.concatenate(df_tr['y'].values).min(),
            np.concatenate(df_tr['y'].values).max()
        ]

        fig, ax = plt.subplots(1, 2, figsize=(22, 6))
        # plot dem
        grids[i].elevation.plot(ax=ax[0], cmap="terrain", cbar_kwargs={"label": "elevation (m)"}, vmin=-10, vmax=10)
        # loop through transects
        for tr in df_tr.index:
            # plot transect
            ax[0].plot(df_tr.loc[tr]['x'], df_tr.loc[tr]['y'], linewidth=1, label=tr)
            # plot beach profile
            ax[1].plot(df_tr.loc[tr]['distance'], df_bp.iloc[i][tr], label=tr)
        ax[1].set_xlabel('cross-shore distance (m)')
        ax[1].set_ylabel('elevation (m)')
        ax[0].legend()
        ax[1].legend()
        ax[0].set_xlim(plot2d_range_x)
        ax[0].set_ylim(plot2d_range_y)
        ax[0].set_aspect("equal")
        fig.suptitle(df_bp.iloc[i]['date'])
        plt.savefig(odir / f'bp_{df_bp.iloc[i]['date'].strftime('%Y%m%d')}.jpg', bbox_inches='tight')
    return



# output file
f_parquet = '/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/beach_profiles_trucvert.parquet'

# output dir
odir = Path('/home/florent/Projects/Shoreliner_CNES/validation/groundtruth')

# input files
filenames = sorted(Path('/home/florent/dev/SDS_Benchmark/datasets/TRUCVERT/raw/').glob('Monitoring*.nc'))
f_grid = Path('/home/florent/dev/SDS_Benchmark/datasets/TRUCVERT/raw/Grids.nc')
f_transects = Path('/home/florent/Projects/Shoreliner_CNES/validation/transects/selection/TRUCVERT_transects.geojson')

# crs
epsg_wl = 32630

# read survey data
df_splines_dem, grids = read_dems(filenames, f_grid)

# read transects
segments = gpd.read_file(f_transects)
segments = segments.to_crs(epsg_wl)

# convert segments to transects
df_tr = seg_to_tr(segments)

# extract beach profiles at transects
df_bp = extract_dems_profiles(df_splines_dem, df_tr)

# plot beach profiles
plot_profiles(df_bp, odir)

# plot
# loop through surveys


# extract survey data along transects




# create a dataframe
# df = pd.DataFrame({'date': time, 'profile_id': profil, 'cross_sh_d':cross_sh_d, 'elevation': elevation})
#
# # save dataframe to parquet
# df.to_parquet(f_parquet)
