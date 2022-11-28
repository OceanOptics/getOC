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
import numpy as np
import socket
import math
# import timeout_decorator
# from signal import signal
# from multiprocessing import Process, Event, Lock

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
# https://oceancolor.gsfc.nasa.gov/products/
INSTRUMENT_FILE_ID = {'SeaWiFS': 'S', 'MODIS-Aqua': 'A', 'MODIS-Terra': 'T', 'OCTS': 'O', 'CZCS': 'C', 'GOCI': 'G',
                      'MERIS': 'M', 'VIIRSN': 'V', 'VIIRSJ1': 'V', 'HICO': 'H', 'OLCI': 'Sentinel3',
                      'SLSTR': 'Sentinel3', 'MSI': 'Sentinel2'}
INSTRUMENT_QUERY_ID = {'SeaWiFS': 'MLAC', 'MODIS-Aqua': 'amod', 'MODIS-Terra': 'tmod', 'OCTS': 'oc', 'CZCS': 'cz',
                       'GOCI': 'goci', 'MERIS': 'RR', 'VIIRSN': 'vrsn', 'VIIRSJ1': 'vrj1', 'HICO': 'hi', 'OLCI': 'OL',
                       'MSI': 'MSI', 'SLSTR': 'SL'}
DATA_TYPE_ID = {'SeaWiFS': 'LAC', 'MODIS-Aqua': 'LAC', 'MODIS-Terra': 'LAC', 'OCTS': 'LAC', 'CZCS': '',
                'MERIS': 'RR', 'VIIRSN': 'SNPP', 'VIIRSJ1': 'JPSS1','HICO': 'ISS', 'OLCI_L1_ERR': 'ERR',
                'OLCI_L1_EFR': 'EFR', 'SLSTR_L1_RBT': 'RBT', 'OLCI_L2_WRR': 'WRR', 'OLCI_L2_WFR': 'WFR',
                'SLSTR_L2_WCT': 'WCT', 'SLSTR_L2_WST': 'WST', 'MSI_L1C': 'L1C', 'MSI_L2A': 'L2A'}  # copernicus 'MSI_L2A': 'S2MSI2A'
LEVEL_CREODIAS = {'L1': 'LEVEL1', 'L2': 'LEVEL2', 'L1C': 'LEVEL1C', 'L2A': 'LEVEL2A'}
SEARCH_CMR = {'SeaWiFS': 'SEAWIFS', 'MODIS-Aqua': 'MODISA', 'MODIS-Terra': 'MODIST',
              'OCTS': 'OCTS', 'CZCS': 'CZCS', 'VIIRSN': 'VIIRSN', 'VIIRSJ1': 'VIIRSJ1', 'GOCI': 'GOCI'}
EXTENSION_L1A = {'MODIS-Aqua': '','MODIS-Terra': '', 'VIIRSN': '.nc', 'VIIRSJ1': '.nc'}


def get_platform(dates, instrument, level):
    # Get acces plateform depending on product and date:
    # - COPERNICUS: MSI-L2A < 12 month, OLCI # DEPRECATED
    # - CREODIAS: MSI, OLCI, SLSTR (L1 and L2)
    # - Common Metadata Repository (CMR): MODISA, MODIST, VIIRSJ1, VIIRSN, SeaWiFS, OCTS, CZCS (L2 and L3)
    # - L1/L2browser Ocean Color (requires 1s delay => slow): MODISA, MODIST, SeaWiFS, OCTS, CZCS (L0 and L1) / MERIS, HICO (all levels)
    # Note: if any query point dedicated to CMR is less than 2 days old, the entire query will be redirected to L1/L2browser (delay of storage on CMR)

    delta_today = datetime.today() - dates
    # if instrument == 'MSI' and level == 'L2A' and all(delta_today > timedelta(days=365)): # DEPRECATED
    #     raise ValueError(instrument + "level " + level + " supported only for online products on Copernicus (< 1 year old)") # DEPRECATED
    # elif instrument == 'MSI' and level == 'L2A': #instrument == 'OLCI' or  # DEPRECATED
    #     if instrument == 'MSI' and any(delta_today < timedelta(days=365)): # DEPRECATED
    #         print('Warning: query older than 12 month old will be ignored (offline products unavailable for bulk download)') # DEPRECATED
    #     access_platform = 'copernicus' # DEPRECATED
    #     password = getpass(prompt='Copernicus Password: ', stream=None) # DEPRECATED
    if instrument == 'MSI' or instrument == 'SLSTR' or instrument == 'OLCI':
        access_platf = 'creodias'
        pwd = getpass(prompt='Creodias Password: ', stream=None)
    elif 'VIIRS' not in instrument and (level == 'L0' or 'L1' in level or level == 'GEO') or instrument == 'MERIS' or \
            instrument == 'HICO' or any(delta_today < timedelta(hours=48)):
        access_platf = 'L1L2_browser'
        pwd = getpass(prompt='EarthData Password: ', stream=None)
    else:
        access_platf = 'cmr'
        pwd = getpass(prompt='EarthData Password: ', stream=None)
    return access_platf, pwd


