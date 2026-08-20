import os
import numpy as np
import pandas as pd
from netCDF4 import Dataset
from pathlib import Path
from datetime import datetime, timedelta


def read_survey_data(filenames):

    # read all files and merge them
    survey_data = dict([])

    # reference time
    ref_t = datetime(1970, 1, 1)

    for f in sorted(filenames):
        data = Dataset(f)
        date_str = f.name[-11:].split('.nc')[0]
        if date_str == '19890523': continue  # skip problematic survey

        # get profile indices corresponding to transects used for validation
        inds_transects = np.isin(data.variables['profileNumber'][:], profiles)

        # read variables of interest
        if np.sum(inds_transects) > 0:
            # time
            t = data.variables['time'][inds_transects]
            t_dtm = ref_t + timedelta(seconds=np.median(t))

            # survey number
            survey_number = np.array(data.variables['surveyNumber'][:])[0]
            # survey data
            survey_data[str(survey_number)] = dict([])
            survey_data[str(survey_number)]['date'] = t_dtm
            survey_data[str(survey_number)]['latitude'] = np.array(data.variables['lat'][:])
            survey_data[str(survey_number)]['longitude'] = np.array(data.variables['lon'][:])
            survey_data[str(survey_number)]['x'] = np.array(data.variables['xFRF'][:])
            survey_data[str(survey_number)]['y'] = np.array(data.variables['yFRF'][:])
            survey_data[str(survey_number)]['elevation'] = np.array(data.variables['elevation'][:])
            survey_data[str(survey_number)]['profile'] = np.array(data.variables['profileNumber'][:])
    return survey_data

# output file
f_parquet = '/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/beach_profiles_duck.parquet'

# input files
filenames = sorted(Path('/home/florent/dev/SDS_Benchmark/datasets/DUCK/raw/').glob('*.nc'))

profiles = [-91, 1, 1006, 1097]
pf_names = [str(_) for _ in profiles]

survey_data = read_survey_data(filenames)

# initialization of output variables
time = []
elevation = []
cross_sh_d = []
profil = []
survey_number = []

# loop through surveys
for n in survey_data.keys():
    survey = survey_data[n]
    for i in range(len(pf_names)):
        idx = np.where(survey['profile'] == profiles[i])[0]
        if len(idx) < 3:
            continue

        # read csd and elevation
        csd = survey['x'][idx]
        el = survey['elevation'][idx]

        # sort by csd
        idx_sorted = np.argsort(csd)
        csd = csd[idx_sorted]
        el = el[idx_sorted]

        # append to output variables
        cross_sh_d.append(csd)
        elevation.append(el)
        profil.append(profiles[i])
        time.append(survey_data[n]['date'])

# create a dataframe
df = pd.DataFrame({'date': time, 'profile_id': profil, 'cross_sh_d':cross_sh_d, 'elevation': elevation})

# save dataframe to parquet
df.to_parquet(f_parquet)
