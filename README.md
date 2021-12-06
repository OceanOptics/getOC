getOC
=====

_Bulk download Ocean Color images from ESA and NASA platforms._

getOC is a python utility simplifying bulk download of Ocean Color images
from [NASA Ocean Data](https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/)
and [ESA CREODIAS](https://finder.creodias.eu/resto/api2/collections/Sentinel2/search.json?) APIs. getOC takes as input
a csv file with the list of positions and dates of interest (ex: test.csv) and it downloads images for the selected
instrument, processing level, and product type. Depending on the options selected
an [EARTHDATA](https://urs.earthdata.nasa.gov/users/new) or a [CREODIAS](https://portal.creodias.eu/register.php)
account is required. A strong internet connection is recommended.

If you only need to download images in a given time frame without specifying a position,
the [File Search](https://oceandata.sci.gsfc.nasa.gov/api/file_search) utility from NASA might be a better tool. The
NASA utility also provides a few wget examples on
this [Ocean Color Forum Post](https://oceancolor.gsfc.nasa.gov/forum/oceancolor/topic_show.pl?pid=12520).

## Supported instrument

| Instrument Name | Instrument Acronym | Temporal Coverage | Spatial Coverage | Level | L2 Product | 
| --- | --- | --- | --- | --- | --- |
| Coastal Zone Color Scanner | CZCZ | 1978-1986 | global@1km | L1A, L2, L3m | OC |
| Ocean Color Temperature Sensor | OCTS | 1996-1997 | global@700m | L1A, L2 | OC |
| Sea Viewing Wide Field Scanner | SeaWiFS | 1997-2010@daily | global@1.1km | L1A, L2, L3m | OC |
| Moderate Resolution Imaging Spectroradiometer Terra | MODIS-Terra | 1999-now@daily | global@0.25,0.5,1km | L1A, L2, L3m | OC |
| Moderate Resolution Imaging Spectroradiometer Aqua | MODIS-Aqua | 2002-now@daily | global@0.25,0.5,1km | L1A, L2, L3m | OC, SST |
| MEdium Resolution Imaging Spectrometer (Reduced/Full Resolution) | MERIS-RR, MERIS-FR@daily | 2002-2012 | global@1km | L1, L2 | OC |
| Geostationary Ocean Color Imager | GOCI | 2010-now@hourly | 36ºN 130ºE@500m | L1B, L2 | OC |
| Visible Infrared Imaging Radiometer Suite (Suomi NPP) | VIIRSN | 2011-now@daily | global@1km | L1A, L2, L3m | OC, SST |
| Visible Infrared Imaging Radiometer Suite (JPSS-1) | VIIRSJ1 | 2017-now@daily | global@1km | L1A, L2, L3m | OC |
| MultiSpectral Instrument (Sentinel-2A/B) | MSI | 2015-now@5days | coastal@10,20,60m | L1C, L2A | OC |
| Ocean and Land Colour Instrument (Sentinel-3A/B) | OLCI | 2016-now@daily | global@300m | L1_EFR, L1_ERR, L2_WFR, L2_WRR | OC |
| Sea and Land Surface Temperature Radiometer (Sentinel-3A/B) | SLSTR | 2016-now@daily | global@0.5-1km| L1, L2_WST, L2_WCT| SST |

Resolutions are indicative for Level 1 and 2 data, Level 3 is only available at 4 or 9 km.

## Command Line Usage

Typical call from bash:

    python getOC -i VIIRSJ1 -l L2 <filename> -u <earthdata-username> -w --box 60

General options:

- `-i INSTRUMENT`, `--instrument=INSTRUMENT`: specify instrument, available options are:
    - `SeaWiFS`
    - `MODIS-Aqua`
    - `MODIS-Terra`
    - `OCTS`
    - `CZCS`
    - `MERIS`
    - `VIIRSN`
    - `VIIRSJ1`
    - `HICO`
    - `OLCI`
    - `SLSTR`
    - `MSI`
    - `GOCI`
- `-l LEVEL`, `--level=LEVEL`: specify processing level, available options are listed below (c.f. table above for level
  compatible with the instrument selected).
    - `GEO`
    - `L1`
    - `L1A`
    - `L1B`
    - `L1C`
    - `L1_EFR` (L1 default for OLCI)
    - `L1_ERR`
    - `L1_RBT` (L1 default for SLSTR)
    - `L2`
    - `L2A`
    - `L2_WFR` (L2 default for OLCI)
    - `L2_WRR`
    - `L2_WST` (default; GHRSST recommendations)
    - `L2_WCT` (weighted combinations of brightness temperatures)
    - `L3m`
- `-u USERNAME`, `--username=USERNAME`: specify username to login to CREODIAS (for OLCI, SLSTR, or MSI instruments) or
  EarthData (for any other sensor). Password will be prompted when the script is executed. Note that if a *
  credentials.ini* file is located in the working directory, the credentials present in that file will be used. In that
  case the option `-u USERNAME` will be ignored and no password will be prompted.
- `-w`, `--write-image-links`: getOC first query an api to retrieve the list of images to download. The output of that
  query can be written to a csv file. getOC can then be restarted directly from that file saving that query time.
- `-r`, `--read-image-list`: getOC loads the list previously queried and printed, to avoid querying twice the same list
- `-q`, `--quiet`: Quiet please ! getOC does not output any information relative to the download and querying of the
  points of interest.

Options specific to a level:

- Level 1 & 2:
    - `--box=BOUNDING_BOX_SIZE`, `--bounding-box-size=BOUNDING_BOX_SIZE`: Define the size of the bounding box around the
      point of interest in nautical miles. getOC downloads all images that intersect with this box (must be > 0).
- Level 2 & 3:
    - `-p PRODUCT`, `--product=PRODUCT`: Specify the product type to download (c.f. table above for level compatible
      with the instrument selected):
        - Level 2:
            - `OC`     (default)
            - `IOP`    (deprecated)
            - `SST`
        - Level 3:
            - `CHL`
            - `POC`
            - not tested: GSM, IOP, KD, LAND, PAR, PIC, QAA, RRS, and ZLEE
- Level 3: at this level the world's ocean is downloaded, getOC ignores the latitude and longitudes in the input csv
  file.
    - `-b BINNING_PERIOD`, `--binning-period=BINNING_PERIOD`: specify binning period (only for L3), available options
      are:
        - DAY (default)
        - 8D
        - MO
        - YR
    - `--res=SRESOL`, `--spatial-resolution=SRESOL`: specify spatial resolution (only for L3), available options are:
        - 4km (default)
        - 9km

Options specific to a downloading platform:

- NASA Ocean Color Level 1&2 Browser:
    - `-d QUERY_DELAY`, `--delay=QUERY_DELAY`:Delay between queries only needed to query L1L2_browser. (default=1
      second)

Instruments specificity:

- VIIRS: GEO files required to process L1A files from that sensor are downloaded automatically when the level L1A is
  selected for this instrument.
- OLCI: use either level L1 or L1_EFR for full resolution and use level L1_ERR for low resolution. Similarly for level
  2: level L2 or L2_EFR for full resolution and use level L2_ERR for low resolution.
- SLSTR: use either level L1 or L1_RBT to download level 1 data.

### Examples:

Level 1:

    ./getOC.py -i MODIS-Aqua -l L1A test.csv -u <earthdata-username> -w --box 60
    ./getOC.py -i GOCI -l L1B test.csv -u <creodias-username> -w --box 60 
    ./getOC.py -i VIIRSN -l L1A test.csv -u <earthdata-username> -w --box 60
    ./getOC.py -i VIIRSJ1 -l L1A test.csv -u <earthdata-username> -w --box 60
    ./getOC.py -i MSI -l L1C test.csv -u <creodias-username> -w --box 60
    ./getOC.py -i OLCI -l L1 test.csv -u <creodias-username> -w --box 60
    ./getOC.py -i SLSTR -l L1 test.csv -u <creodias-username> -w --box 60

Level 2:

    ./getOC.py -i MODIS-Aqua -l L2 test.csv -u <earthdata-username> -p OC -w --box 60
    ./getOC.py -i GOCI -l L2 test.csv -u <creodias-username> -w --box 60
    ./getOC.py -i VIIRSN -l L2 test.csv -u <earthdata-username> -p OC -w --box 60
    ./getOC.py -i VIIRSJ1 -l L2 test.csv -u <earthdata-username> -p OC -w --box 60
    ./getOC.py -i MSI -l L2A test.csv -u <creodias-username> -w --box 60 
    ./getOC.py -i OLCI -l L1 test.csv -u <creodias-username> -w --box 60
    ./getOC.py -i SLSTR -l L2 test.csv -u <creodias-username> -w --box 60

Level 3:

    ./getOC.py -i MODIS-Aqua -l L3b test.csv <earthdata-username> -p CHL -b 8D --res 4km -w

## Module Usage

getOC can be directly integrated into other python applications as follows:

    import getOC
    
    filename = 'test.csv'
    username = 'earthdata-username'
    password = 'earthdata-password'
    instrument = 'MODIS-Aqua'
    level = 'L2'
    product = 'OC'
    
    # Read file with points of interest
    pois = getOC.read_dataset(TEST_FILES[instrument])
    # Get downloading platform and set credentials
    platform = getOC.get_platform(pois.dt.max(), instrument, level)
    platform.username = username
    platform.password = password
    # Query image list
    pois = platform.get_image_list(pois, instrument, level, product=product,
                                   bounding_box_size=60)
    # Download images
    image_names = [item for sublist in pois.image_names.to_list() for item in sublist]
    urls = [item for sublist in pois.urls.to_list() for item in sublist]
    if platform.download_images(image_names, urls) and getOC.verbose:
        print('Download completed')
    