def set_query_string(access_platform, instrument, level='L2', product='OC'):
    # Set query url specific to access plateform:
    # Get parameters to build query
    if instrument in INSTRUMENT_FILE_ID.keys():
        if access_platform == 'copernicus':  # DEPRECATED
            # check which spatial resolution for OLCI, if not input choose lower resolution ERR
            if 'ERR' not in level and 'EFR' not in level and instrument == 'OLCI':
                level = level + '_EFR'
                timeliness = '%20AND%20timeliness:"Non%20Time%20Critical"'
            elif instrument != 'OLCI': # delete EFR and ERR if mistakenly input for other sensors
                level = level.replace('EFR', '')
                level = level.replace('ERR', '')
                level = level.replace('_', '')
                timeliness = ''
            else:
                timeliness = ''
            dattyp = instrument + '_' + level
            if dattyp in DATA_TYPE_ID:
                sen = 'producttype:' + DATA_TYPE_ID[dattyp]
            else:
                raise ValueError("level " + level + " not supported for " + instrument + " sensor")
            query_str = sen + '%20AND%20' + 'instrumentshortname:' + instrument + timeliness + '%20AND%20'
        elif access_platform == 'creodias':
            # https://finder.creodias.eu/resto/api2/collections/Sentinel2/search.json?instrument=MSI&productType=L2A&processingLevel=LEVEL2A
            # check which spatial resolution for SLSTR and OLCI, if not input choose default:
            if 'L1' in level and 'ERR' not in level and 'EFR' not in level and instrument == 'OLCI':
                level = level + '_EFR'
            if 'L1' in level and 'RBT' not in level and instrument == 'SLSTR':
                level = level + '_RBT'
            if 'L2' in level and 'WFR' not in level and 'WRR' not in level and instrument == 'OLCI':
                level = level + '_WFR'
            if 'L2' in level and 'WST' not in level and 'WCT' not in level and instrument == 'SLSTR':
                level = level + '_WST'
            sat = INSTRUMENT_FILE_ID[instrument]
            dattyp = instrument + '_' + level
            if dattyp not in DATA_TYPE_ID:
                raise ValueError("level " + level + " not supported for " + instrument + " sensor")
            else:
                query_str = sat + '/search.json?instrument=' + INSTRUMENT_QUERY_ID[instrument] + '&productType=' + \
                            DATA_TYPE_ID[dattyp] + '&processingLevel=' + LEVEL_CREODIAS[level.split('_')[0]]
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
            query_str = '?sub=' + sub + sen + '&dnm=' + dnm + '&prm=' + prm
        elif access_platform == 'cmr':
            sen = SEARCH_CMR[instrument]
            if 'L1' in level:
                query_str = '&short_name=' + sen + '_' + level[0:2]
            else:
                query_str = '&short_name=' + sen + '_' + level + '_' + product
        else:
            print('Error: plateform not recognized')
            sys.exit(-1)
        return query_str
    else:
        raise ValueError("instrument not supported: " + instrument)


