# shorelinerx_val


## Preprocessing
A preprocessing cis done to exxstract beach profiles along given transects for the differents sites.

All elevations in the extracted profiles are relative to MSL (Mean Sea Level).

Survey datum for the input data are:

|Site|Survey datum|
|--|--|
|NARRABEEN|   MSL|
|DUCK| NAVD88|
|TORREYPINES| NAVD88|
|TRUCVERT|    MSL|

At Duck and Torreypines; Here is the relative position of MSL relatively to NAVD88 :

|Site| MSL (m) (ref NAVD88) |
|--|----------------------|
|DUCK| -0.128               |
|TORREYPINES| 0.774                |


## Installation
Install as a uv tool:

`uv tool install "shorelinerx_val @ git+ssh://git@github.com/wavesnsee/shorelinerx_val.git@main"`


## Usage
`shorelinerx_val myfile.yaml`

## yaml
To see an example of yaml parameters' file, see file: 

**src/shorelinerx_val/cli/yaml/val_s2_duck.yaml**


