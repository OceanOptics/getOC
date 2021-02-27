getOC
=====

_Bulk download Ocean Color images (ESA and NASA platforms)._

getOC is a python utility in command line to easily bulk download Ocean Color images from [NASA Ocean Data](https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/) and [ESA CREODIAS](https://finder.creodias.eu/resto/api2/collections/Sentinel2/search.json?) APIs. Provide a list of positions and dates in a csv file (ex: test.csv), select an instrument, a processing level, and a product type and getOC will get the images.

[EARTHDATA account required to download NASA satellites data](https://urs.earthdata.nasa.gov/users/new)
[CREODIAS account required to download ESA satellites data](https://auth.creodias.eu/auth/realms/dias/protocol/openid-connect/auth?scope=openid+profile+email&response_type=code&redirect_uri=https%3A%2F%2Fcreodias.eu%2Fc%2Fportal%2Flogin&state=9ff87a6f1cefa7fa0e8ec5b49bf9bc33&client_id=CLOUDFERRO_PARTNERS&response_mode=query)

Level 3 download is DEPRECATED

### Argument description:
**`-i`** **instrument**  
    - **`SeaWiFS`**  
    - **`MODIS-Aqua`**  
    - **`MODIS-Terra`**  
    - **`OCTS`**  
    - **`CZCS`**  
    - **`MERIS`**  
    - **`VIIRSN`**  
    - **`VIIRSJ1`**  
    - **`HICO`**  
    - **`OLCI`**  
    - **`SLSTR`**  
    - **`MSI`**  

**`-l`** **level**  
#####- **`MSI`**:  
- **`L1C`**  
- **`L2A`**  
#####- **`MODIS-Aqua`** **`MODIS-Terra`** **`VIIRSN`** **`VIIRSJ1`**:  
- **`L1A`**  
- **`L2`**  
#####- **`OCLI`** full resolution [default]:  
- **`L1`** or **`L1_EFR`**  
- **`L2`** or **`L2_WFR`**  
#####- **`OCLI`** low resolution:  
- **`L1_ERR`**  
- **`L2_WRR`**  
#####- **`SLSTR`** low resolution:  
- **`L1`** or **`L1_RBT`**  
- **`L2`** or **`L2_WST`** [default; GHRSST recommendations]  
- **`L2_WCT`** [weighted combinations of brightness temperatures]  

**`-u`** **username**  
    - Earthdata login for NASA satellites  
    - Creodias login for ESA satellites)

**`-w`** **write**  
    Prints the image list on a copy of the csv file after the query is completed.

**`-r`** **read**  
    getOC loads the list previously queried and printed, to avoid querying twice the same list

**`-p`** **product**  
    Specify the product type to download:  
    - **`OC`**    [default]  
    - **`IOP`**    [Deprecated]  
    - **`SST`**  

**`--box`** **bounding box**  
    Define the size of the bounding box around the point of interest in nautical miles. Downloads all images that intersect with this box.

**`-q`** **quiet**  
    Quiet please ! getOC does not output any information relative to the download and querying of the points of interest.

### Usage examples:
    python -m getOC -i MODIS-Aqua -l L2 <filename> -u <earthdata-username> -w -p OC --box 60
    python -m getOC -i MODIS-Terra -l L2 <filename> -u <earthdata-username> -w -p SST --box 60
    python -m getOC -i VIIRSJ1 -l L1A <filename> -u <earthdata-username> -w --box 60
    python -m getOC -i OCLI -l L1 <filename> -u <creodias-username> -w -p OC --box 60
    python -m getOC -i OCLI -l L2_WRR <filename> -u <creodias-username> -w -p OC --box 60
    python -m getOC -i MSI -l L1C <filename> -u <creodias-username> -w -p OC --box 60

    python -m getOC -i <instrument> -l L3BIN -s yyyymmdd -e yyyymmdd -b <binning-period> -g <geophysical-parameter>     DEPRECATED

If you only need to download images in a given time frame without specifying a position, the [File Search](https://oceandata.sci.gsfc.nasa.gov/api/file_search) utility from NASA might be a better tool. The NASA utility also provides a few wget examples on this [Ocean Color Forum Post](https://oceancolor.gsfc.nasa.gov/forum/oceancolor/topic_show.pl?pid=12520).

A strong internet connection is recommended. 

### List of samples
For level 1 and level 2 downloads only (not needed for level 3), a comma separated value (csv) file must be prepared before using getOC. Each line of the csv file must contain the following information (ex: `test.csv`):
    - variable name: sample_id,date&time,latitude,longitude
    - variable type/units: string,yyyy/mm/dd HH:MM:SS (UTC),degN,degE

Images will be downloaded if they are in the same day UTC as the one specified by the date of the point of interest. For times close to the beginning or the end of the day it can be worth adding a line with the previous or following day.

### Level 1
For **MODIS-Aqua**:
   
    ./getOC -i MODIS-Aqua -l L1A test.csv -u <earthdata-username> -w --box 60
   
Note GEO file are included in SeaDAS for MODIS-Aqua (no need to download them).
   
For **VIIRSN**:

    ./getOC -i VIIRSN -l L1A test.csv -u <earthdata-username> -w --box 60
    
Note getOC will automatically download GEO files in the same time as L1A files for VIIRSN L1A.

For **VIIRSJ1**:

    ./getOC -i VIIRSJ1 -l L1A test.csv -u <earthdata-username> -w --box 60
    
Note getOC will automatically download GEO files in the same time as L1A files for VIIRSJ1 L1A.
    
For **OLCI**:
    Use either level L1 or L1_EFR for full resolution
    Use either level L1_ERR for low resolution
    
    ./getOC -i OLCI -l L1 test.csv -u <creodias-username> -w --box 60
    
Note no need for GEO files (images are already geo referenced).

For **SLSTR**:
    Use either level L1 or L1_RBT
    
    ./getOC -i SLSTR -l L1 test.csv -u <creodias-username> -w --box 60
    
Note no need for GEO files (images are already geo referenced).

For **MSI**:
    
    ./getOC -i MSI -l L1C test.csv -u <creodias-username> -w --box 60
    
Note no need for GEO files (images are already geo referenced).

SeaWiFS is not supported by getOC at level 1.


### Level 2
For **MODIS-Aqua**:
    Choose either OC or SST
   
    ./getOC -i MODIS-Aqua -l L2 test.csv -u <earthdata-username> -p OC -w --box 60
   
For **VIIRSN**:
    Choose either OC or SST

    ./getOC -i VIIRSN -l L2 test.csv -u <earthdata-username> -p OC -w --box 60
    
For **VIIRSJ1**:
    Only OC available

    ./getOC -i VIIRSJ1 -l L2 test.csv -u <earthdata-username> -p OC -w --box 60
    
For **OLCI**:
    Only OC available
    Use either level L2 or L2_WFR for full resolution
    Use either level L1_ERR for low resolution
    
    ./getOC -i OLCI -l L1 test.csv -u <creodias-username> -w --box 60
    
For **SLSTR**:
    Only SST available
    Use either level L2 or L2_WST (default; GHRSST recommendations) or L2_WCT for weighted combinations of brightness temperatures
    
    ./getOC -i SLSTR -l L2 test.csv -u <creodias-username> -w --box 60

For **MSI**:
    
    ./getOC -i MSI -l L2A test.csv -u <creodias-username> -w --box 60
    

### Level 3 DEPRECATED
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

