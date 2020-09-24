#!/usr/bin/env python
"""
Bulk download Ocean Color images.

MIT License

Copyright (c) 2019 Nils Haentjens & Guillaume Bourdin
"""

import csv
import sys
from datetime import datetime, timedelta
from getpass import getpass
import requests
from requests.auth import HTTPBasicAuth
import re
import os
from time import sleep
from pandas import DataFrame, read_csv
import socket

__version__ = "0.6.0"
verbose = False

# Set constants
URL_L12BROWSER = 'https://oceancolor.gsfc.nasa.gov/cgi/browse.pl'
URL_DIRECT_ACCESS = 'https://oceandata.sci.gsfc.nasa.gov/'
URL_SEARCH_API = 'https://oceandata.sci.gsfc.nasa.gov/api/file_search'
URL_GET_FILE_CGI = 'https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/'
URL_CMR = 'https://cmr.earthdata.nasa.gov/search/granules.json?provider=OB_DAAC'
URL_GET_FILE_CMR = 'https://oceandata.sci.gsfc.nasa.gov/cmr/getfile/'
URL_COPERNICUS = 'https://scihub.copernicus.eu/dhus/search?q='
URL_SEARCH_CREODIAS = 'https://finder.creodias.eu/resto/api/collections/'
URL_CREODIAS_LOGIN = 'https://auth.creodias.eu/auth/realms/DIAS/protocol/openid-connect/token'
URL_CREODIAS_GET_FILE = 'https://zipper.creodias.eu/download'

# Documentation of Ocean Color Data Format Specification
#   https://oceancolor.gsfc.nasa.gov/products/
INSTRUMENT_FILE_ID = {'SeaWiFS': 'S', 'MODIS-Aqua': 'A', 'MODIS-Terra': 'T', 'OCTS': 'O', 'CZCS': 'C',
                      'MERIS': 'M', 'VIIRS': 'V', 'HICO': 'H', 'OLCI': 'Sentinel3', 'SLSTR': 'Sentinel3', 'MSI': 'Sentinel2'}
INSTRUMENT_QUERY_ID = {'SeaWiFS': 'MLAC', 'MODIS-Aqua': 'amod', 'MODIS-Terra': 'tmod', 'OCTS': 'oc', 'CZCS': 'cz',
                       'MERIS': 'RR', 'VIIRS': 'vrsn', 'HICO': 'hi', 'OLCI': 's3br@s3ar', 'MSI': 'MSI', 'SLSTR': 'SL'}
DATA_TYPE_ID = {'SeaWiFS': 'LAC', 'MODIS-Aqua': 'LAC', 'MODIS-Terra': 'LAC', 'OCTS': 'LAC', 'CZCS': '',
                'MERIS': 'RR', 'VIIRS': 'SNPP', 'HICO': 'ISS', 'OLCI_L1_ERR': 'OL_1_ERR___', 'SLSTR_L1': 'RBT',
                'OLCI_L1_EFR': 'OL_1_EFR___', 'MSI_L1C': '', 'MSI_L2A': 'S2MSI2A'}
SEARCH_CMR = {'SeaWiFS': 'SEAWIFS', 'MODIS-Aqua': 'MODISA', 'MODIS-Terra': 'MODIST',
              'OCTS': 'OCTS', 'CZCS': 'CZCS','VIIRS': 'VIIRSN'}
EXTENSION_L1A = {'MODIS-Aqua': '','MODIS-Terra': '', 'VIIRS': '.nc'}


