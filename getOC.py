#!/usr/bin/env python
"""
Bulk download Ocean Color images.

MIT License

Copyright (c) 2019 Nils Haentjens

author: Nils Haentjens
created: Nov 28, 2017
"""

import csv
import sys
from datetime import datetime
from getpass import getpass
import requests
import re
import os
from time import sleep
from pandas import DataFrame, read_csv
import socket

__version__ = "0.4.0"
verbose = False

# Set constants
URL_L12BROWSER = 'https://oceancolor.gsfc.nasa.gov/cgi/browse.pl'
URL_DIRECT_ACCESS = 'https://oceandata.sci.gsfc.nasa.gov/'
URL_SEARCH_API = 'https://oceandata.sci.gsfc.nasa.gov/api/file_search'
URL_GET_FILE = 'https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/'

# Documentation of Ocean Color Data Format Specification
#   https://oceancolor.gsfc.nasa.gov/products/
INSTRUMENT_FILE_ID = {'SeaWiFS': 'S', 'MODIS-Aqua': 'A', 'MODIS-Terra': 'T', 'OCTS': 'O', 'CZCS': 'C',
                      'MERIS': 'M', 'VIIRS': 'V', 'HICO': 'H', 'OLCI': 'S3'}
INSTRUMENT_QUERY_ID = {'SeaWiFS': 'MLAC', 'MODIS-Aqua': 'amod', 'MODIS-Terra': 'tmod', 'OCTS': 'oc', 'CZCS': 'cz',
                       'MERIS': 'RR', 'VIIRS': 'vrsn', 'HICO': 'hi', 'OLCI': 's3br@s3ar'} # ERR
DATA_TYPE_ID = {'SeaWiFS': 'LAC', 'MODIS-Aqua': 'LAC', 'MODIS-Terra': 'LAC', 'OCTS': 'LAC', 'CZCS': '',
                'MERIS': 'RR', 'VIIRS': 'SNPP', 'HICO': 'ISS', 'OLCI': 'ERR'}
# SEARCH_API_LEVEL = {'All Types': 'all', 'Level 0': 'L0', 'Level 1': 'L1', 'Level 2': 'L2', 'Level 3 Bin': 'L3b',
#                    'Level 3 SMI': 'L3m', 'Ancillary': 'MET', 'Miscellaneous': 'misc'}
SEARCH_API_LEVEL = {'All': 'all', 'L0': 'L0', 'L1': 'L1', 'L2': 'L2', 'L3BIN': 'L3b',
                    'L3SMI': 'L3m', 'Ancillary': 'MET', 'Miscellaneous': 'misc'}
# SEARCH_API_MISSION = {'All Missions': 'all', 'Aquarius': 'aquarius', 'SeaWiFS': 'seawifs', 'MODIS-Aqua': 'aqua',
#                       'MODIS-Terra': 'terra', 'MERIS': 'meris', 'OCTS': 'octs', 'CZCS': 'czcs', 'HICO': 'hico',
#                       'VIIRS': 'viirs'} # DEPRECATED
SEARCH_API_SENSOR = {'All Missions': 'all', 'Aquarius': 'Aquarius', 'SeaWiFS': 'SeaWiFS', 'MODIS-Aqua': 'MODIS Aqua',
                     'MODIS-Terra': 'MODIS Terra', 'MERIS': 'MERIS', 'OCTS': 'OCTS', 'CZCS': 'CZSZ', 'HICO': 'HICO',
                     'VIIRS': 'VIIRS', 'OLCI': 'S3OLCI'}
EXTENSION_L1A = {'MODIS-Aqua': '','MODIS-Terra': '', 'VIIRS': '.nc'}