def format_dtlatlon_query(poi, access_platform):
    # Add some room using bounding box option (or default = 60 nautical miles) around the given location, and wrap longitude into [-180:180]
    if poi['lat'] + options.bounding_box_sz / 60 > 90:
        n = str(90)
    else:
        n = str(poi['lat'] + options.bounding_box_sz / 60)
    if poi['lat'] - options.bounding_box_sz / 60 < -90:
        s = str(-90)
    else:
        s = str(poi['lat'] - options.bounding_box_sz / 60)
    lon_box = options.bounding_box_sz / 60 / (math.cos(poi['lat'] * math.pi / 180))
    if poi['lon'] - lon_box < -180:
        w = str(poi['lon'] - lon_box + 360)
    else:
        w = str(poi['lon'] - lon_box)
    if poi['lon'] + lon_box > 180:
        e = str(poi['lon'] + lon_box - 360)
    else:
        e = str(poi['lon'] + lon_box)
    if access_platform == 'L1L2_browser':
        day = str((poi['dt'] - datetime(1970, 1, 1)).days)
        return w, s, e, n, day
    else:
        day_st = poi['dt'] - timedelta(hours=12, minutes=0)
        day_end = poi['dt'] + timedelta(hours=12, minutes=0)
        return w, s, e, n, day_st, day_end


def get_login_key(username, password):  # get login key for creodias download
    login_data = {'client_id': 'CLOUDFERRO_PUBLIC','username': username,'password': password, 'grant_type': 'password'}
    login_key = requests.post(URL_CREODIAS_LOGIN, data=login_data).json()
    try:
        return login_key['access_token']
    except KeyError:
        raise RuntimeError('Unable to get login key. Response was ' + {login_key})


def get_image_list_copernicus(pois, access_platform, username, password, query_string, instrument, level='L1'):  # DEPRECATED
    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    pois['prod_entity'] = [[] for _ in range(len(pois))]  # only for copernicus, to check online status & metadata
    for i, poi in pois.iterrows():
        if verbose:
            print('[' + str(i + 1) + '/' + str(len(pois)) + ']   Querying ' + str(poi['id']) + ' ' +
                  instrument + ' ' + level + ' on Copernicus' + '    ' + str(poi['dt']) + '    ' +
                  "%.5f" % poi['lat'] + '  ' + "%.5f" % poi['lon'])
        # get polygon around poi and date
        w, s, e, n, day_st, day_end = format_dtlatlon_query(poi, access_platform)
        # Build Query
        query = URL_COPERNICUS + query_string + 'beginposition:[' + day_st.strftime("%Y-%m-%dT%H:%M:%S.000Z") + \
                '%20TO%20' + day_end.strftime("%Y-%m-%dT%H:%M:%S.000Z") + ']%20AND%20' + \
                'footprint:"Intersects(POLYGON((' + w + '%20' + s + ',' + e + '%20' + s + ',' + e + '%20' + n + ',' \
                + w + '%20' + n + ',' + w + '%20' + s + ')))"&rows=100'
        r = requests.get(query, auth=HTTPBasicAuth(username, password))
        # r = s.get(url_dwld[i], auth=(username, password), stream=True, timeout=30)
        if i == 0 and 'Full authentication is required to access this resource' in r.text:
            print('Error: Unable to login to Copernicus, check username/password')
            return -1
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


def sel_most_recent_olci(imlistraw, fid_list):
    sel_s3 = find_most_recent_olci(imlistraw)
    sel_fid = []
    for i in range(len(imlistraw)):
        if imlistraw[i] in sel_s3:
            sel_fid.append(fid_list[i])
    return sel_s3, sel_fid


def find_most_recent_olci(imlistraw):
    ref = imlistraw
    ref = [x[0:29] for x in ref]
    x = np.array(ref)
    uref = np.unique(x)
    todelete = []
    for singlref in uref:
        str_match = [s for s in imlistraw if singlref in s]
        NR_match = [s for s in str_match if '_NR_' in s]
        NT_match = [s for s in str_match if '_NT_' in s]
        O_match = [s for s in str_match if '_O_' in s]
        R_match = [s for s in str_match if '_R_' in s]
        LN1_match = [s for s in str_match if '_LN1_' in s]
        # LN2_match = [s for s in str_match if '_LN2_' in s]
        MAR_match = [s for s in str_match if '_MAR_' in s]
        if len(str_match) > 1:
            # select reprocessed over operational
            if len(O_match) > 0 and len(R_match) > 0:
                for O_img in O_match:
                    todelete.append(O_img)
            # select no time limit over near real time
            if len(NR_match) > 0 and len(NT_match) > 0:
                for NR_img in NR_match:
                    todelete.append(NR_img)
            # select marine processing over land old processing code
            if len(MAR_match) > 0 and len(LN1_match) > 0:
                for LN1_img in LN1_match:
                    todelete.append(LN1_img)
            for todel in todelete:
                imlistraw = list(filter(todel.__ne__, imlistraw))
    return imlistraw