def get_platform(dates, instrument, level):
    # Get acces plateform depending on product and date:
    # - COPERNICUS: MSI-L2A < 12 month, OLCI
    # - CREODIAS: MSI-L1C, SLSTR
    # - Common Metadata Repository (CMR): MODISA, MODIST, VIIRS, SeaWiFS, OCTS, CZCS (L2 and L3)
    # - L1/L2browser Ocean Color (requires 1s delay => slow): MODISA, MODIST, VIIRS, SeaWiFS, OCTS, CZCS (L0 and L1) / MERIS, HICO (all levels)
    # Note: if any query point dedicated to CMR is less than 60 days old, the entire query will be redirected to L1/L2browser (delay of storage on CMR)
    delta_today = datetime.today() - dates
    if instrument == 'MSI' and level == 'L2A' and all(delta_today > timedelta(days=365)):
        raise ValueError(instrument + "level " + level + " supported only for online products on Copernicus (< 1 year old)")
    elif instrument == 'OLCI' or instrument == 'MSI' and level == 'L2A':
        if instrument == 'MSI' and any(delta_today < timedelta(days=365)):
            print('Warning: query older than 12 month old will be ignored (offline products unavailable for bulk download)')
        access_platform = 'copernicus'
        password = getpass(prompt='Copernicus Password: ', stream=None)
    elif instrument == 'MSI' or instrument == 'SLSTR':
        access_platform = 'creodias'
        password = getpass(prompt='Creodias Password: ', stream=None)
    elif level == 'L0' or level == 'L1A' or level == 'GEO' or instrument == 'MERIS' or instrument == 'HICO' or any(delta_today < timedelta(days=60)):
        access_platform = 'L1L2_browser'
        password = getpass(prompt='EarthData Password: ', stream=None)
    else:
        access_platform = 'cmr'
        password = getpass(prompt='EarthData Password: ', stream=None)
    return access_platform,password


def set_query_string(access_platform, instrument, level='L2', product='OC'):
    # Set query url specific to access plateform:
    image_names = list()
    # Get parameters to build query
    if instrument in INSTRUMENT_FILE_ID.keys():
        if access_platform == 'copernicus':
            # check which spatial resolution for OLCI, if not input choose lower resolution ERR
            if 'ERR' not in level and 'EFR' not in level and instrument == 'OLCI':
                level = level + '_ERR'
                timeliness = '%20AND%20timeliness:"Non%20Time%20Critical"'
            elif instrument != 'OLCI': # delete EFR and ERR if mistakenly input for other sensors
                level = level.replace('EFR','')
                level = level.replace('ERR','')
                level = level.replace('_','')
                timeliness = ''
            else:
                timeliness = ''
            dattyp = instrument + '_' + level

            if dattyp in DATA_TYPE_ID:
                sen = 'producttype:' + DATA_TYPE_ID[dattyp]
            else:
                raise ValueError("level " + level + " not supported for " + instrument + " sensor")
            query_string = sen + '%20AND%20' + 'instrumentshortname:' + instrument + timeliness + '%20AND%20'

        elif access_platform == 'creodias':
            # OLCI possible to get from CREODIAS but easier to get from Copernicus
            sat = INSTRUMENT_FILE_ID[instrument]
            dattyp = instrument + '_' + level
            if dattyp in DATA_TYPE_ID:
                protyp = '&producttype:' + DATA_TYPE_ID[dattyp]
            else:
                raise ValueError("level " + level + " not supported for " + instrument + " sensor")

            query_string = sat + '/search.json?instrument=' + INSTRUMENT_QUERY_ID[instrument] + protyp

        elif access_platform == 'L1L2_browser':
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
                elif product in ['SST4']:
                    dnm = 'N'
                    prm = 'SST4'
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
            query_string = '?sub=' + sub + sen + '&dnm=' + dnm + '&prm=' + prm

        elif access_platform == 'cmr':
            sen = SEARCH_CMR[instrument]
            query_string = '&short_name=' + sen + '_' + level + '_' + product

        return query_string

    else:
        raise ValueError("instrument not supported:'" + instrument + "'")


def format_dtlatlon_query(poi,access_platform):
    # Add some room in the given location
    n, s = str(poi['lat'] + 1), str(poi['lat'] - 1)
    # w, e = str(poi['lon'] - 2), str(poi['lon'] + 2)
    if poi['lon'] < -178:
        w = str(poi['lon'] - 2 + 360)
    else:
        w = str(poi['lon'] - 2)
    if poi['lon'] > 178:
        e = str(poi['lon'] + 2 - 360)
    else:
        e = str(poi['lon'] + 2)

    if access_platform == 'L1L2_browser':
        day = str((poi['dt'] - datetime(1970, 1, 1)).days)
        return w,s,e,n,day
    else:
        day_st = poi['dt'] - timedelta(hours=12, minutes=0)
        day_end = poi['dt'] + timedelta(hours=12, minutes=0)
        return w,s,e,n,day_st,day_end


