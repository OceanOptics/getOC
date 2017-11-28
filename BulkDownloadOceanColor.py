#!/usr/bin/env python
"""
Utility made to easily manage bulk download of Ocean Color images.

  python -m BulkDownloadOceanColor -s <sensor> <filename>
  python BulkDownloadOceanColor.py -s <sensor> <filename>

Sensors supported are:
    - VIIRS_OC
    - MODIS_OC
    - MODIS_SST (include night time images)

Path to a CSV file containing the following should be provided.
    - variable name: id,date&time,latitude,longitude
    - variable type/units: string,yyyy/mm/dd HH:MM:SS (UTC),degN,degE

Only Ocean Color Level 2 is downloaded.
Image within 24 hours are downloaded. (Need validation.)

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

__version__ = "0.1"
verbose = False

# Set constants
# LEVEL = {'All Types': 'all', 'Level 0': 'L0', 'Level 1': 'L1', 'Level 2': 'L2', 'Level 3 Bin': 'L3b', 'Level 3 SMI': 'L3m', 'Ancillary': 'MET', 'Miscellaneous': 'misc'}
# MISSION = {'All Missions': 'all', 'Aquarius':'aquarius', 'SeaWiFS':'seawifs', 'MODIS Aqua':'aqua', 'MODIS Terra':'terra', 'MERIS':'meris', 'OCTS':'octs', 'CZCS':'czcs', 'HICO':'hico', 'VIIRS':'viirs'}
# URL_FILE_SEARCH = 'https://oceandata.sci.gsfc.nasa.gov/api/file_search'
URL_BROWSE ='https://oceancolor.gsfc.nasa.gov/cgi/browse.pl'
URL_GET_FILE = 'https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/'

def get_image_list(sensor, filename):
    # Get image name for each line of csv file provided
    #
    # CSV File should be formated as follow:
    #   variable name: id,date&time,latitude,longitude
    #   variable type/units: string,yyyy/mm/dd HH:MM:SS (UTC),degN,degE

    image_names = list()
    with open(filename) as fid:
        # Pre-build query
        if sensor == 'VIIRS_OC':
            sen, sen_pre, sen_pos =  'v0', 'V', 'L2_SNPP_OC'# VIIRS (v0), MODIS Aqua (am)
            dnm = 'D'
        elif sensor == 'MODIS_OC':
            sen, sen_pre, sen_pos =  'am', 'A', 'L2_LAC_OC'
            dnm = 'D'
        elif sensor == 'MODIS_SST':
            sen, sen_pre, sen_pos =  'am', 'A', 'L2_LAC_SST'
            dnm = 'D@N'
        else:
            print('Sensor not supported.')
            sys.exit(-1)
        # dnm = 'D' # day (D), night (N) or day and night (D@N)
        sub = 'level1or2list'
        # For each line in csv file
        for l in csv.reader(fid, delimiter=','):
            lid, dt, lat, lon = l[0], datetime.strptime(l[1], '%Y/%m/%d %H:%M:%S'), float(l[2]), float(l[3])
            if verbose:
                print('Querying ' + lid + ' ' + str(dt) + ' ' + str(lat) + ' ' + str(lon))
            # Query file search (no location option)
            # r = requests.post(URL_FILE_SEARCH, {'sensor':'octs', 'sdate':'1996-11-01', 'edate':'1997-01-01','dtype':'L2', 'addurl':1, 'results_as_file':1})
            # Build Query
            # Add some room in the given location (need to make it stronger if >180 | <-180)
            n, s = str(lat+1), str(lat-1)
            w, e = str(lon-2), str(lon+2)
            day = str((dt - datetime(1970,1,1)).days)
            query = URL_BROWSE + '?sub=' + sub + '&sen=' + sen + '&per=DAY&day=' + day + '&n=' + n + '&s=' + s + '&w=' + w + '&e=' + e + '&dnm=' + dnm
            # Query API
            r = requests.get(query)
            # Parse html
            regex = re.compile('filenamelist&id=(\d+\.\d+)')
            filenamelist_id = regex.findall(r.text)
            if not filenamelist_id:
                # Case one image
                regex = re.compile('' + sen_pre + '\d+\.'+ sen_pos + '.nc')
                image_names.extend(list(set(regex.findall(r.text)))) # Get unique id
            else:
                # Case multiple images
                r = requests.get(URL_BROWSE + '?sub=filenamelist&id=' + filenamelist_id[0])
                for foo in r.text.splitlines():
                    image_names.append(foo)
        return list(set(image_names))

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

    parser = OptionParser(usage="Usage: BulkDownloadOceanColor.py [options] filename", version="BulkDownloadOceanColor.py " + __version__)
    parser.add_option("-s", "--sensor", action="store", dest="sensor", help="specify sensor, available options are: VIIRS_OC, MODIS_OC, and MODIS_SST")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True)
    (options, args) = parser.parse_args()

    verbose = options.verbose
    if options.sensor is None:
        print('Option -s, --sensor is required')
        sys.exit(-1)

    if len(args) < 1:
        print('Missing path to csv file.')
        sys.exit(-1)
    elif len(args) > 2:
        print('Too many arguments.')
        sys.exit(-1)

    image_names = get_image_list(options.sensor, args[0])
    download(image_names)
