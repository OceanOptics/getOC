getOC
=====

_Bulk download Ocean Color images._

getOC is a python utility in command line to easily bulk download Ocean Color images from [NASA Ocean Data](https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/) API. Provide a list of positions and dates in a csv file (ex: test.csv), select an instrument (MODIS, VIIRS, OLCI, SeaWiFS), a processing level (L1A, L2, L3BIN, L3SMI), and a product type and getOC will get the images. Usage examples:

    python -m getOC -i <instrument> -l L1A <filename> -u <earthdata-username>
    python -m getOC -i <instrument> -l L2 -p <product> <filename>  -u <earthdata-username>
    python -m getOC -i <instrument> -l L3BIN -s yyyymmdd -e yyyymmdd -b <binning-period> -g <geophysical-parameter>

If you only need to download images in a given time frame without specifying a position, the [File Search](https://oceandata.sci.gsfc.nasa.gov/api/file_search) utility from NASA might be a better tool. The NASA utility also provides a few wget examples on this [Ocean Color Forum Post](https://oceancolor.gsfc.nasa.gov/forum/oceancolor/topic_show.pl?pid=12520).

A strong internet connection is recommended. 

### List of samples
For level 1 and level 2 downloads only (not needed for level 3), a comma separated value (csv) file must be prepared before using getOC. Each line of the csv file must contain the following information (ex: `test.csv`):
    - variable name: sample_id,date&time,latitude,longitude
    - variable type/units: string,yyyy/mm/dd HH:MM:SS (UTC),degN,degE

Images will be downloaded if they are in the same day UTC as the one specified by the date of the point of interest. For times close to the beginning or the end of the day it can be worse adding a line with the previous or following day. getOC is looking for any image in a box of 2º of latitude and 4º of longitude around the point of interest.

### Level 1
For **MODIS-Aqua**:
   
    ./getOC.py -i MODIS-Aqua -l L1A test.csv -u <earthdata-username>
   
Note that GEO file are included in SeaDAS for MODIS-Aqua (no need to download them).
   
For **VIIRS**:

    ./getOC.py -i VIIRS -l L1A test.csv -u <earthdata-username>
    ./getOC.py -i VIIRS -l GEO test.csv -u <earthdata-username>
    
Note that you need to download GEO files to process VIIRS L1A with SeaDAS.
    
For **OLCI**:
    
    ./getOC.py test.csv -i OLCI -l L1 -u <EarthData_username>
    
You need an EarthData account to download OLCI data. No need for GEO files (images are already geo referenced). The password is prompted when the script is done querying. You must log in your browser before starting the script.

SeaWiFS is not supported by getOC at level 1.


### Level 2
Supported for **MODIS-Aqua** and **VIIRS**, usage example:
   
    ./getOC.py -i MODIS-Aqua -l L2 test.csv -u <earthdata-username>
    ./getOC.py -i VIIRS -l L2 test.csv -u <earthdata-username>
    
An optional argument `-p <product>` can be added to specify the product type to download:
  - OC    [default]
  - IOP
  - SST   (only MODIS)
    
OLCI and SeaWiFS are not supported by getOC at level 2.


### Level 3
At level 3 the worlds ocean is downloaded for the range of date specified (getOC does not accept a file with a list of positions at this level). Supported sensors are **SeaWiFS**, **MODIS-Aqua**, and **VIIRS**. Usage:

    python getOC.py -i <instrument> -l <L3BIN|L3SMI> -s yyyymmdd -e yyyymmdd -b <binning-period> -g <geophysical-parameter>

Examples:

    python getOC.py -i SeaWiFS -s 19970101 -e 20101231 -b MO -g GSM_chl_gsm_9km -l L3SMI
    python getOC.py -i MODIS-Aqua -s 20020101 -e 20180423 -b MO -g GSM -l L3BIN
    python getOC.py -i MODIS-Aqua -s 20020101 -e 20180423 -b 8D -g GSM_chl_gsm_9km -l L3SMI
    python getOC.py -i VIIRS -s 20111201 -e 20180423 -b MO -g GSM -l L3BIN

Required arguments:
  - `-s`: start of period to download, formatted as follow `yyyymmdd`
  - `-e`: end of period to download, formatted as follow `yyyymmdd`
  - `-b`: binning period, options are:
    - `DAY`: daily images
    - `8D`: 8 days average
    - `MO`: monthly average
    - `YR`: yearly average
  - `-g`: geophysical parameter to download:
    - supported by `L3BIN`:
        - `CHL`
        - `GSM`
        - `IOP`
        - `KD490`
        - `PAR`
        - `PIC`
        - `POC`
        - `QAA`
        - `RRS`
        - `ZLEE`
        - MODIS only: `SST`, `SST4`, and `NSST`
    - supported by `L3SMI` (non exclusive list):
        - `CHL_chl_ocx_4km`
        - `CHL_chlor_a_4km`
        - `GSM_bbp_443_gsm_9km`
        - `GSM_chl_gsm_9km`
        - `IOP_bb_678_giop_9km`
        - `KD490_Kd_490_9km`


### Other Arguments
**`-w`**
getOC first query Ocean Color servers to get the list of images to download and then download all the images one by one. To save the list of images to download the argument `-w` can be used.

**`-d`**
The server queried for GEO, L1, and L2 data does not like to be queried too fast and will cause the script to crash. By default the delay is set to 1 second which seems to be sufficient. For small datasets, this delay can be reduced to 0 and the script seems to run fine. However, if the script keeps crashing after a few queries you could try again increase the delay in between queries. Argument ignored for level 3 data.

**`-q`**
Quiet please ! getOC does not output any information relative to the download and querying of the points of interest.