def get_image_list_from_l12browser(pois, instrument, level='L2', product='OC', query_delay=1):
    # Get image name for each line of csv file provided
    #   support only L0, L1A, GEO, and L2
    #   filter by date and location
    #
    # Get image name for each row of the panda data frame `pois`. `pois` must be formated as follow:
    #   variable name: id, date&time, latitude, longitude
    #   variable type/units: string, yyyy/mm/dd HH:MM:SS (UTC), degN, degE
    #
    # Not output as:
    #   `pois` data frame is altered by this function, a column `image_names` is added and completed.

    image_names = list()
    # Get parameters to build query
    if instrument in INSTRUMENT_FILE_ID.keys():
        if instrument == 'OLCI':
            sen = '&sen=' + INSTRUMENT_QUERY_ID[instrument]
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
            elif level in ['L0', 'L1A']:
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

    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]

    for i, poi in pois.iterrows():
        if verbose:
            print('[' + str(i + 1) + '/' + str(len(pois)) + '] Querying ' + str(poi['id']) + '    ' +
                  str(poi['dt']) + '    ' + "%.5f" % poi['lat'] + '  ' + "%.5f" % poi['lon'])
        # Build Query
        # Add some room in the given location (need to make it stronger if >180 | <-180)
        n, s = str(poi['lat'] + 1), str(poi['lat'] - 1)
        w, e = str(poi['lon'] - 2), str(poi['lon'] + 2)
        day = str((poi['dt'] - datetime(1970, 1, 1)).days)
        query = URL_L12BROWSER + '?sub=' + sub + sen + '&per=DAY&day=' + day + \
                '&n=' + n + '&s=' + s + '&w=' + w + '&e=' + e + '&dnm=' + dnm + '&prm=' + prm
        # Query API
        r = requests.get(query)
        if instrument == 'OLCI':
            # Parse html
            regex = re.compile('>S3' + '(.*?)' + sen_pos)
            pois.at[i, 'image_names'] = list(set(regex.findall(r.text)))  # Get unique id
        else:
            # Parse html
            regex = re.compile('filenamelist&id=(\d+\.\d+)')
            filenamelist_id = regex.findall(r.text)
            if not filenamelist_id:
                # Case one image
                regex = re.compile(sen_pre + '\d+\.' + sen_pos)
                pois.at[i, 'image_names'] = list(set(regex.findall(r.text)))  # Get unique id
            else:
                # Case multiple images
                r = requests.get(URL_L12BROWSER + '?sub=filenamelist&id=' + filenamelist_id[0] + '&prm=' + prm)
                pois.at[i, 'image_names'] = r.text.splitlines()
        # Delay next query (might get kicked by server otherwise)
        sleep(query_delay)

        # Reformat filenames
        if level == 'L2' and product == 'IOP':
            pois.at[i, 'image_names'] = [image_name.replace('OC', 'IOP') for image_name in pois.at[i, 'image_names']]
        elif instrument == 'MODIS-Aqua' and level == 'L1A':
            pois.at[i, 'image_names'] = [image_name + '.bz2' for image_name in pois.at[i, 'image_names']]
        elif instrument == 'OLCI':
            pois.at[i, 'image_names'] = [sen_pre + image_name + sen_pos for image_name in pois.at[i, 'image_names']]
        elif level == 'GEO':
            pois.at[i, 'image_names'] = [image_name.replace('L1A', 'GEO-M') for image_name in pois.at[i, 'image_names']]

    if (instrument == 'VIIRS' and level == 'L1A'):
        geo_names = pois.copy()
        for i in range(len(geo_names)):
            geo_names.at[i, 'image_names'] = [geo_names.at[i, 'image_names'].replace('L1A', 'GEO-M') for geo_names.at[i, 'image_names'] in geo_names.at[i, 'image_names']]
        pois = pois.append(geo_names)

    return pois


def get_image_list_from_direct_access(instrument, start_period, end_period, binning_period='8D',
                                      geophysical_parameter='GSM_chl_gsm_9km', level='L3SMI'):
    # Generate list of images to download from dates and list of filename available at URL_DIRECTACCESS
    #   should support all levels but only tested for L3b
    # reliable but slow

    base_url = URL_DIRECT_ACCESS + instrument + '/' + level + '/'
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
            INSTRUMENT_FILE_ID[instrument] + dt.strftime('%Y%j') + '.*?\.' + SEARCH_API_LEVEL[level] + '_' +
            binning_period + '_' + geophysical_parameter + '\.nc')
        image_names.extend(list(set(regex.findall(r.text))))

    return image_names