def get_image_list_creodias(pois, access_platform, query_string, instrument, level='L1C'):  # username, password,
    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    pois['prod_entity'] = [[] for _ in range(len(pois))]  # only for copernicus, to check online status & metadata
    for i, poi in pois.iterrows():
        if verbose:
            print('[%i/%i]   Querying %s %s %s on Creodias    %s    %.5f  %.5f' %
                  (i + 1, len(pois), poi['id'], instrument, level, poi['dt'], poi['lat'], poi['lon']))
        # get polygon around poi and date
        w, s, e, n, day_st, day_end = format_dtlatlon_query(poi, access_platform)
        # Build Query
        query = '%s%s&startDate=%s&completionDate=%s&box=%s,%s,%s,%s' % \
                (URL_SEARCH_CREODIAS, query_string, day_st.strftime("%Y-%m-%d"),
                 day_end.strftime("%Y-%m-%d"), w, s, e, n)
        r = requests.get(query)
        # extract image name from response
        imlistraw = re.findall(r'"parentIdentifier":null,"title":"(.*?)","description"', r.text)
        # extract url from response
        fid_list = re.findall(r'"download":{"url":"https:\\/\\/zipper.creodias.eu\\/download\\/(.*?)","mimeType"',
                              r.text)
        sel_s3, sel_fid = sel_most_recent_olci(imlistraw, fid_list)
        # populate lists with image name and url
        # pois.at[i, 'image_names'] = [sub.replace('.SAFE', '') + '.zip' for sub in imlistraw]
        pois.at[i, 'image_names'] = [s + '.zip' for s in sel_s3]
        # pois.at[i, 'image_names'] = imlistraw
        pois.at[i, 'url'] = ['%s/%s?token=' % (URL_CREODIAS_GET_FILE, s) for s in sel_fid]
    return pois


def get_image_list_l12browser(pois, access_platform, query_string, instrument, level='L2', product='OC', query_delay=1):
    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    pois['prod_entity'] = [[] for _ in range(len(pois))] # only for copernicus, to check online status & metadata
    for i, poi in pois.iterrows():
        if verbose:
            print('[%i/%i]   Querying %s %s %s %s on L1L2_browser    %s    %.5f  %.5f' %
                  (i+1, len(pois), poi['id'], instrument, level, product, poi['dt'], poi['lat'], poi['lon']))
        # get polygon around poi and date
        w, s, e, n, day = format_dtlatlon_query(poi, access_platform)
        # Build Query
        query = '%s%s&per=DAY&day=%s&n=%s&s=%s&w=%s&e=%s' % (URL_L12BROWSER, query_string, day, n, s, w, e)
        r = requests.get(query)
        # extract image name from response
        if 'href="https://oceandata.sci.gsfc.nasa.gov/ob/getfile/' in r.text: # if one image
            imlistraw = re.findall(r'href="https://oceandata.sci.gsfc.nasa.gov/ob/getfile/(.*?)">', r.text)
            imlistraw = [x for x in imlistraw if level in x]
        else:  # if multiple images
            imlistraw = re.findall(r'title="(.*?)"\nwidth="70"', r.text)
            if level == 'L1A':
                if instrument == 'MODIS-Aqua' or instrument == 'MODIS-Terra':
                    # add missing extension when multiple results
                    imlistraw = [s + '.bz2' for s in imlistraw]
                    # remove duplicates
                    imlistraw = list(dict.fromkeys(imlistraw))
        # append VIIRS GEO file names at the end of the list
        if 'VIIRS' in instrument and level == 'L1A':
            imlistraw = imlistraw + [sub.replace('L1A', 'GEO') for sub in imlistraw]
            if len(imlistraw) > 0:
                imlistraw = [sub.replace(';;', ';') for sub in imlistraw]
                if imlistraw[-1] == ';':
                    imlistraw = imlistraw[0:-1]
        # Delay next query (might get kicked by server otherwise)
        sleep(query_delay)
        # populate lists with image name and url
        pois.at[i, 'image_names'] = imlistraw
        # populate url list
        pois.at[i, 'url'] = ['%s%s' % (URL_GET_FILE_CGI, s) for s in pois.at[i, 'image_names']]
    return pois


