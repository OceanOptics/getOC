#!/usr/bin/env python
"""
Bulk download Ocean Color images.

MIT License

Copyright (c) 2019 Nils Haentjens & Guillaume Bourdin
"""

import sys
from datetime import datetime, timedelta
from operator import itemgetter
from getpass import getpass
import requests
# from requests.auth import HTTPBasicAuth
import re
import os
from time import sleep
from pandas import read_csv
import numpy as np
import pandas as pd
# import socket
import math
# import json
import logging

__version__ = "0.8.0"

# Set constants
URL_L12BROWSER = 'https://oceancolor.gsfc.nasa.gov/cgi/browse.pl'
URL_DIRECT_ACCESS = 'https://oceandata.sci.gsfc.nasa.gov/'
URL_SEARCH_API = 'https://oceandata.sci.gsfc.nasa.gov/api/file_search'
URL_GET_FILE_CGI = 'https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/'
URL_CMR = 'https://cmr.earthdata.nasa.gov/search/granules.json?provider=OB_DAAC'
URL_GET_FILE_CMR = 'https://oceandata.sci.gsfc.nasa.gov/ob/getfile/'
URL_SEARCH_COPERNICUS = 'https://catalogue.dataspace.copernicus.eu/resto/api/collections/'
URL_SEARCH_CREODIAS = 'https://finder.creodias.eu/resto/api/collections/'
URL_CREODIAS_LOGIN = 'https://auth.creodias.eu/auth/realms/DIAS/protocol/openid-connect/token'
URL_CREODIAS_GET_FILE = 'https://zipper.creodias.eu/download'

# add dates to logs
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
# initialize logger
logger = logging.getLogger('getOC.py')
# choose log level
logger.setLevel(os.environ.get("LOGLEVEL", 'INFO'))

# Documentation of Ocean Color Data Format Specification
# https://oceancolor.gsfc.nasa.gov/products/
INSTRUMENT_FILE_ID = {'SeaWiFS': 'S',
                      'MODIS-Aqua': 'A',
                      'MODIS-Terra': 'T',
                      'OCTS': 'O',
                      'CZCS': 'C',
                      'GOCI': 'G',
                      'MERIS': 'M',
                      'VIIRSN': 'V',
                      'VIIRSJ1': 'V',
                      'VIIRSJ2': 'V',
                      'HICO': 'H',
                      'OLCI': 'Sentinel3',
                      'SLSTR': 'Sentinel3',
                      'SRAL': 'Sentinel3',
                      'SYN': 'Sentinel3',
                      'MSI': 'Sentinel2',
                      'SAR': 'Sentinel1',
                      'L5-TM': 'Landsat5',
                      'L7-ETM': 'Landsat7',
                      'L8-OLI-TIRS': 'Landsat8'}
INSTRUMENT_QUERY_ID = {'SeaWiFS': 'MLAC',
                       'MODIS-Aqua': 'amod',
                       'MODIS-Terra': 'tmod',
                       'OCTS': 'oc', 'CZCS': 'cz',
                       'GOCI': 'goci',
                       'MERIS': 'RR',
                       'VIIRSN': 'vrsn',
                       'VIIRSJ1': 'vrj1',
                       'VIIRSJ2': 'vrj2',
                       'HICO': 'hi',
                       'OLCI': 'OLCI',
                       'SLSTR': 'SLSTR',
                       'SRAL': 'SRAL',
                       'SYN': 'SYN',
                       'MSI': 'MSI',
                       'SAR': 'SAR',
                       'L5-TM': 'L5-TM',
                       'L7-ETM': 'L7-ETM',
                       'L8-OLI-TIRS': 'L8-OLI-TIRS'}
