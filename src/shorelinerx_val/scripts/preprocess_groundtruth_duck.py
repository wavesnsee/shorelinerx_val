from pathlib import Path
import numpy as np
import pandas as pd
from netCDF4 import Dataset
from scipy.interpolate import UnivariateSpline
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random


def generate_random_colors(n):
    return [(random.random(), random.random(), random.random()) for _ in range(n)]


# execution options
save_to_parquet = True
plot_profils = False
f_parquet = '/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/beach_profiles_duck.parquet'

# selection of transects used for validation
transects = [-91, 1, 1006, 1097]

if save_to_parquet:

    # read raw profiles
    dir_raw = Path('/home/florent/dev/SDS_Benchmark/datasets/DUCK/raw/')
    ls_raw = sorted(dir_raw.glob('*.nc'))

    # reference time
    ref_t = datetime(1970, 1, 1)

    time = []
    elevation = []
    cross_sh_d = []
    profil = []
    survey_number = []

    # read all nc files
    for i, f in enumerate(ls_raw):
        print(f)
        data = Dataset(f)

        # get profile indices corresponding to transects used for validation
        profil_tmp = data.variables['profileNumber'][:]
        inds_transects = np.isin(profil_tmp, transects)

        if np.sum(inds_transects) > 0:

            # list transects that have data for the considered date
            profil_tmp = data.variables['profileNumber'][inds_transects]
            transects_tmp = sorted(set(profil_tmp))

            # select data at transects
            t = data.variables['time'][inds_transects]
            t_dtm = ref_t + timedelta(seconds=np.median(t))
            for transect in transects_tmp:
                i_tr = np.where(profil_tmp == transect)[0]
                time.append(t_dtm)
                profil.append(transect)
                csd = data.variables['xFRF'][i_tr]
                el = data.variables['elevation'][i_tr]
                isort_csd = np.argsort(csd)
                cross_sh_d.append(csd[isort_csd])
                elevation.append(el[isort_csd])

    # create a dataframe
    df = pd.DataFrame({'date': time, 'profile_id': profil, 'cross_sh_d':cross_sh_d, 'elevation': elevation})