def get_image_list_cmr(pois, access_platform, query_string, instrument, level='L2', product='OC'):
    # https://cmr.earthdata.nasa.gov/search/granules.json?provider=OB_DAAC&short_name=MODISA_L2_OC&temporal=2016-08-21T00:00:01Z,2016-08-22T00:00:01Z&page_size=2000&page_num=1
    # https://cmr.earthdata.nasa.gov/search/granules.json?provider=OB_DAAC&short_name=VIIRSJ1_L1&temporal=2020-08-16T00:00:01Z,2020-08-17T00:00:01Z&page_size=2000&page_num=1
    # https://cmr.earthdata.nasa.gov/search/granules.json?provider=OB_DAAC&short_name=VIIRSJ1_L1_GEO&temporal=2020-08-16T00:00:01Z,2020-08-17T00:00:01Z&page_size=2000&page_num=1
    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    pois['prod_entity'] = [[] for _ in range(len(pois))]  # only for copernicus, to check online status & metadata
    for i, poi in pois.iterrows():
        if verbose:
            print('[%i/%i]   Querying %s %s %s %s on CMR    %s    %.5f  %.5f' %
                  (i+1, len(pois), poi['id'], instrument, level, product, poi['dt'], poi['lat'], poi['lon']))
        # get polygon around poi and date
        w, s, e, n, day_st, day_end = format_dtlatlon_query(poi, access_platform)
        # Build Query
        query = '%s%s&bounding_box=%s,%s,%s,%s&temporal=%s,%s&page_size=2000&page_num=1' % \
                (URL_CMR, query_string, w, s, e, n, day_st.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 day_end.strftime("%Y-%m-%dT%H:%M:%SZ"))
        r = requests.get(query)
        # extract image name from response
        imlistraw = re.findall(r'https://oceandata.sci.gsfc.nasa.gov/cmr/getfile/(.*?)"},', r.text)
        # run second query for GEO files if VIIRS and L1A
        if 'VIIRS' in instrument and level == 'L1A' or level == 'L1':
            query = '%s%s_NRT&bounding_box=%s,%s,%s,%s&temporal=%s,%s&page_size=2000&page_num=1' % \
                    (URL_CMR, query_string.replace('_L1', '_L1_GEO'), w, s, e, n, day_st.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     day_end.strftime("%Y-%m-%dT%H:%M:%SZ"))
            r = requests.get(query)
            # extract image name from response
            imlistraw = imlistraw + re.findall(r'https://oceandata.sci.gsfc.nasa.gov/cmr/getfile/(.*?)"},', r.text)
        # run second query for NRT files if date_st or date_end more recent than 60 days
        if datetime.utcnow() - day_st < timedelta(days=60) or datetime.utcnow() - day_end < timedelta(days=60):
            query = '%s%s_NRT&bounding_box=%s,%s,%s,%s&temporal=%s,%s&page_size=2000&page_num=1' % \
                    (URL_CMR, query_string, w, s, e, n, day_st.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     day_end.strftime("%Y-%m-%dT%H:%M:%SZ"))
            r = requests.get(query)
            # extract image name from response
            imlistraw = imlistraw + re.findall(r'https://oceandata.sci.gsfc.nasa.gov/cmr/getfile/(.*?)"},', r.text)
        if level == 'L3m' or product == 'L3b':
            imlistraw = [x for x in imlistraw if options.sresol in x and options.binning_period in x]
        # Keep only good image name image name
        if instrument == 'VIIRSN':
            imlistraw = [x for x in imlistraw if "SNPP_VIIRS." in x]
        if instrument == 'VIIRSJ1':
            imlistraw = [x for x in imlistraw if "JPSS1_VIIRS." in x]
        if 'MODIS' in instrument:
            imlistraw = [x for x in imlistraw if "MODIS" in x]
        # populate lists with image name and url
        pois.at[i, 'image_names'] = imlistraw
        pois.at[i, 'url'] = ['%s%s' % (URL_GET_FILE_CMR, s) for s in imlistraw]
    return pois


