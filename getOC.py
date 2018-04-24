#!/usr/bin/env python
"""
Bulk download Ocean Color images.

  python -m getOC -i <instrument> -l <level> -p <product> <filename>
  python getOC.py -i <instrument> -l <level> -p <product> <filename>
  python getOC.py -i <instrument> -l L3BIN -s yyyymmdd -e yyyymmdd -b <binning-period> -g <geophysical-parameter>

  python getOC.py -i VIIRS -s 20111201 -e 20180423 -b MO -g GSM -l L3BIN
  python getOC.py -i MODIS-Aqua -s 20020101 -e 20180423 -b MO -g GSM -l L3BIN
  python getOC.py -i SeaWiFS -s 19970101 -e 20101231 -b MO -g GSM_chl_gsm_9km -l L3SMI

instruments supported are:
    - VIIRS
    - MODIS
    - OLCI

level of processing supported are:
    - GEO
    - L1A
    - L2    [default]
    - L3BIN
    - L3SMI

L2 specific product supported are:
    - OC    [default]
    - IOP
    - SST   (only MODIS)

L3BIN and L3SMI specific options are:
    - start of period <str> yyyymmdd
    - end of period   <str> yyyymmdd
    - binning period DAY, 8D, MO, and YR
    - geophysical parameters supported by L3BIN are:
        - CHL, GSM, IOP, KD490, PAR, PIC, POC, QAA, RRS, and ZLEE
        - MODIS also accept SST, SST4, and NSST
    - example of geophysical parameters supported by L3SMI are:
        - CHL_chl_ocx_4km, CHL_chlor_a_4km, GSM_bbp_443_gsm_9km, GSM_chl_gsm_9km, IOP_bb_678_giop_9km, KD490_Kd_490_9km

Path to a CSV file should be provided for GEO, L1A, and L2. Fields in the CSV file are has follow (ex: test.csv).
    - variable name: id,date&time,latitude,longitude
    - variable type/units: string,yyyy/mm/dd HH:MM:SS (UTC),degN,degE

For GEO, L1A, and L2 Image within 24 hours are downloaded. (To verify)
For OCLI only level L1 is supported (level and product arguments are ignored).
Note that you need to provide your EarthData username and password to download OLCI.

author: Nils Haentjens
created: Nov 28, 2017

MIT License

Copyright (c) [year] [fullname]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import csv
import sys
from datetime import datetime
from getpass import getpass
import requests
import re
import os
from time import sleep

__version__ = "0.3.0"
verbose = False

# Constants and query for file_search
# LEVEL = {'All Types': 'all', 'Level 0': 'L0', 'Level 1': 'L1', 'Level 2': 'L2', 'Level 3 Bin': 'L3b', 'Level 3 SMI': 'L3m', 'Ancillary': 'MET', 'Miscellaneous': 'misc'}
# MISSION = {'All Missions': 'all', 'Aquarius':'aquarius', 'SeaWiFS':'seawifs', 'MODIS Aqua':'aqua', 'MODIS Terra':'terra', 'MERIS':'meris', 'OCTS':'octs', 'CZCS':'czcs', 'HICO':'hico', 'VIIRS':'viirs'}
# URL_FILE_SEARCH = 'https://oceandata.sci.gsfc.nasa.gov/api/file_search'
# r = requests.post(URL_FILE_SEARCH, {'instrument':'octs', 'sdate':'1996-11-01', 'edate':'1997-01-01','dtype':'L2', 'addurl':1, 'results_as_file':1})

# Set constants
URL_BROWSE = 'https://oceancolor.gsfc.nasa.gov/cgi/browse.pl'
URL_BROWSE_LIST = 'https://oceandata.sci.gsfc.nasa.gov/'
URL_GET_FILE = 'https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/'

# Documentation of Ocean Color Data Format Specification
#   https://oceancolor.gsfc.nasa.gov/products/
INSTRUMENT_FILE_ID = {'SeaWiFS': 'S', 'MODIS-Aqua': 'A', 'TerraMODIS': 'T', 'OCTS': 'O','CZCS': 'C','MERIS': 'M','VIIRS': 'V','HICO': 'H', 'OLCI':'S3A_OL_1_ERR'}
INSTRUMENT_QUERY_ID = {'SeaWiFS': 'MLAC', 'MODIS-Aqua': 'am', 'TerraMODIS': 'tm', 'OCTS': 'oc', 'CZCS': 'cz',
                       'MERIS': 'RR', 'VIIRS': 'v0', 'HICO': 'hi', 'OLCI': 'ERR'}
DATA_TYPE_ID = {'SeaWiFS':'LAC', 'MODIS-Aqua': 'LAC', 'TerraMODIS': 'LAC', 'OCTS': 'LAC', 'CZCS': '', 'MERIS':'RR', 'VIIRS': 'SNPP', 'HICO':'ISS', 'OLCI':'ERR'}
EXTENSION_L1A = {'MODIS-Aqua': '', 'VIIRS': '.nc'}
SOFTWARENAME_TO_FILENAME = {'L3BIN': 'L3b', 'L3SMI': 'L3m'}


def get_image_list_from_csv(filename, instrument, level='L2', product='OC'):
    # Get image name for each line of csv file provided
    #   support only L0, L1A, GEO, and L2
    #
    # CSV File should be formated as follow:
    #   variable name: id, date&time, latitude, longitude
    #   variable type/units: string, yyyy/mm/dd HH:MM:SS (UTC), degN, degE

    image_names = list()
    with open(filename) as fid:
        # Get parameters to build query
        if instrument in INSTRUMENT_FILE_ID.keys():
            if instrument == 'OLCI':
                sen = '&typ=' + INSTRUMENT_QUERY_ID[instrument]
                sen_pre = INSTRUMENT_FILE_ID[instrument]
                sen_pos = '.zip'
                dnm = 'D'
                prm = 'TC'
                sub = 'level1or2list'
            else:
                sen = '&sen=' + INSTRUMENT_QUERY_ID[instrument]
                sen_pre = INSTRUMENT_FILE_ID[instrument]
                if level == 'L2':
                    # Level 2, need to specify product, adjust day|night
                    sen_pos = level + '_' + DATA_TYPE_ID[instrument] + '_' + product + '.nc'
                    if product in ['OC', 'IOP']:
                        dnm = 'D'
                        prm = 'CHL'
                    elif product in ['SST']:
                        dnm = 'D@N'
                        prm = 'SST'
                    else:
                        if verbose:
                            print('product not supported.')
                        return None
                    sub = 'level1or2list'
                elif level in  ['L0', 'L1A']:
                    # Level 1A specify daily data only
                    sen_pos = level + '_' + DATA_TYPE_ID[instrument] + EXTENSION_L1A[instrument]
                    dnm = 'D'
                    prm = 'TC'
                    sub = 'level1or2list'
                # elif level == 'L3':
                    # sub = 'level3'
                elif level in ['GEO']:
                    sen_pos = 'GEO-M' + '_' + DATA_TYPE_ID[instrument] + '.nc'
                    dnm = 'D'
                    prm = 'TC'
                    sub = 'level1or2list'
                else:
                    raise ValueError("level not supported: '" + level + "'")
        else:
            raise ValueError("instrument not supported:'" + instrument + "'")

        # For each line in csv file
        for l in csv.reader(fid, delimiter=','):
            lid, dt, lat, lon = l[0], datetime.strptime(l[1], '%Y/%m/%d %H:%M:%S'), float(l[2]), float(l[3])
            if verbose:
                print('Querying ' + lid + ' ' + str(dt) + ' ' + str(lat) + ' ' + str(lon))
            # Build Query
            # Add some room in the given location (need to make it stronger if >180 | <-180)
            n, s = str(lat+1), str(lat-1)
            w, e = str(lon-2), str(lon+2)
            day = str((dt - datetime(1970,1,1)).days)
            query = URL_BROWSE + '?sub=' + sub + sen + '&per=DAY&day=' + day + '&n=' + n + '&s=' + s + '&w=' + w + '&e=' + e + '&dnm=' + dnm + '&prm=' + prm
            # Query API
            r = requests.get(query)
            if instrument == 'OLCI':
                # Parse html
                regex = re.compile(sen_pre + '(.*?)'+ sen_pos)
                image_names.extend(list(set(regex.findall(r.text))))
            else:
                # Parse html
                regex = re.compile('filenamelist&id=(\d+\.\d+)')
                filenamelist_id = regex.findall(r.text)
                if not filenamelist_id:
                    # Case one image
                    regex = re.compile(sen_pre + '\d+\.'+ sen_pos)
                    image_names.extend(list(set(regex.findall(r.text)))) # Get unique id
                else:
                    # Case multiple images
                    r = requests.get(URL_BROWSE + '?sub=filenamelist&id=' + filenamelist_id[0] + '&prm=' + prm)
                    for foo in r.text.splitlines():
                        image_names.append(foo)

        # Reformat list
        if level == 'L2' and product == 'IOP':
            image_names = [image_name.replace('OC', 'IOP') for image_name in image_names]
        elif instrument == 'MODIS-Aqua' and level == 'L1A':
            image_names = [image_name + '.bz2' for image_name in image_names]
        elif instrument == 'OLCI':
            image_names = [sen_pre + image_name + sen_pos for image_name in image_names]
        elif level == 'GEO':
            image_names = [image_name.replace('L1A', 'GEO-M') for image_name in image_names]
        return list(set(image_names))
    if verbose:
        print('unable to open file.')
    return None


def get_image_list_from_dates(instrument, start_period, end_period, binning_period='8D',
                              geophysical_parameter='GSM_chl_gsm_9km', level='L3SMI', write_image_list=True):
    # Generate list of images to download from dates and list of filename available at URL_BROWSE_LIST
    #   should support all levels but only tested for L3b

    base_url = URL_BROWSE_LIST + instrument + '/' + level + '/'
    dt_start = datetime.strptime(start_period, '%Y%m%d')
    dt_end = datetime.strptime(end_period, '%Y%m%d')

    # VIIRS Special treatment
    if instrument == 'VIIRS':
        geophysical_parameter = DATA_TYPE_ID[instrument] + '_' + geophysical_parameter

    # Get list of files available matching time
    # List years available within input period
    r = requests.get(base_url)
    regex = re.compile('/' + instrument + '/' + level + '/(\d+)')
    years_selected = [y for y in list(set(regex.findall(r.text))) if dt_start.year <= int(y) <= dt_end.year]
    # List dates available within input period
    dt_selected = list()
    for y in years_selected:
        r = requests.get(base_url + y + '/')
        regex = re.compile('/' + instrument + '/' + level + '/' + y + '/(\d+)')
        dt_available = [datetime.strptime(y + x, '%Y%j') for x in list(set(regex.findall(r.text)))]
        dt_selected.extend([dt for dt in dt_available if dt_start <= dt <= dt_end])
    dt_selected = sorted(dt_selected)
    # List files matching options
    image_names = list()
    i = 0
    for dt in dt_selected:
        if verbose:
            print('#' + str(i) + ' ' + dt.strftime('%Y/%m/%d'))
            i += 1
        run_request = True
        while run_request:
            try:
                r = requests.get(base_url + dt.strftime('%Y/%j/'), timeout=5)
                run_request = False
            except Exception as e:
                print(e)
        regex = re.compile(
            INSTRUMENT_FILE_ID[instrument] + dt.strftime('%Y%j') + '.*?\.' + SOFTWARENAME_TO_FILENAME[level] + '_' +
            binning_period + '_' + geophysical_parameter + '\.nc')
        image_names.extend(list(set(regex.findall(r.text))))

    if write_image_list:
        with open(instrument + '_' + start_period + '-' + end_period + '_' +
                  level + '_' + binning_period + '_' + geophysical_parameter + '.csv', 'w') as f:
            for i in image_names:
                f.write("%s\n" % i)

    return image_names


# Test function above
# verbose = True
# print(get_image_list_from_dates('VIIRS', '20170101', '20180315',
#                                 binning_period='8D', geophysical_parameter='GSM', level='L3BIN'))


def download(image_names):
    # Download all images provided in list
    if image_names is None:
        if verbose:
            print('No image to download.')
        return None

    for i in image_names:
        if os.path.isfile(i):
            if verbose:
                print('Skip ' + i)
        else:
            if verbose:
                print('Downloading ' + i)
            response = requests.get(URL_GET_FILE + i, stream=True)
            handle = open(i, "wb")
            for chunk in response.iter_content(chunk_size=512):
                if chunk:  # filter out keep-alive new chunks
                    handle.write(chunk)


def login_download(image_names, username, password):
    # Login to Earth Data and Download image
    if image_names is None:
        if verbose:
            print('No image to download.')
        return None

    for i in image_names:
        url = URL_GET_FILE + i
        if os.path.isfile(i):
            if verbose:
                print('Skip ' + i)
        else:
            # Open session
            with requests.Session() as s:
                # Login to EarthData
                s.auth = (username, password)
                r1 = s.request('get', url)
                r = s.get(r1.url, auth=(username, password), stream=True)
                if r.ok:
                    if verbose:
                        print('Downloading ' + i)
                    # Download data
                    handle = open(i, "wb")
                    for chunk in r.iter_content(chunk_size=512):
                        if chunk:  # filter out keep-alive new chunks
                            handle.write(chunk)
                else:
                    print('Unable to login to EarthData.\n'
                          '\t- Did you accept the End User License Agreement for this dataset ?\n'
                          '\t- A typo in the username or password ?')
                    return None

# image_names = ['S3A_OL_1_ERR____20171118T193838_20171118T202254_20171119T234331_2656_024_313______LN1_O_NT_002.zip', 'S3A_OL_1_ERR____20171124T202355_20171124T210810_20171126T003934_2655_025_014______LN1_O_NT_002.zip', 'S3A_OL_1_ERR____20171120T202724_20171120T211139_20171122T014330_2655_024_342______LN1_O_NT_002.zip', 'S3A_OL_1_ERR____20171121T200117_20171121T204532_20171123T010654_2655_024_356______LN1_O_NT_002.zip', 'S3A_OL_1_ERR____20171125T195748_20171125T204202_20171127T000012_2654_025_028______LN1_O_NT_002.zip', 'S3A_OL_1_ERR____20171117T200445_20171117T204900_20171119T002156_2655_024_299______LN1_O_NT_002.zip']
# login_download(image_names, 'nhtjs', 'P6a-4L2-sWK-kkh')


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser(usage="Usage: getOC.py [options] [filename]", version="getOC " + __version__)
    parser.add_option("-i", "--instrument", action="store", dest="instrument",
                      help="specify instrument, available options are: VIIRS, MODIS-Aqua, OLCI, and SeaWiFS (L3 only)")
    parser.add_option("-l", "--level", action="store", dest="level", default='L2',
                      help="specify processing level, available options are: GEO, L1A, L2, L3BIN, and L3SMI")
    # Level 2 specific option
    parser.add_option("-p", "--product", action="store", dest="product", default='OC',
                      help="specify product identifier (only for L2), available options are: OC, SST, and IOP")
    # Level 3 specific options
    parser.add_option("-s", "--start-period", action="store", dest="start_period",
                      help="specify start period date (only for L3), yyyymmdd")
    parser.add_option("-e", "--end-period", action="store", dest="end_period",
                      help="specify end period date (only for L3), yyyymmdd")
    parser.add_option("-b", "--binning-period", action="store", dest="binning_period", default='8D',
                      help="specify binning period (only for L3), available options are: DAY, 8D, MO, and YR")
    parser.add_option("-g", "--geophysical-parameter", action="store", dest="geophysical_parameter", default='GSM',
                      help="specify geophysical parameter (only for L3), available options are for L3BIN: "
                           "CHL, GSM, IOP, KD490, PAR, PIC, POC, QAA, RRS, and ZLEE "
                           "MODIS also accept SST, SST4, and NSST;"
                           "example of options for L3SMI are:"
                           "CHL_chl_ocx_4km, CHL_chlor_a_4km, GSM_bbp_443_gsm_9km,"
                           "GSM_chl_gsm_9km, IOP_bb_678_giop_9km, KD490_Kd_490_9km")
    # OLCI specific options
    parser.add_option("-u", "--username", action="store", dest="username", default=None, help="specify username to login to EarthData (only for OLCI)")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True)
    (options, args) = parser.parse_args()

    verbose = options.verbose
    if options.instrument is None:
        print(parser.usage)
        print('getOC.py: error: option -i, --instrument is required')
        sys.exit(-1)

    if len(args) < 1 and options.level not in ['L3BIN', 'L3SMI']:
        print(parser.usage)
        print('getOC.py: error: argument filename is required for Level GEO, L1A, or L2')
        sys.exit(-1)
    elif len(args) > 2:
        print(parser.usage)
        print('getOC.py: error: too many arguments')
        sys.exit(-1)

    if options.level in ['L3BIN', 'L3SMI']:
        # Download Level 3 based on start and end date
        download(get_image_list_from_dates(options.instrument, options.start_period, options.end_period,
                                           options.binning_period, options.geophysical_parameter))
    else:
        # Download for Level 1 and 2 requires a list of images to download generated from the filename
        if options.username is not None:
            password = getpass(prompt='EarthData Password: ', stream=None)
            login_download(get_image_list_from_csv(args[0], options.instrument, options.level, options.product),
                           options.username, password)
        else:
            download(get_image_list_from_csv(args[0], options.instrument, options.level, options.product))