def get_login_key(username, password): # get login key for creodias download
    login_data = {'client_id': 'CLOUDFERRO_PUBLIC','username': username,'password': password, 'grant_type': 'password'}
    login_key = requests.post(URL_CREODIAS_LOGIN, data=login_data).json()
    try:
        return login_key['access_token']
    except KeyError:
        raise RuntimeError(f'Unable to get login key. Response was {login_key}')


def get_image_list_copernicus(pois, access_platform, username, password, query_string, instrument, level='L1'):
    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    pois['prod_entity'] = [[] for _ in range(len(pois))] # only for copernicus, to check online status & metadata

    for i, poi in pois.iterrows():
        if verbose:
            print('[' + str(i + 1) + '/' + str(len(pois)) + ']   Querying ' + str(poi['id']) + ' ' +
                  instrument + ' ' + level + ' on Copernicus' + '    ' + str(poi['dt']) + '    ' + "%.5f" % poi['lat'] + '  ' + "%.5f" % poi['lon'])
        # get polygon around poi and date
        w,s,e,n,day_st,day_end = format_dtlatlon_query(poi, access_platform)
        # Build Query
        query = URL_COPERNICUS + query_string + 'beginposition:[' + day_st.strftime("%Y-%m-%dT%H:%M:%S.000Z") + '%20TO%20' + \
            day_end.strftime("%Y-%m-%dT%H:%M:%S.000Z") + ']%20AND%20' + 'footprint:"Intersects(POLYGON((' + w + '%20' + s + ',' + e + '%20' + s + \
            ',' + e + '%20' + n + ',' + w + '%20' + n + ',' + w + '%20' + s + ')))"&rows=100'
        r = requests.get(query, auth=HTTPBasicAuth(username, password))

        # r = s.get(url_dwld[i], auth=(username, password), stream=True, timeout=30)
        if i == 0 and 'Full authentication is required to access this resource' in r.text:
            raise Error('Unable to login to Copernicus, check username/password')
        # extract image name from response
        imlistraw = re.findall(r'<entry>\n<title>(.*?)</title>\n<', r.text)
        # extract url from response
        url_list = re.findall(r'\n<link href="(.*?)"/>\n<link rel="alternative"', r.text)
        # extract product meta data from response to check online status
        prod_meta = re.findall(r'\n<link rel="alternative" href="(.*?)"/>\n<link rel="icon"', r.text)
        # populate lists with image name and url
        pois.at[i, 'image_names'] = [s + '.zip' for s in imlistraw]
        pois.at[i, 'url'] = url_list
        pois.at[i, 'prod_entity'] = prod_meta

    return pois

def get_image_list_creodias(pois, access_platform, username, password, query_string, instrument, level='L1C'):
    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    pois['prod_entity'] = [[] for _ in range(len(pois))] # only for copernicus, to check online status & metadata

    for i, poi in pois.iterrows():
        if verbose:
            print('[' + str(i + 1) + '/' + str(len(pois)) + ']   Querying ' + str(poi['id']) + ' ' +
                  instrument + ' ' + level + ' on Creodias' + '    ' + str(poi['dt']) + '    ' + "%.5f" % poi['lat'] + '  ' + "%.5f" % poi['lon'])
        # get polygon around poi and date
        w,s,e,n,day_st,day_end = format_dtlatlon_query(poi, access_platform)
        # Build Query
        query = URL_SEARCH_CREODIAS + query_string + '&startDate=' + day_st.strftime("%Y-%m-%d") + \
            '&completionDate=' + day_end.strftime("%Y-%m-%d") + '&box=' + w + ',' + s + ',' + e + ',' + n
        r = requests.get(query)
        # extract image name from response
        imlistraw = re.findall(r'"parentIdentifier":null,"title":"(.*?)","description"', r.text)
        # extract url from response
        fid_list = re.findall(r'"download":{"url":"https:\\/\\/zipper.creodias.eu\\/download\\/(.*?)","mimeType"', r.text)

        # populate lists with image name and url
        pois.at[i, 'image_names'] = [sub.replace('.SAFE', '') + '.zip' for sub in imlistraw]
        pois.at[i, 'url'] = [URL_CREODIAS_GET_FILE + '/' + s + '?token=' for s in fid_list]

    return pois