def request_platform(s, image_names, url_dwld, access_platform, username, password, login_key):
    if access_platform == 'copernicus':  # DEPRECATED
        login_key = None
        headers = {'Range':'bytes=' + str(os.stat(image_names).st_size) + '-'}
        r = s.get(url_dwld, auth=(username, password), stream=True, timeout=900, headers=headers)
        if r.status_code != 200 and r.status_code != 206:
            if 'offline products retrieval quota exceeded' in r.text:
                print('Unable to download from https://scihub.copernicus.eu/\n'
                      '\t- User offline products retrieval quota exceeded (1 fetch max)')
                return None
            else:
                print(r.status_code)
                print(r.text)
                print('Unable to download from https://scihub.copernicus.eu/\n'
                      '\t- Check login/username\n'
                      '\t- Invalid image name?')
        return r, login_key
    elif access_platform == 'creodias':
        headers = {'Range': 'bytes=' + str(os.stat(image_names).st_size) + '-'}
        r = s.get(url_dwld + login_key, stream=True, timeout=900, headers=headers)
        if r.status_code != 200 and r.status_code != 206:
            if r.text == 'Expired signature!':
                print('Login expired, reconnection ...')
                # get login key to include it into url
                login_key = get_login_key(username, password)
                r = s.get(url_dwld + login_key, stream=True, timeout=900, headers=headers)
            else:
                print(r.status_code)
                print(r.text)
                print('Unable to download from https://auth.creodias.eu/\n'
                      '\t- Check login/username\n'
                      '\t- Invalid image name?')
        return r, login_key
    else:
        # modify header to hide requests query and mimic web browser
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, '
                                 'like Gecko) Chrome/68.0.3440.106 Safari/537.36',}
        login_key = None
        s.auth = (username, password)
        # headers = {'Range':'bytes=' + str(os.stat(image_names).st_size) + '-'}
        r1 = s.request('get', url_dwld)
        r = s.get(r1.url, auth=(username, password), stream=True, timeout=900, headers=headers)
        return r, login_key