# Test function above
# verbose = True
# print(get_image_list_from_direct_access('VIIRS', '20170101', '20180315',
#                                         binning_period='8D', geophysical_parameter='GSM', level='L3BIN'))


def get_image_list_from_search_api(instrument, start_period, end_period, binning_period='8D',
                                   geophysical_parameter='GSM_chl_gsm_9km', level='L3SMI'):
    # USE Search API: simple post request and receive list of files
    #   => Fast

    dt_start = datetime.strptime(start_period, '%Y%m%d')
    dt_end = datetime.strptime(end_period, '%Y%m%d')

    # VIIRS Special treatment
    if instrument == 'VIIRS':
        geophysical_parameter = DATA_TYPE_ID[instrument] + '_' + geophysical_parameter

    # Request OBPG API (might take a long time for server to answer so extend timeout)
    # Order of fields is very important !
    r = requests.post(URL_SEARCH_API, data=
    {'search': '',  # Search specific file
                       'sdate': dt_start.strftime('%Y-%m-%d'), 'edate': dt_end.strftime('%Y-%m-%d'),
     'dtype': SEARCH_API_LEVEL[level],  # Data type (Level)
     'sensor': SEARCH_API_SENSOR[instrument],
     'subID': '',  # Subscription ID
     'subType': 1,  # Subscription type Non-Extracted
     'std_only': 1,  # Only search for standard processed files
     'results_as_file': 1}, timeout=120,  # stream=True,
                      headers={'accept': 'text/plain, text/html',
                               'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4)'
                                             ' AppleWebKit/537.36 (KHTML, like Gecko)'
                                             ' Chrome/66.0.3359.117 Safari/537.36'}
                      )
    # 'addurl': 1,   # Add url prefix at the beginning of each filename
    # field sensor used to be switchable by instrument however instrument returns incomplete files in some cases.

    # Answer can be big so stream answer from API back
    # buffer = ''
    # for chunk in r.iter_content(chunk_size=512):
    #     if chunk:
    #         buffer += chunk.decode(r.encoding, 'replace')
    # print(r.text)
    # print(len(r.text))

    # Filter out answer with regex
    regex = re.compile(INSTRUMENT_FILE_ID[instrument] + '.*?\.' + SEARCH_API_LEVEL[level] + '_' +
                       binning_period + '_' + geophysical_parameter + '\.nc')
    image_names = sorted(list(set(regex.findall(r.text))))

    return image_names


# Test function above
# verbose = True
# print(get_image_list_from_search_api('MODIS-Aqua', '20170101', '20180115',
#                                      binning_period='8D', geophysical_parameter='CHL_chlor_a_4km', level='L3SMI'))
# print(get_image_list_from_search_api('MODIS-Aqua', '20110101', '20111231', write_image_list=False,
#                                      binning_period='8D', geophysical_parameter='GSM_chl_gsm_9km', level='L3SMI'))
# print(get_image_list_from_search_api('VIIRS', '20170101', '20171231', write_image_list=False,
#                                      binning_period='8D', geophysical_parameter='GSM_bbp_443_gsm_9km', level='L3SMI'))