def get_image_list_l12browser(pois, access_platform, query_string, instrument, level='L2', product='OC', query_delay=1):
    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    pois['prod_entity'] = [[] for _ in range(len(pois))] # only for copernicus, to check online status & metadata

    for i, poi in pois.iterrows():
        if verbose:
            print('[' + str(i + 1) + '/' + str(len(pois)) + ']   Querying ' + str(poi['id']) + ' ' +
                  instrument + ' ' + level + ' on L1L2_browser' + '    ' + str(poi['dt']) + '    ' + "%.5f" % poi['lat'] + '  ' + "%.5f" % poi['lon'])
        # get polygon around poi and date
        w,s,e,n,day = format_dtlatlon_query(poi, access_platform)
        # Build Query
        query = URL_L12BROWSER + query_string + '&per=DAY&day=' + day + '&n=' + n + '&s=' + s + '&w=' + w + '&e=' + e
        r = requests.get(query)
        # extract image name from response
        if 'href="https://oceandata.sci.gsfc.nasa.gov/ob/getfile/' in r.text: # if one image
            imlistraw = re.findall(r'href="https://oceandata.sci.gsfc.nasa.gov/ob/getfile/(.*?)">', r.text)
            imlistraw = [ x for x in imlistraw if level in x ]
        else: # if multiple images
            imlistraw = re.findall(r'title="(.*?)"\nwidth="70"', r.text)
            if instrument == 'MODIS-Aqua' or instrument == 'MODIS-Terra' and level == 'L1A':
                # add missing extension when multiple reuslts
                imlistraw = [s + '.bz2' for s in imlistraw]
                # remove duplicates
                imlistraw = list(dict.fromkeys(imlistraw))

        # append VIIRS GEO file names at the end of the list
        if instrument == 'VIIRS' and level == 'L1A':
            imlistraw = imlistraw + [sub.replace('L1A', 'GEO-M') for sub in imlistraw]

        # Delay next query (might get kicked by server otherwise)
        sleep(query_delay)

        # populate lists with image name and url
        pois.at[i, 'image_names'] = imlistraw

        # populate url list
        pois.at[i, 'url'] = [URL_GET_FILE_CGI + s for s in pois.at[i, 'image_names']]

    return pois


def get_image_list_cmr(pois, access_platform, query_string, instrument, level='L2', product='OC'):
    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    pois['prod_entity'] = [[] for _ in range(len(pois))] # only for copernicus, to check online status & metadata

    for i, poi in pois.iterrows():
        if verbose:
            print('[' + str(i + 1) + '/' + str(len(pois)) + ']   Querying ' + str(poi['id']) + ' ' +
                  instrument + ' ' + level + ' on CMR' + '    ' + str(poi['dt']) + '    ' + "%.5f" % poi['lat'] + '  ' + "%.5f" % poi['lon'])
        # get polygon around poi and date
        w,s,e,n,day_st,day_end = format_dtlatlon_query(poi, access_platform)
        # Build Query
        query = URL_CMR + query_string + '&bounding_box=' + w + ',' +  s + ',' + e + ',' + n + \
                '&temporal=' + day_st.strftime("%Y-%m-%dT%H:%M:%SZ,") + day_end.strftime("%Y-%m-%dT%H:%M:%SZ") + '&page_size=2000&page_num=1'
        r = requests.get(query)
        # extract image name from response
        imlistraw = re.findall(r'https://oceandata.sci.gsfc.nasa.gov/cmr/getfile/(.*?)"},', r.text)
        # Reformat VIIRS image name
        if instrument == 'VIIRS' and product == 'SST':
            imlistraw = [ x for x in imlistraw if "SNPP_VIIRS." in x ]

        # populate lists with image name and url
        pois.at[i, 'image_names'] = imlistraw
        pois.at[i, 'url'] = [URL_GET_FILE_CMR + s for s in imlistraw]

    return pois