DATA_TYPE_ID = {'SeaWiFS': 'LAC',
                'MODIS-Aqua': 'LAC',
                'MODIS-Terra': 'LAC',
                'OCTS': 'LAC',
                'CZCS': '',
                'MERIS': 'RR',
                'VIIRSN': 'SNPP',
                'VIIRSJ1': 'JPSS1',
                'VIIRSJ2': 'JPSS2',
                'HICO': 'ISS',
                'OLCI_L1-ERR': 'productType=OL_1_ERR___&processingLevel=1&instrument=OLCI',
                'OLCI_L1-EFR': 'productType=OL_1_EFR___&processingLevel=1&instrument=OLCI',
                'SLSTR_L1-RBT': 'productType=SL_1_RBT___&processingLevel=1&instrument=SLSTR',
                'OLCI_L2-WRR': 'productType=OL_2_WRR___&processingLevel=2&instrument=OLCI',
                'OLCI_L2-WFR': 'productType=OL_2_WFR___&processingLevel=2&instrument=OLCI',
                'OLCI_L2-LRR': 'productType=OL_2_LRR___&processingLevel=2&instrument=OLCI',
                'OLCI_L2-LFR': 'productType=OL_2_LFR___&processingLevel=2&instrument=OLCI',
                'SLSTR_L2-WST': 'productType=SL_2_WST___&processingLevel=2&instrument=SLSTR',
                'SLSTR_L2-LST': 'productType=SL_2_LST___&processingLevel=2&instrument=SLSTR',
                'SLSTR_L2-AOD': 'productType=SL_2_AOD___&processingLevel=2&instrument=SLSTR',
                'SLSTR_L2-FRP': 'productType=SL_2_FRP___&processingLevel=2&instrument=SLSTR',
                'SRAL_L1-SRA': 'productType=SR_1_SRA___&processingLevel=1&instrument=SRAL',
                'SRAL_L1-SRA-A': 'productType=SR_1_SRA_A_&processingLevel=1&instrument=SRAL',
                'SRAL_L1-SRA-BS': 'productType=SR_1_SRA_BS&processingLevel=1&instrument=SRAL',
                'SRAL_L2-WAT': 'productType=SR_2_WAT___&processingLevel=2&instrument=SRAL',
                'SRAL_L2-LAN': 'productType=SR_2_LAN___&processingLevel=2&instrument=SRAL',
                'SRAL_L2-LAN-HY': 'productType=SR_2_LAN_HY&processingLevel=2&instrument=SRAL',
                'SRAL_L2-LAN-LY': 'productType=SR_2_LAN_LY&processingLevel=2&instrument=SRAL',
                'SRAL_L2-LAN-SI': 'productType=SR_2_LAN_SI&processingLevel=2&instrument=SRAL',
                'SYN_L2-SYN': 'productType=SY_2_SYN___&processingLevel=2&instrument=SYNERGY',
                'SYN_L2-V10': 'productType=SY_2_V10___&processingLevel=2&instrument=SYNERGY',
                'SYN_L2-VG1': 'productType=SY_2_VG1___&processingLevel=2&instrument=SYNERGY',
                'SYN_L2-VGP': 'productType=SY_2_VGP___&processingLevel=2&instrument=SYNERGY',
                'SYN_L2-AOD': 'productType=SY_2_AOD___&processingLevel=2&instrument=SYNERGY',
                'MSI_L1C': 'productType=S2MSI1C&processingLevel=S2MSI1C&instrument=MSI',
                'MSI_L2A': 'productType=S2MSI2A&processingLevel=S2MSI2A&instrument=MSI',
                'L5-TM_L1G': 'processingLevel=LEVEL1G&instrument=TM',
                'L5-TM_L1T': 'processingLevel=LEVEL1T&instrument=TM',
                'L7-ETM_L1G': 'processingLevel=LEVEL1G&instrument=ETM',
                'L7-ETM_L1GT': 'processingLevel=LEVEL1GT&instrument=ETM',
                'L7-ETM_L1T': 'processingLevel=LEVEL1T&instrument=ETM',
                'L7-ETM_TC-1P': 'processingLevel=LEVEL1TTC_1P&instrument=ETM',
                'L8-OLI-TIRS_L1': 'processingLevel=LEVEL1&instrument=OLI_TIRS',
                'L8-OLI-TIRS_L1GT': 'processingLevel=LEVEL1GT&instrument=OLI_TIRS',
                'L8-OLI-TIRS_L1T': 'processingLevel=LEVEL1T&instrument=OLI_TIRS',
                'L8-OLI-TIRS_L1TP': 'processingLevel=LEVEL1TP&instrument=OLI_TIRS',
                'L8-OLI-TIRS_L2': 'processingLevel=LEVEL2&instrument=OLI_TIRS',
                'L8-OLI-TIRS_L2SP': 'processingLevel=LEVEL2SPT&instrument=OLI_TIRS',
                'SAR_L0-RAW': 'productType=RAW&processingLevel=LEVEL0&instrument=SAR',
                'SAR_L1-GRD': 'productType=GRD&processingLevel=LEVEL1&instrument=SAR',
                'SAR_L1-GRD-COG': 'productType=GRD-COG&processingLevel=LEVEL1&instrument=SAR',
                'SAR_L1-SLC': 'productType=SLC&processingLevel=LEVEL1&instrument=SAR',
                'SAR_L2-OCN': 'productType=OCN&processingLevel=LEVEL2&instrument=SAR',
                'SAR_L2-CARD-BS': 'productType=CARD-BS&processingLevel=LEVEL2&instrument=SAR',
                'SAR_L2-CARD-COH12': 'productType=CARD-COH12&processingLevel=LEVEL2&instrument=SAR'}