def download(image_names):
    # Download all images provided in list
    if image_names is None:
        if verbose:
            print('No image to download.')
        return None

    for i, image_name in enumerate(image_names):
        if os.path.isfile(image_name):
            if verbose:
                print('[' + str(i + 1) + '/' + str(len(image_names)) + '] Skip ' + image_name)
        else:
            if verbose:
                print('[' + str(i + 1) + '/' + str(len(image_names)) + '] Downloading ' + image_name)
            response = requests.get(URL_GET_FILE + image_name, stream=True)
            handle = open(image_name, "wb")
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
            MAX_RETRIES = 3
            WAIT_SECONDS = 30
            for j in range(MAX_RETRIES):
                try:
                    # Open session
                    with requests.Session() as s:
                        # Login to EarthData
                        s.auth = (username, password)
                        r1 = s.request('get', url)
                        r = s.get(r1.url, auth=(username, password), stream=True, timeout=30)
                        if r.ok:
                            if verbose:
                                print('Downloading ' + i)
                            # Download data
                            handle = open(i, "wb")
                            for chunk in r.iter_content(chunk_size=512):
                                if chunk:
                                    handle.write(chunk)
                            handle.close()
                            break
                        else:
                            print('Unable to login to EarthData.\n'
                              '\t- Did you accept the End User License Agreement for this dataset ?\n'
                              '\t- A typo in the username or password ?\n'
                              '\t- Invalid image name?')
                            return None
                except requests.exceptions.ConnectionError:
                    print('Build https connection failed, download failed, reconnection ...')
                    handle.close()
                except requests.exceptions.ReadTimeout:
                    print('Read time out, download failed, reconnection ...')
                    handle.close()
                except socket.timeout:
                    print('Connetion lost: download failed, reconnection ...')
                    handle.close()
                sleep(WAIT_SECONDS)
            else:
                print('%d connection attempts failed, download aborted.\n'
                    '\t- Check login/username.\n'
                    '\t- Check for connection problems: https://oceancolor.gsfc.nasa.gov/forum/oceancolor/topic_show.pl?tid=6447\n'
                    '\t- Check for blocked IP emailing: connection_problems@oceancolor.gsfc.nasa.gov\n'  % MAX_RETRIES)
                return None

############# DEPRECATED bug at midnight #############
#            # Open session
#            with requests.Session() as s:
#                # Login to EarthData
#                s.auth = (username, password)
#                r1 = s.request('get', url)
#                r = s.get(r1.url, auth=(username, password), stream=True)
#                if r.ok:
#                    if verbose:
#                        print('Downloading ' + i)
#                    # Download data
#                    handle = open(i, "wb")
#                    for chunk in r.iter_content(chunk_size=512):
#                        if chunk:  # filter out keep-alive new chunks
#                            handle.write(chunk)
#                else:
#                    print('Unable to login to EarthData.\n'
#                          '\t- Did you accept the End User License Agreement for this dataset ?\n'
#                          '\t- A typo in the username or password ?')
#                    return None