def login_download(img_names, urls, instrument, access_platform, username, password):
    # Login to Earth Data and Download image
    if urls is None and img_names is None:
        if verbose:
            print('No image to download.')
        return None
    # remove duplicate from image and url lists
    print('Removing duplicates from %s image list' % instrument)
    if instrument == 'OLCI':
        # select the most recent version of all images
        img_names, urls = sel_most_recent_olci(img_names, urls)
    image_names = []
    url_dwld = []
    for x in range(len(img_names)):
        if img_names[x] not in image_names:
            image_names.append(img_names[x])
            url_dwld.append(urls[x])
    # remove empty string from image and url lists
    image_names = list(filter(None, image_names))
    url_dwld = list(filter((URL_CREODIAS_GET_FILE + '/').__ne__, url_dwld))
    url_dwld = list(filter((URL_GET_FILE_CMR).__ne__, url_dwld))
    url_dwld = list(filter((URL_GET_FILE_CGI).__ne__, url_dwld))
    if access_platform == 'creodias':
        # get login key to include it into url
        login_key = get_login_key(username, password)
        sleep(5)
    else:
        login_key = None
    for i in range(len(url_dwld)):
        if os.path.isfile(image_names[i]):
            if verbose:
                print('Skip ' + image_names[i])
        else:
            max_retries = 5
            wait_seconds = 120
            for j in range(max_retries):
                try:
                    # Open session
                    with requests.Session() as s:
                        handle = open('tmp_' + image_names[i], "wb")
                        r, login_key = request_platform(s, 'tmp_' + image_names[i], url_dwld[i], access_platform,
                                                        username, password, login_key)
                        sleep(5)
                        r.raise_for_status()
                        if access_platform == 'creodias':
                            expected_length = int(r.headers.get('Content-Length'))
                            # complete the file even if connection is cut while downloading and file is incomplete
                            while os.stat('tmp_' + image_names[i]).st_size < expected_length:
                                r, login_key = request_platform(s, 'tmp_' + image_names[i], url_dwld[i],
                                                                access_platform, username, password, login_key)
                                sleep(5)
                                r.raise_for_status()
                                trump_shutup = 0
                                with open('tmp_' + image_names[i], "ab") as handle:
                                    for chunk in r.iter_content(chunk_size=16*1024):
                                        if chunk:
                                            handle.write(chunk)
                                            if verbose and os.path.isfile('tmp_' + image_names[i]):
                                                biden_president = round(float(
                                                    os.stat('tmp_' + image_names[i]).st_size)/expected_length*100, -1)
                                                if biden_president > trump_shutup:
                                                    sys.stdout.write('\rDownloading ' + image_names[i] +
                                                                     '      ' + str(biden_president) + '%')
                                                    trump_shutup = biden_president
                                            else:
                                                print('Warning: temporary file tmp_' + image_names[i] + ' not found')
                                if handle.closed:
                                    handle = open('tmp_' + image_names[i], "ab")
                                handle.flush()
                            actual_length = os.stat('tmp_' + image_names[i]).st_size
                            if actual_length < expected_length:
                                raise IOError('incomplete read ({} bytes read, {} more expected)'.
                                              format(actual_length, expected_length - actual_length))
                            handle.close()
                            print()
                            os.rename('tmp_' + image_names[i], image_names[i])
                            break
                        else:
                            if verbose:
                                print('Downloading ' + image_names[i])
                            with open('tmp_' + image_names[i], "ab") as handle:
                                for chunk in r.iter_content(chunk_size=16*1024):
                                    if chunk:
                                        handle.write(chunk)
                            handle.close()
                            os.rename('tmp_' + image_names[i], image_names[i])
                            break
                except requests.exceptions.HTTPError as e:
                    print('Requests error: %s. Attempt [%i/%i] reconnection ...' % (e, j+1, max_retries))
                    handle.close()
                except requests.exceptions.ConnectionError:
                    print('Build https connection failed: download failed, attempt [%i/%i] reconnection ...' %
                          (j+1, max_retries))
                    handle.close()
                except requests.exceptions.Timeout:
                    print('Request timed out: download failed, attempt [%i/%i] reconnection ...' % (j+1, max_retries))
                    handle.close()
                except requests.exceptions.RequestException:
                    print('Unknown error: download failed, attempt [%i/%i] reconnection ...' % (j+1, max_retries))
                    handle.close()
                except socket.timeout:
                    print('Connetion lost: download failed, attempt [%i/%i] reconnection ...' % (j+1, max_retries))
                    handle.close()
                if j+2 == max_retries:
                    return None
                sleep(wait_seconds)
            else:
                print('%d All connection attempts failed, download aborted.\n'
                      '\t- Did you accept the End User License Agreement for this dataset ?\n'
                      '\t- Check login/username.\n'
                      '\t- Check image name/url in *.csv file\n'
                      '\t- Check for connection problems \n'  
                      '\t- Check for blocked IP \n')
                # Earthdata download issuecheck https://oceancolor.gsfc.nasa.gov/forum/oceancolor/topic_show.pl?tid=6447
                # When IP blocked on Earthdata email: connection_problems@oceancolor.gsfc.nasa.gov)
                return None