LEVEL_CREODIAS = {'L1': 'LEVEL1',
                  'L2': 'LEVEL2',
                  'L1C': 'LEVEL1C',
                  'L2A': 'LEVEL2A'}
SEARCH_CMR = {'SeaWiFS': 'SEAWIFS',
              'MODIS-Aqua': 'MODISA',
              'MODIS-Terra': 'MODIST',
              'OCTS': 'OCTS',
              'CZCS': 'CZCS',
              'VIIRSN': 'VIIRSN',
              'VIIRSJ1': 'VIIRSJ1',
              'VIIRSJ2': 'VIIRSJ2',
              'GOCI': 'GOCI'}
EXTENSION_L1A = {'MODIS-Aqua': '',
                 'MODIS-Terra': '',
                 'VIIRSN': '.nc',
                 'VIIRSJ1': '.nc',
                 'VIIRSJ2': '.nc'}

# https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel1/describe.xml
# productType
# instrument: SAR
# CARD-BS CARD-COH6 CARD-COH12 GRD GRD-COG OCN RAW SLC

# https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/describe.xml
# productType
# instrument: MSI
# S2MSI1C S2MSI2A

# info collection: https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel3/describe.xml
# productType
# instrument: OLCI
# OL_1_EFR___ OL_1_ERR___
# OL_2_WFR___ OL_2_WRR___ OL_2_LFR___ OL_2_LRR___
# instrument: SLSTR
# SL_1_RBT___
# SL_2_AOD___ SL_2_FRP___ SL_2_WST___ SL_2_LST___
# instrument: SRAL
# SR_1_SRA___ SR_1_SRA_A_ SR_1_SRA_BS
# SR_2_WAT___ SR_2_LAN___ SR_2_LAN_HY SR_2_LAN_LY SR_2_LAN_SI
# instrument: SYN
# SY_2_SYN___ SY_2_V10___ SY_2_VG1___ SY_2_VGP___ SY_2_AOD___

# https://catalogue.dataspace.copernicus.eu/resto/api/collections/Landsat5/describe.xml
# productType
# instrument: OLI/TIRS
# L1G L1T

# https://catalogue.dataspace.copernicus.eu/resto/api/collections/Landsat7/describe.xml
# productType
# instrument: OLI/TIRS
# GTC_1P L1G L1GT L1T

# https://catalogue.dataspace.copernicus.eu/resto/api/collections/Landsat8/describe.xml
# productType
# instrument: OLI/TIRS
# L1GT L1T L1TP L2SP

def get_platform(dates, instrument, level):
    # Get acces plateform depending on product and date:
    # - COPERNICUS: MSI-L2A < 12 month, OLCI # DEPRECATED
    # - CREODIAS: MSI, OLCI, SLSTR (L1 and L2)
    # - Common Metadata Repository (CMR): MODISA, MODIST, VIIRSJ1, VIIRSJ2, VIIRSN, SeaWiFS, OCTS, CZCS (L2 and L3)
    # - L1/L2browser Ocean Color (requires 1s delay => slow): SeaWiFS, OCTS, CZCS (L0 and L1) / MERIS, HICO (all levels)
    # Note: if any query point dedicated to CMR is less than 2 days old, the entire query will be redirected to L1/L2browser (delay of storage on CMR)

    # if instrument == 'MSI' or instrument == 'SLSTR' or instrument == 'OLCI': # DEPRECATED
    #     access_platf = 'creodias'
    #     pwd = getpass(prompt='Creodias Password: ', stream=None)
    if instrument == 'MSI' or instrument == 'SLSTR' or instrument == 'OLCI' or instrument == 'SRAL' \
            or instrument == 'SYN' or instrument == 'L5-TM' or instrument == 'L8-ETM' or instrument == 'L8-OLI-TIRS' \
            or instrument == 'SAR':
        access_platf = 'copernicus'
        pwd = getpass(prompt='Copernicus Password: ', stream=None)
    elif level == 'L0' or instrument == 'MERIS' or instrument == 'HICO':
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
        if access_platform == 'copernicus':
            # "https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json?productType=S2MSI1C&orbitDirection=DESCENDING&cloudCover=[0,100]&startDate=2016-06-11T00:00:00Z&completionDate=2016-06-22T23:59:59Z&maxRecords=200&box=55,-21,56,-20"
            # make sure product type is included in level for SLSTR OLCI SRAL SYN
            if (instrument == 'SLSTR' or instrument == 'OLCI' or instrument == 'SRAL' or instrument == 'SYN' or
                instrument == 'SAR') and \
                    '-' not in level:
                logger.exception('ValueError: Product type "level-producttype" required for %s' % instrument)
                sys.exit(-1)
            dattyp = '%s_%s' % (instrument, level)
            if dattyp in DATA_TYPE_ID:
                query_str = DATA_TYPE_ID[dattyp]
            else:
                logger.exception('ValueError: level %s not supported for %s sensor' % (level, instrument))
                sys.exit(-1)
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
                logger.exception('ValueError: level %s not supported for %s sensor' % (level, instrument))
                sys.exit(-1)
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
                    logger.exception('ValueError: product %s not supported for %s sensor' % (product, instrument))
                    sys.exit(-1)
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
                logger.exception('ValueError: level %s not supported for %s sensor' % (level, instrument))
                sys.exit(-1)
            query_str = '?sub=' + sub + sen + '&dnm=' + dnm + '&prm=' + prm
        elif access_platform == 'cmr':
            sen = SEARCH_CMR[instrument]
            if 'L1' in level:
                query_str = '&short_name=' + sen + '_' + level[0:2]
            else:
                query_str = '&short_name=' + sen + '_' + level + '_' + product
        else:
            logger.exception('Error: API not recognized for %s level %s suite %s' % (instrument, level, product))
            sys.exit(-1)
        return query_str
    else:
        logger.exception('Error: instrument %s not supported' % instrument)
        sys.exit(-1)


