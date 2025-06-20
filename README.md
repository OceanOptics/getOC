getOC
=====

_Bulk download Ocean Color images from ESA and NASA platforms._

getOC is a python utility simplifying bulk download of Ocean Color images from [NASA Ocean Data](https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/) and [ESA COPERNICUS Dataspace](https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json?) APIs. getOC takes as input a csv file with the list of positions and dates of interest (ex: test.csv) and it downloads images for the selected
instrument, processing level, and product type. Depending on the options selected an [EARTHDATA](https://urs.earthdata.nasa.gov/users/new) or a [COPERNICUS dataspace] (https://identity.dataspace.copernicus.eu/auth/realms/CDSE/login-actions/registration?client_id=cdse-public&tab_id=G8kjxyKCxI8) account is required. A strong internet connection is recommended.

Synthax for ESA satellite collections can be found [here](https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel3/describe.xml) (example for Sentinel-3 collection)

DEPRECATED: Previous getOC versions used the Creodias API but the Creodias v2 API required 2 step authentications preventing automatic downloads. ESA satellites (+Landsat over europe) are now downloaded using the new Copernicus API

If you only need to download images in a given time frame without specifying a position, the [File Search](https://oceandata.sci.gsfc.nasa.gov/api/file_search) utility from NASA might be a better tool. The NASA utility also provides a few wget examples on this [Ocean Color Forum Post](https://oceancolor.gsfc.nasa.gov/forum/oceancolor/topic_show.pl?pid=12520).

## Supported instrument

| Instrument Name | Instrument Acronym | Temporal Coverage | Spatial Coverage | Level | L2 Product | 
| --- | --- | --- | --- | --- | --- |
| Coastal Zone Color Scanner (CZCZ) | CZCZ | 1978-1986 | global@1km | L1A, L2, L3m | OC |
| Ocean Color Temperature Sensor (OCTS) | OCTS | 1996-1997 | global@700m | L1A, L2 | OC |
| Sea Viewing Wide Field Scanner (SeaWiFS) | SeaWiFS | 1997-2010@daily | global@1.1km | L1A, L2, L3m | OC |
| Moderate Resolution Imaging Spectroradiometer (MODIS, Terra) | MODIS-Terra | 1999-now@daily | global@0.25,0.5,1km | L1A, L2, L3m | OC |
| Moderate Resolution Imaging Spectroradiometer (MODIS, Aqua) | MODIS-Aqua | 2002-now@daily | global@0.25,0.5,1km | L1A, L2, L3m | OC, SST |
| MEdium Resolution Imaging Spectrometer (MERIS, Full/Reduced Resolution) | MERIS-FR, MERIS-FR | 2002-2012@daily | global@300m-1km | L1, L2 | OC |
| Geostationary Ocean Color Imager (GOCI) | GOCI | 2010-now@hourly | 36ºN 130ºE@500m | L1B, L2 | OC |
| Visible Infrared Imaging Radiometer Suite (VIIRS, Suomi NPP) | VIIRSN | 2011-now@daily | global@1km | L1A, L2, L3m | OC, SST |
| Visible Infrared Imaging Radiometer Suite (VIIRS, JPSS-1) | VIIRSJ1 | 2017-now@daily | global@1km | L1A, L2, L3m | OC |
| MultiSpectral Instrument (MSI, Sentinel-2A/B) | MSI | 2015-now@5days | coastal@10,20,60m | L1C, L2A | OC |
| Ocean and Land Colour Instrument (OLCI, Sentinel-3A/B) | OLCI | 2016-now@daily | global@300m-1km | L1-EFR, L1-ERR, L2-WFR, L2-WRR, L2-LFR, L2-LRR | OC |
| Sea and Land Surface Temperature Radiometer (SLSTR, Sentinel-3A/B) | SLSTR | 2016-now@daily | global@1km | L1-RBT, L2-WST, L2-LST, L2-AOD, L2-FRP | SST |
| OLCI/SLSTR Synergy products (SYN, Sentinel-3A/B) | SYN | 2016-now@daily | global@1km | L2-SYN, L2-V10, L2-VG1, L2-VGP, L2-AOD | OC, SST |
| SAR Radar Altimeter (SRAL, Sentinel-3A/B) | SRAL | 2016-now@daily | global@300m | L1-SRA, L1-SRA-A, L1-SRA-BS, L2-WAT, L2-LAN, L2-LAN-HY, L2-LAN-LY, L2-WAT-SI | OTHER (Altimeter) |
| Synthetic Aperture Radar (SAR, Sentinel-1A/B) | SAR | 2014-now@12days | global@5m | L0-RAW, L1-GRD, L1-GRD-COG, L1-SLC, L2-OCN, L2-CARD-BS, L2-CARD-COH12 | OTHER (ice, fishing, and oil spill monitoring) |
| Thematic Mapper (TM, Landsat-5) | L5-TM | 1984-2013@16days | Europe@30m-OC 120m-SST | L1G, L1T | OC, SST |
| Enhenced Thematic Mapper Plus (ETM+, Landsat-7) | L7-ETM | 1999-2011@16days | Europe@30m-OC 120m-SST | L1G, L1GT, L1T, TC-1P | OC, SST |
| Operational Land Imager (OLI) & Thermal Infrared Sensor (TIRS) (Landsat-8) | L8-OLI-TIRS | 2013-now@16days | Europe@30m-OC 100m-SST | L1, L1GT, L1T, L1TP, L2, L2SP| OC, SST |

Resolutions are indicative for Level 1 and 2 data, Level 3 is only available at 4 or 9 km for NASA satellites.


## Command Line Usage

Typical call from bash:

    python getOC.py -i VIIRSJ1 -l L2 <csv_filename> -u <earthdata-username> -w --box 60

### Argument description:
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
     - `SYN`
     - `SRAL`
     - `MSI`
     - `GOCI`
     - `L5-TM`
     - `L7-ETM`
     - `L8-OLI-TIRS`
- `-l LEVEL`, `--level=LEVEL`: specify processing level, available options are listed below (c.f. table above for level compatible with the instrument selected).
     - MODIS-Aqua MODIS-Terra VIIRSN VIIRSJ1 SeaWiFS OCTS CZCS:  
         - `L1A`
         - `L2`
         - `L3b`
         - `L3m`
     - OLCI:  
         - `L1-EFR` full resolution or `L1_ERR` reduced resolution  
         - `L2-WFR` full resolution or `L2_WRR` reduced resolution [Water]  
         - `L2-LFR` full resolution or `L2_LRR` reduced resolution [Land]  
     - SLSTR:  
         - `L1-RBT`
         - `L2_WST` [Water temperature]  
         - `L2_LST` [Land temprature]  
         - `L2_AOD` [Aerosol optical depth]  
         - `L2_FRP` [Fire radiative power]  
     - SRAL:  
         - `L1-SRA`
         - `L1-SRA-A`
         - `L1-SRA-BS`
         - `L2-WAT` [Water altimetry]  
         - `L2-LAN` [Land altimetry]  
         - `L2-LAN-HY`
         - `L2-LAN-LY`
         - `L2-LAN-SI`
     - SYN:  
         - `L2-SYN` [Reflectance and aerosol parameter over land]  
         - `L2-V10` [Vegetation-Like product (~VGT-S10), 10 day synthesis surface reflectance and NDVI]  
         - `L2-VG1` [Vegetation-Like product (~VGT-S1), 1 day synthesis surface reflectance and NDVI]  
         - `L2-VGP` [Vegetation-Like product (~VGT-P), TOA reflectance]  
         - `L2-AOD` [Aerosol optical depth over land and water 4.5x4.5 km resolution]  
     - MERIS:  
         - `L1`
         - `L2`
         - `L3b`
         - `L3m`
     - SAR:  
         - `L0-RAW`
         - `L1-GRD`
         - `L1-GRD-COG`
         - `L1-SLC`
         - `L2-OCN`
         - `L2-CARD-BS`
         - `L2-CARD-COH12`
     - GOCI:
         - `L1B`
         - `L2`
     - MSI:  
         - `L1C`
         - `L2A`
- `-u USERNAME`, `--username=USERNAME`: specify username to login to Copernicus (for OLCI, SLSTR, SLAR, SAR, MSI, L5-TM, L7-ETM and L8-OLI-TIRS instruments) or
  EarthData (for any other sensor). Password will be prompted when the script is executed. (TO DO: add option to use a credential file *credentials.ini*)
     - Earthdata login for NASA satellites  
     - Copernicus dataspace login for ESA satellites
- `-w`, `--write-image-name`: getOC first query an api to retrieve the list of images to download. The output of that query can be written to a csv file. getOC can then be restarted directly from that file saving that query time.
- `-r`, `--read-image-list`: getOC loads the list previously queried and printed, to avoid querying twice the same list
- `-q`, `--quiet`: Quiet please ! getOC does not output any information relative to the download and querying of the points of interest.

- `-p` product  
    Specify the product type to download:  
     - `OC`  [default]  
     - `IOP`
     - `SST`


Options specific to a level:

- Level 1 & 2:
    - `--box=BOUNDING_BOX_SIZE`, `--bounding-box-size=BOUNDING_BOX_SIZE`: Define the size of the bounding box around the
      point of interest in nautical miles. getOC downloads all images that intersect with this box (must be > 0).
- Level 2 & 3:
    - `-p PRODUCT`, `--product=PRODUCT`: Specify the product type to download (only for NASA satellites) (c.f. table above for level compatible
      with the instrument selected):
        - Level 2 (NASA):
            - `OC`     (default)
            - `IOP`    (deprecated)
            - `SST`
        - Level 3 (NASA):
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

- ESA Copernicus downloads only:
    - `-c CLOUD_COVER_INTERVAL`, `--cloud-cover=CLOUD_COVER_INTERVAL`: Cloud cover interval to download (in %):
        - `-c [0 100]`: download all images [default]
        - `-c [0 80]`: download all images with less than 80% cloud cover
        - `-c [0 20]`: download all images with less than 20% cloud cover
        - ...

- NASA Ocean Color Level 1&2 Browser:
    - `-d QUERY_DELAY`, `--delay=QUERY_DELAY`: Delay between queries only needed to query L1L2_browser. (default=1 second)

Instruments specificity:

- VIIRS: GEO files required to process L1A files from that sensor are downloaded automatically when the level L1A is
  selected for this instrument.
- Level synthax for ESA satellites are specific to sensors providing different options: Use L1-EFR for OLCI full resolution data and L1-ERR for low resolution (cf table and level paragraph)

### Examples:

Level 1:

    python getOC.py -i MODIS-Aqua -l L1A test.csv -u <earthdata-username> -w --box 60
    python getOC.py -i GOCI -l L1B test.csv -u <copernicus-username> -w --box 60 
    python getOC.py -i VIIRSN -l L1A test.csv -u <earthdata-username> -w --box 60
    python getOC.py -i VIIRSJ1 -l L1A test.csv -u <earthdata-username> -w --box 60
    python getOC.py -i MSI -l L1C test.csv -u <copernicus-username> -w --box 60
    python getOC.py -i OLCI -l L1-EFR test.csv -u <copernicus-username> -w --box 60
    python getOC.py -i SLSTR -l L1-WST test.csv -u <copernicus-username> -w --box 60
    python getOC.py -i SRAL -l L1-RBT test.csv -u <copernicus-username> -w --box 60
    python getOC.py -i L5-TM -l L1T test.csv -u <copernicus-username> -w --box 60

Level 2:

    python getOC.py -i MODIS-Aqua -l L2 test.csv -u <earthdata-username> -p OC -w --box 60
    python getOC.py -i GOCI -l L2 test.csv -u <copernicus-username> -w --box 60
    python getOC.py -i VIIRSN -l L2 test.csv -u <earthdata-username> -p OC -w --box 60
    python getOC.py -i VIIRSJ1 -l L2 test.csv -u <earthdata-username> -p OC -w --box 60
    python getOC.py -i MSI -l L2A test.csv -u <copernicus-username> -w --box 60 
    python getOC.py -i OLCI -l L2-WRR test.csv -u <copernicus-username> -w --box 60
    python getOC.py -i SLSTR -l L2-WST test.csv -u <copernicus-username> -w --box 60
    python getOC.py -i SYN -l L2-AOD test.csv -u <copernicus-username> -w --box 60
    python getOC.py -i L8-OLI-TIRS -l L2 test.csv -u <copernicus-username> -w --box 60

Level 3:

    python getOC.py -i MODIS-Aqua -l L3b test.csv <earthdata-username> -p CHL -b 8D --res 4km -w
    python getOC.py -i MODIS-Aqua -l L3m test.csv <earthdata-username> -p CHL -b YR --res 9km -w

