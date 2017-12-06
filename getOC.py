#!/usr/bin/env python
"""
Bulk download Ocean Color images.

  python -m getOC -i <instrument> -l <level> -p <product> <filename>
  python getOC.py -i <instrument> -l <level> -p <product> <filename>

instruments supported are:
    - VIIRS
    - MODIS
    - OLCI

level of processing supported are:
    - L1A
    - l2    [default]

product supported are (only for level L2):
    - OC    [default]
    - IOP
    - SST

Path to a CSV file containing the following should be provided.
    - variable name: id,date&time,latitude,longitude
    - variable type/units: string,yyyy/mm/dd HH:MM:SS (UTC),degN,degE

Image within 24 hours are downloaded. (To verify)
For OCLI only level L1 is supported (level and product arguments are ignored)

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
import requests
import re
import os

__version__ = "0.2"
verbose = False

# Constants and query for file_search
# LEVEL = {'All Types': 'all', 'Level 0': 'L0', 'Level 1': 'L1', 'Level 2': 'L2', 'Level 3 Bin': 'L3b', 'Level 3 SMI': 'L3m', 'Ancillary': 'MET', 'Miscellaneous': 'misc'}
# MISSION = {'All Missions': 'all', 'Aquarius':'aquarius', 'SeaWiFS':'seawifs', 'MODIS Aqua':'aqua', 'MODIS Terra':'terra', 'MERIS':'meris', 'OCTS':'octs', 'CZCS':'czcs', 'HICO':'hico', 'VIIRS':'viirs'}
# URL_FILE_SEARCH = 'https://oceandata.sci.gsfc.nasa.gov/api/file_search'
# r = requests.post(URL_FILE_SEARCH, {'instrument':'octs', 'sdate':'1996-11-01', 'edate':'1997-01-01','dtype':'L2', 'addurl':1, 'results_as_file':1})

# Set constants
URL_BROWSE ='https://oceancolor.gsfc.nasa.gov/cgi/browse.pl'
URL_GET_FILE = 'https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/'

# Documentation of Ocean Color Data Format Specification
#   https://oceancolor.gsfc.nasa.gov/products/
# Documentation regarding product definition
#   https://oceancolor.gsfc.nasa.gov/products/
INSTRUMENT_FILE_ID = {'SeaWiFS': 'S', 'MODIS-Aqua': 'A', 'TerraMODIS': 'T', 'OCTS': 'O','CZCS': 'C','MERIS': 'M','VIIRS': 'V','HICO': 'H', 'OLCI':'S3A_OL_1_ERR'}
INSTRUMENT_QUERY_ID = {'SeaWiFS': 'MLAC', 'MODIS-Aqua': 'am', 'TerraMODIS': 'tm', 'OCTS': 'oc','CZCS': 'cz','MERIS': 'RR','VIIRS': 'v0','HICO': 'hi', 'OLCI':'ERR'};
DATA_TYPE_ID = {'SeaWiFS':'LAC', 'MODIS-Aqua': 'LAC', 'TerraMODIS': 'LAC', 'OCTS': 'LAC', 'CZCS': '', 'MERIS':'RR', 'VIIRS': 'SNPP', 'HICO':'ISS', 'OLCI':'ERR'}
EXTENSION_L1A = {'MODIS-Aqua': '', 'VIIRS': '.nc'};

def get_image_list(filename, instrument, level='L2', product='OC'):
    # Get image name for each line of csv file provided
    #
    # CSV File should be formated as follow:
    #   variable name: id,date&time,latitude,longitude
    #   variable type/units: string,yyyy/mm/dd HH:MM:SS (UTC),degN,degE

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
                else:
                    if verbose:
                        print('level not supported.')
                    return None
        else:
            if verbose:
                print('instrument not supported.')
            return None

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
        if instrument == 'MODIS-Aqua' and level == 'L1A':
            image_names = [image_name + '.bz2' for image_name in image_names]
        if instrument == 'OLCI':
            image_names = [sen_pre + image_name + sen_pos for image_name in image_names]
        return list(set(image_names))
    if verbose:
        print('unable to open file.')
    return None

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


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser(usage="Usage: getOC.py [options] filename", version="getOC " + __version__)
    parser.add_option("-i", "--instrument", action="store", dest="instrument", help="specify instrument, available options are: VIIRS, MODIS-Aqua, and OLCI")
    parser.add_option("-l", "--level", action="store", dest="level", default='L2', help="specify processing level, available options are: L1A, and L2")
    parser.add_option("-p", "--product", action="store", dest="product", default='OC', help="specify product identifier, available options are: OC, SST, and IOP")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True)
    (options, args) = parser.parse_args()

    verbose = options.verbose
    if options.instrument is None:
        print(parser.usage)
        print('getOC.py: error: option -i, --instrument is required')
        sys.exit(-1)

    if len(args) < 1:
        print(parser.usage)
        print('getOC.py: error: argument filename is required')
        sys.exit(-1)
    elif len(args) > 2:
        print(parser.usage)
        print('getOC.py: error: too many arguments')
        sys.exit(-1)

    image_names = get_image_list(args[0], options.instrument, options.level, options.product)
    if image_names is not None:
        download(image_names)