def format_dtlatlon_query(poi, access_platform):
    # Add room around poi using bounding box option (default = 60 nautical miles), and wrap longitude into [-180:180]
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
        raise RuntimeError('Unable to get login key. Response was ' + login_key.text)


def get_keycloak(username: str, password: str) -> str:
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    try:
        r = requests.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data=data,
            )
        r.raise_for_status()
    except Exception as e:
        raise Exception(
            f"Keycloak token creation failed. Reponse from the server was: {r.json()}"
        )
    return r.json()["access_token"]


def clean_nrt_nt_files(imlistraw, fid_list):
    sel_img = []
    sel_fid = []
    for i in range(len(imlistraw)):
        if 'NRT' not in imlistraw[i]:
            sel_img.append(imlistraw[i])
            sel_fid.append(fid_list[i])
        elif imlistraw[i].replace('.NRT.nc', 'nc') not in imlistraw:
            sel_img.append(imlistraw[i])
            sel_fid.append(fid_list[i])
    return sel_img, sel_fid


def sel_most_recent_esa(imlistraw, fid_list, instrument):
    sel_s3 = find_most_recent_esa(imlistraw, instrument)
    sel_fid = []
    for i in range(len(imlistraw)):
        if imlistraw[i] in sel_s3:
            sel_fid.append(fid_list[i])
    return sel_s3, sel_fid


def find_most_recent_esa(imlistraw, instrument):
    ref = imlistraw
    if 'OLCI' in instrument:
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
    elif 'MSI' in instrument:
        dt_processing = [datetime.strptime(x.replace('.SAFE.zip', '').split('_')[-1], '%Y%m%dT%H%M%S') for x in ref]
        ref = ['_'.join(itemgetter(*[0,1,2,4,5])(x.replace('.SAFE.zip', '').split('_'))) for x in ref]
        dtx = np.array(dt_processing)
        refx = np.array(ref)
        imlistrawx = np.array(imlistraw)
        uref = np.unique(refx)
        todelete = []
        for singlref in uref:
            str_match = imlistrawx[np.where(refx == singlref)]
            dt_match = dtx[np.where(refx == singlref)]
            if len(dt_match) > 1:
                # select last reprocessing
                dt_ref = datetime.utcnow()
                recent_dt = dt_match[np.where(abs(dt_match - dt_ref) == min(abs(dt_match - dt_ref)))]
                ref_tokeep = imlistrawx[np.logical_and(refx == singlref, dtx == recent_dt)]
                ref_todel = str_match[ref_tokeep != str_match]
                for todel in ref_todel:
                    todelete.append(todel)
                    imlistraw = list(filter(todel.__ne__, imlistraw))
    return imlistraw