def login_download(image_names, url_dwld, instrument, access_platform, username, password):
    # Login to Earth Data and Download image
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',}
    if url_dwld is None and image_names is None:
        if verbose:
            print('No image to download.')
        return None
    if access_platform == 'creodias':
        # get login key to include it into url
        login_key = get_login_key(username, password)
    for i in range(len(url_dwld)):
        if os.path.isfile(image_names[i]):
            if verbose:
                print('Skip ' + image_names[i])
        else:
            MAX_RETRIES = 3
            WAIT_SECONDS = 30
            for j in range(MAX_RETRIES):
                try:
                    # modify header to hide requests query and mimic web browser
                    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',}
                    # Open session
                    with requests.Session() as s:
                        # Login and download by chunk
                        if access_platform == 'copernicus':
                            r = s.get(url_dwld[i], auth=(username, password), stream=True, timeout=30, headers=headers)
                            if r.status_code != 200:
                                if 'offline products retrieval quota exceeded' in r.text:
                                    print('Unable to download from https://scihub.copernicus.eu/\n'
                                      '\t- User offline products retrieval quota exceeded (1 fetch max)')
                                    break
                                else:
                                    print('Unable to download from https://scihub.copernicus.eu/\n'
                                      '\t- Check login/username\n'
                                      '\t- Invalid image name?')
                                    return None
                        elif access_platform == 'creodias':
                            r = s.get(url_dwld[i] + login_key, stream=True, timeout=30, headers=headers)
                            if r.status_code != 200:
                                if r.text == 'Expired signature!':
                                    print('Login expired, reconnection ...')
                                    # get login key to include it into url
                                    login_key = get_login_key(username, password)
                                    r = s.get(url_dwld[i] + login_key, stream=True, timeout=30, headers=headers)
                                else:
                                    print('Unable to download from https://auth.creodias.eu/\n'
                                      '\t- Check login/username\n'
                                      '\t- Invalid image name?')
                                    return None
                        else:
                            s.auth = (username, password)
                            r1 = s.request('get', url_dwld[i])
                            r = s.get(r1.url, auth=(username, password), stream=True, timeout=30, headers=headers)
                        if r.ok:
                            if verbose:
                                print('Downloading ' + image_names[i])
                            handle = open(image_names[i], "wb")
                            for chunk in r.iter_content(chunk_size=512):
                                if chunk:
                                    handle.write(chunk)
                            handle.close()
                            break
                        else:
                            print('Unable to download from EarthData.\n'
                              '\t- Did you accept the End User License Agreement for this dataset ?\n'
                              '\t- Check login/username\n'
                              '\t- Invalid image name?')
                            return None
                except requests.exceptions.ConnectionError:
                    print('Build https connection failed: download failed, reconnection ...')
                    handle.close()
                except requests.exceptions.ProxyError:
                    print('Proxy error: download failed, reconnection ...')
                    handle.close()
                except requests.exceptions.SSLError:
                    print('SSL error: download failed, reconnection ...')
                    handle.close()
                except requests.exceptions.Timeout:
                    print('Request timed out: download failed, reconnection ...')
                    handle.close()
                except requests.exceptions.ReadTimeout:
                    print('Read timed out: download failed, reconnection ...')
                    handle.close()
                except requests.exceptions.ConnectTimeout:
                    print('Connection timed out: download failed, reconnection ...')
                    handle.close()
                except requests.exceptions.RequestException:
                    print('Unknown error: download failed, reconnection ...')
                    handle.close()
                except requests.exceptions.InvalidURL:
                    print('URL not valid: download failed, reconnection ...')
                    handle.close()
                except requests.exceptions.ChunkedEncodingError:
                    print('The server declared chunked encoding but sent an invalid chunk: download failed, reconnection ...')
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


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser(usage="Usage: getOC.py [options] [filename]", version="getOC " + __version__)
    parser.add_option("-i", "--instrument", action="store", dest="instrument",
                      help="specify instrument, available options are: VIIRS, MODIS-Aqua, MODIS-Terra, OCTS, CZCS, MERIS, HICO, "
                      "OLCI (L1 only), SLSTR (L1 only), MSI (L1C and L2A < 12 month) and SeaWiFS (L3 only)")
    parser.add_option("-l", "--level", action="store", dest="level", default='L2',
                      help="specify processing level, available options are: GEO, L1A, L1C (MSI only), L2A (MSI only), L2, "
                      "L3BIN, and L3SMI, append '_ERR' to level for lower OLCI resoltion or '_EFR' for full resoltuion")
    # Level 2 specific option
    parser.add_option("-p", "--product", action="store", dest="product", default='OC',
                      help="specify product identifier (only for L2), available options are: OC, SST, and IOP, "
                      "not available for Copernicus (OLCI, SLSTR and MSI) queries")
    parser.add_option("-d", "--delay", action="store", dest="query_delay", type='float', default=1,
                      help="Delay between queries only needed to query L1L2_browser")
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
                      help="specify username to login to Copernicus (OLCI / SLSTR), Creodias (MSI) or EarthData (any other plateform")
    # Other options
    parser.add_option("-w", "--write-image-links", action="store_true", dest="write_image_links", default=False,
                      help="Write query results image names and corresponding url into csv file.")
    parser.add_option("-r", "--read-image-list", action="store_true", dest="read_image_list", default=False,
                      help="Read previous query from csv file")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True)
    (options, args) = parser.parse_args()


    verbose = options.verbose
    if options.instrument is None:
        print(parser.usage)
        print('getOC.py: error: option -i, --instrument is required')
        sys.exit(-1)
    if 'L3' not in options.level and options.username is None:
        print(parser.usage)
        print('getOC.py: error: option -u, --username is required')
        sys.exit(-1)

    if len(args) < 1 and options.level not in ['L3BIN', 'L3SMI']:
        print(parser.usage)
        print('getOC.py: error: argument filename is required for Level GEO, L1A, or L2')
        sys.exit(-1)
    elif len(args) > 2:
        print(parser.usage)
        print('getOC.py: error: too many arguments')
        sys.exit(-1)


    image_names = list()
    # Get list of images to download
    if options.read_image_list:
        if os.path.isfile(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                                  options.level + '_' + options.product + '.csv'):
            pois = read_csv(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                                      options.level + '_' + options.product + '.csv',
                                      names=['id', 'dt', 'lat', 'lon', 'image_names', 'url', 'prod_entity'], parse_dates=[1])
            pois.dropna(subset=['image_names'], axis=0, inplace= True)
            points_of_interest = pois.copy()

            access_platform,password = get_platform(points_of_interest['dt'], options.instrument, options.level)

            # Parse image_names and url
            image_names = list()
            url_dwld = list()
            for index, record in pois.iterrows():
                # Convert 'stringified' list to list
                imli = record['image_names'].split(';')
                urli = record['url'].split(';')
                for im in range(len(imli)):
                    image_names.append(imli[im])
                    url_dwld.append(urli[im])
        else:
            if verbose:
                print('IOError: [Errno 2] File ' + os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                                  options.level + '_' + options.product + '.csv' + ' does not exist, select option -w (write) instead of -r (read)')
            sys.exit(0)
    else:
        # Parse csv file containing points of interest
        points_of_interest = read_csv(args[0], names=['id', 'dt', 'lat', 'lon'], parse_dates=[1])

        access_platform,password = get_platform(points_of_interest['dt'], options.instrument, options.level)
        query_string = set_query_string(access_platform, options.instrument, options.level, options.product)

        if access_platform == 'copernicus':
            pois = get_image_list_copernicus(points_of_interest, access_platform, options.username, password,
                            query_string, options.instrument, options.level)
        elif access_platform == 'creodias':
            pois = get_image_list_creodias(points_of_interest, access_platform, options.username, password,
                            query_string, options.instrument, options.level)
        elif access_platform == 'L1L2_browser':
            pois = get_image_list_l12browser(points_of_interest, access_platform, query_string, options.instrument,
                            options.level, options.product, options.query_delay)
        elif access_platform == 'cmr':
            pois = get_image_list_cmr(points_of_interest, access_platform, query_string, options.instrument,
                            options.level, options.product)

        points_of_interest = pois.copy()
        # parse image_names
        image_names = list()
        url_dwld = list()
        prod_meta = list()
        for _, pois in pois.iterrows():
            image_names.extend(pois['image_names'])
            url_dwld.extend(pois['url'])
            prod_meta.extend(pois['prod_entity'])

    # Write image names
    if options.write_image_links:
        # Reformat image names & url
        for i, poi in points_of_interest.iterrows():
            points_of_interest.at[i, 'image_names'] = ';'.join(poi['image_names'])
            points_of_interest.at[i, 'url'] = ';'.join(poi['url'])
            points_of_interest.at[i, 'prod_entity'] = ';'.join(poi['prod_entity'])
        points_of_interest.to_csv(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                                  options.level + '_' + options.product + '.csv',
                                  date_format='%Y/%m/%d %H:%M:%S', header=False, index=False, float_format='%.5f')

    # Download images from url list
    login_download(image_names, url_dwld, options.instrument, access_platform, options.username, password)