# image_names = ['S3A_OL_1_ERR____20171118T193838_20171118T202254_20171119T234331_2656_024_313______LN1_O_NT_002.zip', 'S3A_OL_1_ERR____20171124T202355_20171124T210810_20171126T003934_2655_025_014______LN1_O_NT_002.zip', 'S3A_OL_1_ERR____20171120T202724_20171120T211139_20171122T014330_2655_024_342______LN1_O_NT_002.zip', 'S3A_OL_1_ERR____20171121T200117_20171121T204532_20171123T010654_2655_024_356______LN1_O_NT_002.zip', 'S3A_OL_1_ERR____20171125T195748_20171125T204202_20171127T000012_2654_025_028______LN1_O_NT_002.zip', 'S3A_OL_1_ERR____20171117T200445_20171117T204900_20171119T002156_2655_024_299______LN1_O_NT_002.zip']
# login_download(image_names, '<username>', '<password>')


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
    parser.add_option("-d", "--delay", action="store", dest="query_delay", type='float', default=1,
                      help="Delay between queries to find GEO, L1, and L2 data to download")
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
    parser.add_option("-u", "--username", action="store", dest="username", default=None,
                      help="specify username to login to EarthData (only for OLCI)")
    # Other options
    parser.add_option("-w", "--write-image-links", action="store_true", dest="write_image_links", default=False,
                      help="Write links found during queries in csv file.")
    parser.add_option("-r", "--read-image-list", action="store_true", dest="read_image_list", default=False,
                      help="Read previous query")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True)
    (options, args) = parser.parse_args()

    verbose = options.verbose
    if options.instrument is None:
        print(parser.usage)
        print('getOC.py: error: option -i, --instrument is required')
        sys.exit(-1)
    if options.username is None:
        print(parser.usage)
        print('getOC.py: error: option -u, --username is required')
        sys.exit(-1)
    else:
        password = getpass(prompt='EarthData Password: ', stream=None)

    if len(args) < 1 and options.level not in ['L3BIN', 'L3SMI']:
        print(parser.usage)
        print('getOC.py: error: argument filename is required for Level GEO, L1A, or L2')
        sys.exit(-1)
    elif len(args) > 2:
        print(parser.usage)
        print('getOC.py: error: too many arguments')
        sys.exit(-1)
    elif options.instrument == 'OLCI' and options.username is None:
        print(parser.usage)
        print('getOC.py: error: OLCI requires to input a EarthData username (-u <username>)')
        sys.exit(-1)

    if options.level in ['L3BIN', 'L3SMI']:
        # Download Level 3 based on start and end date

        # Get list of images (based on start and end dates)
        # image_list = get_image_list_from_direct_access(options.instrument, options.start_period, options.end_period,
        #                                                options.binning_period, options.geophysical_parameter)
        #                                                # deprecated method
        image_names = get_image_list_from_search_api(options.instrument, options.start_period, options.end_period,
                                                     options.binning_period, options.geophysical_parameter,
                                                     options.level)
        # Write list of images
        if options.write_image_links:
            with open(options.instrument + '_' + options.start_period + '-' + options.end_period + '_' +
                      options.level + '_' + options.binning_period + '_' + options.geophysical_parameter +
                      '.csv', 'w') as f:
                for image_name in image_names:
                    f.write("%s\n" % image_name)
        # Download images
        download(image_names)
    else:
        # Get list of images to download
        if options.read_image_list:
            if os.path.isfile(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                                      options.level + '_' + options.product + '.csv'):
                pois = read_csv(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                                          options.level + '_' + options.product + '.csv',
                                          names=['id', 'dt', 'lat', 'lon', 'image_names'], parse_dates=[1])
                #pois.image_names.replace('[]', np.nan, inplace=True)
                pois.dropna(axis=0, inplace= True)
                #print(pois)
                points_of_interest = pois.copy()
                # Parse image_names
                image_names = list()
                for index, record in pois.iterrows():
                    # Convert 'stringified' list to list
                    imli = record['image_names'].split(';')
                    for im in range(len(imli)):
                        image_names.append(imli[im])
            else:
                if verbose:
                    print('IOError: [Errno 2] File ' + os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                                      options.level + '_' + options.product + '.csv' + ' does not exist')
                sys.exit(0)
        else:
            # Parse csv file containing points of interest
            points_of_interest = read_csv(args[0], names=['id', 'dt', 'lat', 'lon'], parse_dates=[1])
            pois = get_image_list_from_l12browser(points_of_interest, options.instrument, options.level,
                                           options.product, options.query_delay)
            points_of_interest = pois.copy()
            # parse image_names
            image_names = list()
            for _, pois in pois.iterrows():
                image_names.extend(pois['image_names'])

        # Write image names
        if options.write_image_links:
            # Reformat image names
            for i, poi in points_of_interest.iterrows():
                points_of_interest.at[i, 'image_names'] = ';'.join(poi['image_names'])
            points_of_interest.to_csv(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                                      options.level + '_' + options.product + '.csv',
                                      date_format='%Y/%m/%d %H:%M:%S', header=False, index=False, float_format='%.5f')
        # Download for Level 1 and 2 requires a list of images to download generated from the filename
        if options.username is not None:
            login_download(image_names, options.username, password)
        else:
            print('download without login is deprecated and might not work.')
            download(image_names)