def get_image_list_copernicus(pois, access_platform, query_string, instrument, level='L1', cloud_cover='[0,100]'):
    # https://documentation.dataspace.copernicus.eu/APIs/
    # Add column to points of interest data frame
    maxretries = 10
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    for i, poi in pois.iterrows():
        logger.info('[%i/%i]   Querying %s %s %s on Copernicus    %s    %.5f  %.5f' %
                    (i + 1, len(pois), poi['id'], instrument, level, poi['dt'], poi['lat'], poi['lon']))
        # get polygon around poi and date
        w, s, e, n, day_st, day_end = format_dtlatlon_query(poi, access_platform)
        query = "%s%s/search.json?%s&cloudCover=%s&startDate=%s&completionDate=%s&maxRecords=200&box=%s,%s,%s,%s" % \
                (URL_SEARCH_COPERNICUS, INSTRUMENT_FILE_ID[instrument], query_string, cloud_cover,
                 day_st.strftime("%Y-%m-%dT%H:%M:%S.000Z"), day_end.strftime("%Y-%m-%dT%H:%M:%S.000Z"), w, s, e, n)
        r = requests.get(query).json()
        attempt = 0
        while 'features' not in list(r.keys()) and attempt <= maxretries:
            r = requests.get(query).json()
            attempt += 1
            logger.info('Image feature not found in server response, retry [%i/%i]' % (attempt, maxretries))
            sleep(5)
        # extract image name, id, and status from response
        if 'features' in list(r.keys()):
            img_features = pd.DataFrame.from_dict(r['features'])
            if len(img_features) > 0:
                url_list = list(img_features.id)
                img_properties = dict(img_features.properties)
                imlistraw = list()
                prod_meta = list()
                for im in range(len(url_list)):
                    imlistraw.append(img_properties[im]['title'] + '.zip')
                    prod_meta.append(img_properties[im]['status'])
                sel_s3, sel_fid = sel_most_recent_esa(imlistraw, url_list, instrument)
                # populate lists with image name, id, and status
                # pois.at[i, 'image_names'] = [s + '.zip' for s in sel_s3]
                pois.at[i, 'image_names'] = sel_s3
                pois.at[i, 'url'] = sel_fid
        else:
            logger.info('%s unsuccessful attemps to retrieve image feature in server response, '
                        'datetime %s, lat %s, lon %s ignored' % (maxretries, poi['dt'], poi['lat'], poi['lon']))
    return pois


