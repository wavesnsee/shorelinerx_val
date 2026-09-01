from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timezone

f_parquet = '/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/beach_profiles_narrabeen.parquet'


# read raw profiles
f_raw = Path('/home/florent/dev/SDS_Benchmark/datasets/NARRABEEN/raw/Narrabeen_Profiles.csv')
df = pd.read_csv(f_raw, usecols=['Profile ID', 'Date', 'Chainage', 'Elevation'])
profile_ids = sorted(set(df['Profile ID']))
date = sorted(set(df['Date']))

# initialize output variables
cross_sh_d_raw = []
elevation_raw = []
date_out = []
profile = []
dico_out = {}

for t in date:
    for p in profile_ids:
        inds = np.where((df['Date'] == t) & (df['Profile ID'] == p))
        cross_sh_d_raw.append(df['Chainage'].iloc[inds].to_numpy())
        elevation_raw.append(df['Elevation'].iloc[inds].to_numpy())
        date_out.append(datetime.strptime(t + ' 12:00', '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc))
        profile.append(p)

dico_out['date'] = date_out
dico_out['profile_id'] = profile
dico_out['cross_sh_d'] = cross_sh_d_raw
dico_out['elevation'] = elevation_raw

df_out = pd.DataFrame.from_dict(dico_out)

# save dataframe to parquet
df_out.to_parquet(f_parquet)


