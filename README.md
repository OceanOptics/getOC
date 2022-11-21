getOC
=====

_Bulk download Ocean Color images (ESA and NASA platforms)._

getOC is a python utility in command line to easily bulk download Ocean Color images from [NASA Ocean Data](https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/) and [ESA CREODIAS](https://finder.creodias.eu/resto/api2/collections/Sentinel2/search.json?) APIs. Provide a list of positions and dates in a csv file (ex: test.csv), select an instrument, a processing level, and a product type and getOC will get the images.

[EARTHDATA account](https://urs.earthdata.nasa.gov/users/new) required to download NASA satellites data
[CREODIAS account](https://auth.creodias.eu/auth/realms/dias/protocol/openid-connect/auth?scope=openid+profile+email&response_type=code&redirect_uri=https%3A%2F%2Fcreodias.eu%2Fc%2Fportal%2Flogin&state=9ff87a6f1cefa7fa0e8ec5b49bf9bc33&client_id=CLOUDFERRO_PARTNERS&response_mode=query) required to download ESA satellites data

Level 3 'L3b' and 'L3m' download are only available for NASA satellites

### Argument description:
- **`-i`** **instrument**  
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
     - **`GOCI`**  

- **`-l`** **level**  
     - **MSI**:  
         - **`L1C`**
         - **`L2A`**  

     - **MODIS-Aqua** **MODIS-Terra** **VIIRSN** **VIIRSJ1** **SeaWiFS** **OCTS** **CZCS**:  
         - **`L1A`**  
         - **`L2`**  
         - **`L3b`**  
         - **`L3m`**  

     - **OCLI** full resolution [default]:  
         - **`L1`** or **`L1_EFR`**  
         - **`L2`** or **`L2_WFR`**  

     - **OCLI** low resolution:  
         - **`L1_ERR`**  
         - **`L2_WRR`**  

     - **SLSTR** low resolution:  
         - **`L1`** or **`L1_RBT`**  
         - **`L2`** or **`L2_WST`** [default; GHRSST recommendations]  
         - **`L2_WCT`** [weighted combinations of brightness temperatures]  

     - **MERIS**:  
         - **`L1`**  
         - **`L2`**  
         - **`L3b`**  
         - **`L3m`** 

     - **GOCI**:
         - **`L1B`**  
         - **`L2`**  

- **`-u`** **username**  
     - Earthdata login for NASA satellites  
     - Creodias login for ESA satellites

- **`-w`** **write**  
     - Prints the image list on a copy of the csv file after the query is completed.

- **`-r`** **read**  
     - getOC loads the list previously queried and printed, to avoid querying twice the same list

- **`-p`** **product**  
    Specify the product type to download:  
     - **`OC`**    [default]  
     - **`IOP`**  
     - **`SST`**  

**`--box`** **bounding box**  
   - Define the size of the bounding box around the point of interest in nautical miles. Downloads all images that intersect with this box (must be > 0).

**`-q`** **quiet**  
   - Quiet please ! getOC does not output any information relative to the download and querying of the points of interest.

### Usage examples:
    python getOC -i MODIS-Aqua -l L2 <filename> -u <earthdata-username> -w -p OC --box 60
    python getOC -i MODIS-Terra -l L2 <filename> -u <earthdata-username> -w -p SST --box 60
    python getOC -i VIIRSJ1 -l L1A <filename> -u <earthdata-username> -w --box 60
    python getOC -i OLCI -l L1 <filename> -u <creodias-username> -w -p OC --box 60
    python getOC -i OLCI -l L2_WRR <filename> -u <creodias-username> -w -p OC --box 60
    python getOC -i MSI -l L1C <filename> -u <creodias-username> -w -p OC --box 60
    python getOC -i MODIS-Aqua -l L3m test.csv <earthdata-username> -p CHL -b 8D --res 4km -w

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

For **GOCI**:  
    
    ./getOC -i GOCI -l L1B test.csv -u <creodias-username> -w --box 60

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

For **GOCI**:  
    
    ./getOC -i GOCI -l L2 test.csv -u <creodias-username> -w --box 60
    

### Level 3
At level 3 the worlds ocean is downloaded. getOC ignores the latitude and longitude in the input csv file. Usage:

    ./getOC -i MODIS-Aqua -l <L3b|L3m> test.csv -u <earthdata-username> -p <product> -b <binning-period> --res 4km -w

Examples:

    python getOC -i MODIS-Aqua -l L3b test.csv -u <earthdata-username> -p POC -b DAY --res 4km -w
    python getOC -i MODIS-Aqua -l L3m test.csv -u <earthdata-username> -p CHL -b 8D --res 9km -w
    python getOC -i MODIS-Aqua -l L3m test.csv -u <earthdata-username> -p CHL -b MO --res 9km -w