def get_image_list_creodias(pois, access_platform, query_string, instrument, level='L1C'):  # username, password,
    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    for i, poi in pois.iterrows():
        logger.info('[%i/%i]   Querying %s %s %s on Creodias    %s    %.5f  %.5f' %
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
        fid_list = re.findall(r'{"download":{"url":"https://zipper.creodias.eu/download/(.*?)","mimeType"',
                              r.text)
        sel_s3, sel_fid = sel_most_recent_esa(imlistraw, fid_list, instrument)
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
    for i, poi in pois.iterrows():
        logger.info('[%i/%i]   Querying %s %s %s %s on L1L2_browser    %s    %.5f  %.5f' %
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


def select_day_night_flag(r, imlistraw, dn_flag):
    if dn_flag.lower() != 'both':
        daynight_flag = re.findall(r'"day_night_flag":"(.*?)","time_end":', r.text)
        imlistraw = [x for x, dn in zip(imlistraw, daynight_flag) if dn == dn_flag.upper()]
    return imlistraw


def get_image_list_cmr(pois, access_platform, query_string, instrument, level='L2', product='OC', dn_flag='both'):
    # https://cmr.earthdata.nasa.gov/search/granules.json?provider=OB_DAAC&short_name=MODISA_L2_OC&temporal=2016-08-21T00:00:01Z,2016-08-22T00:00:01Z&page_size=2000&page_num=1
    # https://cmr.earthdata.nasa.gov/search/granules.json?provider=OB_DAAC&short_name=VIIRSJ1_L1&temporal=2020-08-16T00:00:01Z,2020-08-17T00:00:01Z&page_size=2000&page_num=1
    # https://cmr.earthdata.nasa.gov/search/granules.json?provider=OB_DAAC&short_name=VIIRSJ1_L1_GEO&temporal=2020-08-16T00:00:01Z,2020-08-17T00:00:01Z&page_size=2000&page_num=1
    # Add column to points of interest data frame
    pois['image_names'] = [[] for _ in range(len(pois))]
    pois['url'] = [[] for _ in range(len(pois))]
    for i, poi in pois.iterrows():
        logger.info('[%i/%i]   Querying %s %s %s %s on CMR    %s    %.5f  %.5f' %
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
        imlistraw = select_day_night_flag(r, imlistraw, dn_flag)
        # run second query for GEO files if VIIRS and L1A
        if 'VIIRS' in instrument and level == 'L1A' or level == 'L1':
            query = '%s%s&bounding_box=%s,%s,%s,%s&temporal=%s,%s&page_size=2000&page_num=1' % \
                    (URL_CMR, query_string.replace('_L1', '_L1_GEO'), w, s, e, n, day_st.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     day_end.strftime("%Y-%m-%dT%H:%M:%SZ"))
            r = requests.get(query)
            # extract image name from response
            imlist_temp = re.findall(r'https://oceandata.sci.gsfc.nasa.gov/cmr/getfile/(.*?)"},', r.text)
            imlist_temp = select_day_night_flag(r, imlist_temp, dn_flag)
            imlistraw = imlistraw + imlist_temp
        # run second query for NRT files if date_st or date_end more recent than 60 days
        if datetime.utcnow() - day_st < timedelta(days=60) or datetime.utcnow() - day_end < timedelta(days=60):
            query = '%s%s_NRT&bounding_box=%s,%s,%s,%s&temporal=%s,%s&page_size=2000&page_num=1' % \
                    (URL_CMR, query_string, w, s, e, n, day_st.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     day_end.strftime("%Y-%m-%dT%H:%M:%SZ"))
            r = requests.get(query)
            # extract image name from response
            imlist_temp = re.findall(r'https://oceandata.sci.gsfc.nasa.gov/cmr/getfile/(.*?)"},', r.text)
            imlist_temp = select_day_night_flag(r, imlist_temp, dn_flag)
            imlistraw = imlistraw + imlist_temp
        if level == 'L3m' or product == 'L3b':
            imlistraw = [x for x in imlistraw if options.sresol in x and options.binning_period in x]
        # Keep only good image name
        if instrument == 'VIIRSN':
            imlistraw = [x for x in imlistraw if "SNPP_VIIRS." in x]
        if instrument == 'VIIRSJ1':
            imlistraw = [x for x in imlistraw if "JPSS1_VIIRS." in x]
        if instrument == 'VIIRSJ2':
            imlistraw = [x for x in imlistraw if "JPSS2_VIIRS." in x]
        if 'MODIS' in instrument:
            if 'L1' in level:
                imlistraw = [s + '.bz2' for s in imlistraw]
            else:
                imlistraw = [x for x in imlistraw if "MODIS" in x]
        # populate lists with image name and url
        pois.at[i, 'image_names'] = imlistraw
        pois.at[i, 'url'] = ['%s%s' % (URL_GET_FILE_CMR, s) for s in imlistraw]
    return pois


def request_platform(s, image_names, url_dwld, access_platform, username, password, login_key_in):
    if access_platform == 'copernicus':
        # get keycloak_token
        login_key = get_keycloak(username, password)
        # start download request
        url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products(%s)/$value" % url_dwld
        s.headers.update({'Authorization': 'Bearer %s' % login_key})
        response = s.get(url, allow_redirects=False)
        while response.status_code in (301, 302, 303, 307):
            url = response.headers['Location']
            response = s.get(url, allow_redirects=False, stream=True, timeout=30)
        return response, None, url
    elif access_platform == 'creodias':  # DEPRECATED
        headers = {'Range': 'bytes=' + str(os.stat('tmp_' + image_names).st_size) + '-'}
        response = s.get(url_dwld + login_key_in, stream=True, timeout=900, headers=headers)
        if response.status_code != 200 and response.status_code != 206:
            if response.text == 'Expired signature!':
                logger.info('Login expired, reconnection ...')
                # get login key to include it into url
                login_key = get_login_key(username, password)
                response = s.get(url_dwld + login_key, stream=True, timeout=900, headers=headers)
            else:
                login_key = None
                logger.info(response.status_code)
                logger.info(response.text)
                logger.info('Unable to download from https://auth.creodias.eu/\n'
                            '\t- Check login/username\n'
                            '\t- Invalid image name?')
            return response, login_key, None
    else:
        # modify header to hide requests query and mimic web browser
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, '
                                 'like Gecko) Chrome/68.0.3440.106 Safari/537.36',}
        response = s.get(url_dwld, auth=(username, password), stream=True, timeout=900, headers=headers)
        return response, None, None


def download_files(file_todownload, file_name, expected_sz):
    prev_file_sz = 0
    with open(file_name, "ab") as handle:
        for chunk in file_todownload.iter_content(chunk_size=128 * 1024):
            if chunk:
                handle.write(chunk)
                if os.path.isfile(file_name):
                    tmp_file_sz = round(float(
                        os.stat(file_name).st_size) / expected_sz * 100, -1)
                    if tmp_file_sz > prev_file_sz:
                        if verbose:
                            sys.stdout.write('\rDownloading %s   %s%%' %
                                             (file_name.replace('tmp_', ''), str(round(tmp_file_sz))))
                        prev_file_sz = tmp_file_sz
                else:
                    logger.info('Warning: temporary file %s not found' % file_name)
    if handle.closed:
        handle = open(file_name, "ab")
    handle.flush()
    actual_length = os.stat(file_name).st_size
    if actual_length < expected_sz:
        raise IOError('incomplete read ({} bytes read, {} more expected)'.
                      format(actual_length, expected_sz - actual_length))
    if verbose:
        print(' done')
    return handle


def login_download(img_names, urls, instrument, access_platform, username, password):
    # Login to Earth Data and Download image
    if len(urls) == 0 or len(img_names) == 0:
        logger.warning('No image to download.')
        return None
    # remove duplicate from image and url lists
    logger.info('Removing duplicates from %s image list' % instrument)
    if instrument == 'OLCI' or instrument == 'MSI':
        # select the most recent version of all images
        img_names, urls = sel_most_recent_esa(img_names, urls, instrument)
    else:
        img_names, urls = clean_nrt_nt_files(img_names, urls)
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
        sleep(1)
    else:
        login_key = None
    handle = None
    for i in range(len(url_dwld)):
        dwnld_bool = True
        if os.path.isfile(image_names[i]):
            if float(os.stat(image_names[i]).st_size) > 2*10**5:
                dwnld_bool = False
                logger.info('Skip ' + image_names[i])
            else:
                logger.info('File %s exists but incomplete (< 200Kb): downloading again' % image_names[i])
                os.remove(image_names[i])
        elif os.path.isfile('tmp_' + image_names[i]):
            os.remove('tmp_' + image_names[i])
        if dwnld_bool:
            max_retries = 10
            wait_seconds = 30
            attempts = 0
            while attempts < max_retries:
                try:
                    # Open session
                    logger.info('Downloading %s' % image_names[i])
                    with requests.Session() as s:
                        r, login_key, url = request_platform(s, 'tmp_' + image_names[i], url_dwld[i],
                                                             access_platform, username, password, login_key)
                        sleep(0.1)
                        r.raise_for_status()
                        if access_platform == 'copernicus':
                            with s.get(url, allow_redirects=True, stream=True) as file:
                                file.raise_for_status()
                                expected_length = int(file.headers.get('Content-Length'))
                                handle = download_files(file, 'tmp_' + image_names[i], expected_length)
                        elif access_platform == 'creodias' or 'cmr':  # creodias is DEPRECATED
                            expected_length = int(r.headers.get('Content-Length'))
                            handle = download_files(r, 'tmp_' + image_names[i], expected_length)
                        else:
                            with open('tmp_' + image_names[i], "ab") as handle:
                                for chunk in r.iter_content(chunk_size=128*1024):
                                    if chunk:
                                        handle.write(chunk)
                            if handle.closed:
                                handle = open('tmp_' + image_names[i], "ab")
                            handle.flush()
                            actual_length = float(os.stat('tmp_' + image_names[i]).st_size)
                            if actual_length < 2*10**5:
                                raise IOError('Download incomplete (< 200Kb): %i bytes downloaded' % actual_length)
                        handle.close()
                        os.rename('tmp_' + image_names[i], image_names[i])
                        break
                except Exception as e:
                    logger.exception('Error downloading %s: %s. Attempt [%i/%i] reconnection ...' %
                                     (image_names[i], e, attempts+1, max_retries))
                    if handle:
                        handle.close()
                    attempts += 1
                    if os.path.isfile('tmp_' + image_names[i]):
                        os.remove('tmp_' + image_names[i])
                    if os.path.isfile(image_names[i]):
                        os.remove(image_names[i])
                    if attempts < max_retries:
                        sleep(wait_seconds)
                    else:
                        logger.exception('%d All download attempts failed: aborted.\n'
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
                      help="specify instrument, available options are: VIIRSN, VIIRSJ1, VIIRSJ2, MODIS-Aqua, "
                           "MODIS-Terra, OCTS, CZCS, MERIS, HICO, SeaWiFS, OLCI, SLSTR , MSI (L1C and L2A < 12 month)")
    parser.add_option("-l", "--level", action="store", dest="level", default='L2',
                      help="specify processing level, available options are: GEO, L1A, L1C (MSI only), L2A (MSI only),"
                           " L2, L3b (only for EarthData queries), and L3m (only for EarthData queries), append "
                           "'_ERR' or '-ERR' for lower OLCI resolution and '_EFR' or '-EFR' for full resolution")
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
    parser.add_option("-w", "--write-image-names", action="store_true", dest="write_image_names", default=True,
                      help="Write query results image names and corresponding url into csv file.")
    parser.add_option("--dn", "--day-night-flag", action="store", dest="dn_flag", type='str', default='both',
                      help="Select day, night or both images, default = both")
    parser.add_option("-r", "--read-image-list", action="store_true", dest="read_image_list", default=False,
                      help="Read previous query from csv file")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True)
    parser.add_option("--box", "--bounding-box-size", action="store", dest="bounding_box_sz", type='float', default=60,
                      help="specify bounding box size in nautical miles")
    parser.add_option("-c", "--cloud-cover", action="store", dest="cloud_cover", type='str', default='[0, 100]',
                      help="specify cloud cover interval to download")
    (options, args) = parser.parse_args()
    verbose = options.verbose
    if options.instrument is None:
        logger.info(parser.usage)
        logger.info('getOC.py: error: option -i, --instrument is required')
        sys.exit(-1)
    if 'L3' not in options.level and options.username is None:
        logger.info(parser.usage)
        logger.info('getOC.py: error: option -u, --username is required')
        sys.exit(-1)
    if len(args) < 1 and options.level:
        logger.info(parser.usage)
        logger.info('getOC.py: error: argument filename is required for Level GEO, L1A, or L2')
        sys.exit(-1)
    elif len(args) > 2:
        logger.info(parser.usage)
        logger.info('getOC.py: error: too many arguments')
        sys.exit(-1)
    # levelname = options.level.replace('_', '-')
    # options.level = options.level.replace('-', '_')
    image_names = list()
    url_dwld = list()
    # Get list of images to download from written file if available
    if options.read_image_list and os.path.isfile(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                                                  options.level + '_' + options.product + '.csv'):
        options.write_image_names = False
        pois = read_csv(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                        options.level + '_' + options.product + '.csv',
                        names=['id', 'dt', 'lat', 'lon', 'image_names', 'url'], parse_dates=[1])
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
    elif options.read_image_list:
        logger.exception('IOError: [Errno 2] Option -r (read) was selected, however, file ' +
                         os.path.splitext(args[0])[0] + '_' + options.instrument + '_' + options.level + '_' +
                         options.product + '.csv' + ' does not exist: option -w (write) was activated by default')
        options.write_image_names = True
    # Query list of images to download
    if options.write_image_names:
        # Parse csv file containing points of interest
        points_of_interest = read_csv(args[0], names=['id', 'dt', 'lat', 'lon'], parse_dates=[1])
        access_platform, password = get_platform(points_of_interest['dt'], options.instrument, options.level)
        query_string = set_query_string(access_platform, options.instrument, options.level, options.product)
        # if access_platform == 'creodias':  # DEPRECATED
        #     pois = get_image_list_creodias(points_of_interest, access_platform,
        #                                    query_string, options.instrument, options.level)
        logger.info('Query %s level %s %s on %s' % (options.instrument, options.level, options.product, access_platform))#
        if access_platform == 'copernicus':
            pois = get_image_list_copernicus(points_of_interest, access_platform,
                                             query_string, options.instrument, options.level, options.cloud_cover)
        elif access_platform == 'L1L2_browser':
            pois = get_image_list_l12browser(points_of_interest, access_platform, query_string, options.instrument,
                                             options.level, options.product, options.query_delay)
        elif access_platform == 'cmr':
            pois = get_image_list_cmr(points_of_interest, access_platform, query_string, options.instrument,
                                      options.level, options.product, options.dn_flag)
        else:
            logger.exception('Error: plateform not recognized')
            sys.exit(-1)
        points_of_interest = pois.copy()
        # parse image_names
        for _, poi in pois.iterrows():
            image_names.extend(poi['image_names'])
            url_dwld.extend(poi['url'])
    # Write list of images to download in csv
    if options.write_image_names:
        # Reformat image names & url
        for i, poi in points_of_interest.iterrows():
            points_of_interest.at[i, 'image_names'] = ';'.join(poi['image_names'])
            points_of_interest.at[i, 'url'] = ';'.join(poi['url'])
        points_of_interest.to_csv(os.path.splitext(args[0])[0] + '_' + options.instrument + '_' +
                                  options.level + '_' + options.product + '.csv',#
                                  date_format='%Y/%m/%d %H:%M:%S', header=False, index=False, float_format='%.5f')
    # Download images from url list
    login_download(image_names, url_dwld, options.instrument, access_platform, options.username, password)
    logger.info('Download completed')