if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser(usage="Usage: getOC.py [options] [filename]", version="getOC " + __version__)
    parser.add_option("-i", "--instrument", action="store", dest="instrument",
                      help="specify instrument, available options are: VIIRS, MODIS-Aqua, MODIS-Terra, OCTS, CZCS, "
                           "MERIS, HICO, SeaWiFS, OLCI, SLSTR , MSI (L1C and L2A < 12 month)")
    parser.add_option("-l", "--level", action="store", dest="level", default='L2',
                      help="specify processing level, available options are: GEO, L1A, L1C (MSI only), L2A (MSI only),"
                           " L2, L3b (only for EarthData queries), and L3m (only for EarthData queries), append "
                           "'_ERR' to level for lower OLCI resolution or '_EFR' for full resolution")
    # Level 2 specific option
    parser.add_option("-p", "--product", action="store", dest="product", default='OC',
                      help="specify product identifier (only for L2), available options are: OC, SST, and IOP, "
                      "not available for CREODIAS queries (OLCI, SLSTR and MSI)")
    parser.add_option("-d", "--delay", action="store", dest="query_delay", type='float', default=1,
                      help="Delay between queries only needed to query L1L2_browser")
    # Level 3 specific options
    parser.add_option("-b", "--binning-period", action="store", dest="binning_period", default='8D',
                      help="specify binning period (only for L3), available options are: DAY, 8D, MO, and YR")
    parser.add_option("--res", "--spatial-resolution", action="store", dest="sresol", default='4km',
                      help="specify spatial resolution (only for L3), available options are: 4km, 9km")
    # credential specific options
    parser.add_option("-u", "--username", action="store", dest="username", default=None,
                      help="specify username to login Creodias (OLCI / SLSTR / MSI) or EarthData (any other sensor)"
                           "(Copernicus DEPRECATED)")
    # Other options
    parser.add_option("-w", "--write-image-links", action="store_true", dest="write_image_links", default=False,
                      help="Write query results image names and corresponding url into csv file.")
    parser.add_option("-r", "--read-image-list", action="store_true", dest="read_image_list", default=False,
                      help="Read previous query from csv file")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True)
    parser.add_option("--box", "--bounding-box-size", action="store", dest="bounding_box_sz", type='float', default=60,
                      help="specify bounding box size in nautical miles")
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
    if len(args) < 1 and options.level:
        print(parser.usage)
        print('getOC.py: error: argument filename is required for Level GEO, L1A, or L2')
        sys.exit(-1)
    elif len(args) > 2:
        print(parser.usage)
        print('getOC.py: error: too many arguments')
        sys.exit(-1)
    image_names = list()
    url_dwld = list()
    # Get list of images to download
    if options.read_image_list:
        if os.path.isfile(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                          options.level + '_' + options.product + '.csv'):
            pois = read_csv(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                            options.level + '_' + options.product + '.csv',
                            names=['id', 'dt', 'lat', 'lon', 'image_names', 'url', 'prod_entity'], parse_dates=[1])
            pois.dropna(subset=['image_names'], axis=0, inplace=True)
            points_of_interest = pois.copy()
            access_platform, password = get_platform(points_of_interest['dt'], options.instrument, options.level)
            # Parse image_names and url
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
                      options.level + '_' + options.product + '.csv' +
                      ' does not exist, select option -w (write) instead of -r (read)')
            sys.exit(0)
    else:
        # Parse csv file containing points of interest
        points_of_interest = read_csv(args[0], names=['id', 'dt', 'lat', 'lon'], parse_dates=[1])
        access_platform, password = get_platform(points_of_interest['dt'], options.instrument, options.level)
        query_string = set_query_string(access_platform, options.instrument, options.level, options.product)
        # if access_platform == 'copernicus': # DEPRECATED
        #     pois = get_image_list_copernicus(points_of_interest, access_platform, options.username, password,
        #                     query_string, options.instrument, options.level)
        print('Query %s level %s %s on %s' % (options.instrument, options.level, options.product, access_platform))
        if access_platform == 'creodias':
            pois = get_image_list_creodias(points_of_interest, access_platform,
                                           query_string, options.instrument, options.level)
        elif access_platform == 'L1L2_browser':
            pois = get_image_list_l12browser(points_of_interest, access_platform, query_string, options.instrument,
                                             options.level, options.product, options.query_delay)
        elif access_platform == 'cmr':
            pois = get_image_list_cmr(points_of_interest, access_platform, query_string, options.instrument,
                                      options.level, options.product)
        else:
            print('Error: plateform not recognized')
            sys.exit(-1)
        points_of_interest = pois.copy()
        # parse image_names
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

    print('Download completed')
