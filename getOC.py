#!/usr/bin/env python
"""
Bulk download Ocean Color images.

MIT License

Copyright (c) 2021 Nils Haentjens & Guillaume Bourdin
"""
import sys
from datetime import datetime, timedelta
from getpass import getpass
import requests
from requests.auth import HTTPBasicAuth
import re
import os
from time import sleep
import pandas as pd
import socket
import math

__version__ = "0.7.0"
verbose = False


def get_platform(last_date, instrument, level, *args, **kwargs):
    """
    Return instance of optimal platform to download data of interest, depends on product and date

        - COPERNICUS: MSI-L2A < 12 month, OLCI # DEPRECATED
        - CREODIAS: MSI, OLCI, SLSTR (L1 and L2)
        - Common Metadata Repository (CMR): MODISA, MODIST, VIIRSN, SeaWiFS, OCTS, CZCS (L2 and L3)
        - Ocean Color Level 1&2 Browser (OC): MODISA, MODIST, VIIRSJ1, SeaWiFS, OCTS, CZCS (L0 and L1),
                                              MERIS, HICO (all levels)
                                              requires 1s delay => slow
        Note: if any query point dedicated to CMR is less than 2 days old, the entire query will be redirected
        to L1/L2browser.

    :param last_date:
    :param instrument:
    :param level:
    :return:
    """
    recent_flag = datetime.utcnow() - last_date < timedelta(hours=48)
    # if instrument == 'MSI' and level == 'L2A':
    #     if instrument == 'MSI' and any(delta_today < timedelta(days=365)):
    #             print('Warning: query older than 12 month old will be ignored '
    #                   '(offline products unavailable for bulk download)') # DEPRECATED
    #     return PlatformCOPERNICUS(*args, **kwargs)  # DEPRECATED
    if instrument == 'MSI' or instrument == 'SLSTR' or instrument == 'OLCI':
        return PlatformCREODIAS(*args, **kwargs)
    elif level in ['L0', 'L1', 'L1A', 'GEO'] or \
            'MERIS' in instrument or instrument == 'HICO' or \
            recent_flag:
        return PlatformOC(*args, **kwargs)
    else:
        return PlatformCMR(*args, **kwargs)


class Platform:
    MAX_RETRIES = 3
    WAIT_SECONDS = 120
    URL_SEARCH = ''
    URL_GET_FILE = ''
    URL_AUTH = ''
    INSTRUMENT_QUERY_ID = {'SeaWiFS': 'swml', 'MODIS-Aqua': 'amod', 'MODIS-Terra': 'tmod', 'OCTS': 'octs',
                           'CZCS': 'czcs',
                           'GOCI': 'goci', 'MERIS-RR': 'merr', 'MERIS-FRS': 'mefr', 'VIIRSN': 'vrsn', 'VIIRSJ1': 'vrj1',
                           'HICO': 'hi',
                           'OLCI': 'OL', 'MSI': 'MSI', 'SLSTR': 'SL'}
    PRODUCT_TYPE = {'SeaWiFS': 'LAC', 'MODIS-Aqua': 'LAC', 'MODIS-Terra': 'LAC', 'OCTS': 'LAC', 'CZCS': '',
                    'MERIS': 'RR', 'VIIRSN': 'SNPP', 'VIIRSJ1': 'JPSS1', 'HICO': 'ISS',
                    'OLCI_L1_ERR': 'ERR', 'OLCI_L1_EFR': 'EFR', 'OLCI_L2_WRR': 'WRR', 'OLCI_L2_WFR': 'WFR',
                    'SLSTR_L1_RBT': 'RBT', 'SLSTR_L2_WCT': 'WCT', 'SLSTR_L2_WST': 'WST',
                    'MSI_L1C': 'L1C', 'MSI_L2A': 'L2A'}  # copernicus 'MSI_L2A': 'S2MSI2A'

    def __init__(self, credentials=None):
        self.username = credentials['EARTHDATA']['username'] if credentials else ''
        self.password = credentials['EARTHDATA']['password'] if credentials else ''

    @staticmethod
    def get_bounding_box(poi, bounding_box_size=60):
        n = poi.lat + bounding_box_size / 60
        n = n if n < 90 else 90
        s = poi.lat - bounding_box_size / 60
        s = s if s > -90 else -90

        lon_bbs = bounding_box_size / 60 / (math.cos(poi.lat * math.pi / 180))
        w = poi.lon - lon_bbs
        w = w if w > -180 else w + 360
        e = poi.lon + lon_bbs
        e = e if e < 180 else e - 360

        return w, s, e, n

    @staticmethod
    def get_datetime_window(poi, delta=12):  # set_query_string
        # delta = kwargs['delta'] if 'delta' in kwargs.keys() else 12
        day_st = poi['dt'] - timedelta(hours=delta)
        day_end = poi['dt'] + timedelta(hours=delta)
        return day_st, day_end

    def get_image_list(self, pois, instrument, level='L2', bounding_box_size=60, **kwargs):
        raise NotImplementedError('Method not implemented in parent class.')

    def request_platform(self, s, url, *args, **kwargs):
        # modify header to hide requests query and mimic web browser
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36'
                                 ' (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}
        s.auth = (self.username, self.password)
        r1 = s.request('get', url)
        r = s.get(r1.url, auth=(self.username, self.password), stream=True, timeout=900, headers=headers)
        return r

    def download_images(self, image_names, urls):
        # Login to Earth Data and Download image
        if not urls and not image_names:
            if verbose:
                print('No image to download.')
            return False
        for image_name, url in zip(image_names, urls):
            if os.path.isfile(image_name):
                if verbose:
                    print('Skip ' + image_name)
            else:
                for j in range(self.MAX_RETRIES):
                    try:
                        # Open session
                        with requests.Session() as s:
                            handle = open('tmp_' + image_name, "wb")
                            r = self.request_platform(s, url, image_name='tmp_' + image_name)
                            sleep(5)
                            r.raise_for_status()
                            if verbose:
                                print('Downloading ' + image_name)
                            with open('tmp_' + image_name, "ab") as handle:
                                for chunk in r.iter_content(chunk_size=16 * 1024):
                                    if chunk:
                                        handle.write(chunk)
                            handle.close()
                            os.rename('tmp_' + image_name, image_name)
                            break
                    except requests.exceptions.RequestException as e:
                        handle.close()
                        print(f"{e}\n\tAttempt [{j + 2}/{self.MAX_RETRIES}] reconnection ...")
                    except socket.timeout:
                        handle.close()
                        print(
                            f"Connetion lost: download failed\n\tAttempt [{j + 2}/{self.MAX_RETRIES}] reconnection ...")
                    if j + 2 == self.MAX_RETRIES:
                        return False
                    print(f'Retrying in {self.WAIT_SECONDS} seconds')
                    sleep(self.WAIT_SECONDS)
                else:
                    print('%d All connection attempts failed, download aborted.\n'
                          '\t- Did you accept the End User License Agreement for this dataset ?\n'
                          '\t- Check login/username.\n'
                          '\t- Check image name/url in *.csv file\n'
                          '\t- Check for connection problems \n'
                          '\t- Check for blocked IP \n')
                    # for Earthdata download:
                    #   + check https://oceancolor.gsfc.nasa.gov/forum/oceancolor/topic_show.pl?tid=6447
                    #   + connection_problems@oceancolor.gsfc.nasa.gov
                    return False
        return True


class PlatformCOPERNICUS(Platform):
    NAME = 'Copernicus'
    URL_SEARCH = 'https://scihub.copernicus.eu/dhus/search?q='

    def __init__(self, credentials=None):
        super().__init__(credentials)
        raise DeprecationWarning('Platform COPERNICUS is deprecated.')

    def get_image_list(self, pois, instrument, level='L1', bounding_box_size=60, time_window=12, **kwargs):
        # Set static query parameters
        # check which spatial resolution for OLCI, if not input choose lower resolution ERR
        if 'ERR' not in level and 'EFR' not in level and instrument == 'OLCI':
            level = level + '_EFR'
            timeliness = '%20AND%20timeliness:"Non%20Time%20Critical"'
        elif instrument != 'OLCI':  # delete EFR and ERR if mistakenly input for other sensors
            level = level.replace('EFR', '')
            level = level.replace('ERR', '')
            level = level.replace('_', '')
            timeliness = ''
        else:
            timeliness = ''
        product_type = instrument + '_' + level
        if product_type not in self.PRODUCT_TYPE:
            raise ValueError(f"Level {level} not supported for {instrument}.")
        sen = 'producttype:' + self.PRODUCT_TYPE[product_type]
        query_string = sen + '%20AND%20' + 'instrumentshortname:' + instrument + timeliness + '%20AND%20'
        # Add column to points of interest data frame
        pois['image_names'] = [[] for _ in range(len(pois))]
        pois['urls'] = [[] for _ in range(len(pois))]
        pois['prod_entity'] = [[] for _ in range(len(pois))]  # only for copernicus, to check online status & metadata
        for i, poi in pois.iterrows():
            if verbose:
                print(f"[{i + 1}/{len(pois)}] Querying {self.NAME} {instrument} {level} {poi.id} "
                      f"{poi['dt']} {poi.lat:.5f} {poi.lon:.5f}")
            # Get Bounding Box around point of interest and time window
            w, s, e, n = self.get_bounding_box(poi, bounding_box_size)
            day_st, day_end = self.get_datetime_window(poi, time_window)
            # Build Query
            query = self.URL_SEARCH + query_string + 'beginposition:[' + \
                    day_st.strftime("%Y-%m-%dT%H:%M:%S.000Z") + '%20TO%20' + \
                    day_end.strftime("%Y-%m-%dT%H:%M:%S.000Z") + ']%20AND%20' + \
                    'footprint:"Intersects(POLYGON((' + w + '%20' + s + ',' + e + '%20' + s + \
                    ',' + e + '%20' + n + ',' + w + '%20' + n + ',' + w + '%20' + s + ')))"&rows=100'
            r = requests.get(query, auth=HTTPBasicAuth(self.username, self.password))
            if i == 0 and 'Full authentication is required to access this resource' in r.text:
                raise ValueError('Unable to login to Copernicus, check username/password')
            # extract image name from response
            imlistraw = re.findall(r'<entry>\n<title>(.*?)</title>\n<', r.text)
            # extract url from response
            url_list = re.findall(r'\n<link href="(.*?)"/>\n<link rel="alternative"', r.text)
            # extract product meta data from response to check online status
            prod_meta = re.findall(r'\n<link rel="alternative" href="(.*?)"/>\n<link rel="icon"', r.text)
            # populate lists with image name and url
            pois.at[i, 'image_names'] = [s + '.zip' for s in imlistraw]
            pois.at[i, 'urls'] = url_list
            pois.at[i, 'prod_entity'] = prod_meta
        return pois

    def request_platform(self, s, url, *args, **kwargs):
        image_name = args[0] if args else kwargs['image_name'] if 'image_name' in kwargs.keys() else None
        if image_name is None:
            raise ValueError('Missing argument image_name')
        headers = {'Range': 'bytes=' + str(os.stat(image_name).st_size) + '-'}
        r = s.get(url, auth=(self.username, self.password), stream=True, timeout=900, headers=headers)
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
        return r


class PlatformCREODIAS(Platform):
    NAME = 'CREODIAS'
    URL_SEARCH = 'https://finder.creodias.eu/resto/api/collections/'
    URL_GET_FILE = 'https://zipper.creodias.eu/download'
    URL_AUTH = 'https://auth.creodias.eu/auth/realms/DIAS/protocol/openid-connect/token'
    INSTRUMENT_FILE_ID = {'SeaWiFS': 'S', 'MODIS-Aqua': 'A', 'MODIS-Terra': 'T', 'OCTS': 'O', 'CZCS': 'C', 'GOCI': 'G',
                          'MERIS': 'M', 'VIIRSN': 'V', 'VIIRSJ1': 'V', 'HICO': 'H', 'OLCI': 'Sentinel3',
                          'SLSTR': 'Sentinel3', 'MSI': 'Sentinel2'}
    LEVEL = {'L1': 'LEVEL1', 'L2': 'LEVEL2', 'L1C': 'LEVEL1C', 'L2A': 'LEVEL2A'}

    def __init__(self, credentials=None):
        self.username = credentials['CREODIAS']['username'] if credentials else ''
        self.password = credentials['CREODIAS']['password'] if credentials else ''

    def get_image_list(self, pois, instrument, level='L1C', bounding_box_size=60, time_window=12, **kwargs):
        # Set static query parameters
        # https://finder.creodias.eu/resto/api2/collections/Sentinel2/search.json?instrument=MSI&productType=L2A&processingLevel=LEVEL2A
        if instrument == 'SLSTR':
            level = 'L1_RBT' if level == 'L1' else level
            level = 'L2_WST' if level == 'L2' else level
            if level not in ['L1_RBT', 'L2_WST', 'L2_WCT']:
                raise ValueError(f"Level {level} not supported for {instrument}.")
            product_type = f'{instrument}_{level}'
            level = level.split('_')[0]
        elif instrument == 'OLCI':
            level = 'L1_EFR' if level == 'L1' else level
            level = 'L2_WFR' if level == 'L2' else level
            if level not in ['L1_EFR', 'L1_ERR', 'L2_WFR', 'L2_WRR']:
                raise ValueError(f"Level {level} not supported for {instrument}.")
            product_type = f'{instrument}_{level}'
            level = level.split('_')[0]
        elif instrument == 'MSI':
            product_type = f'{instrument}_{level}'
        else:
            product_type = f'{instrument}'
        # Check input
        if instrument not in self.INSTRUMENT_FILE_ID or instrument not in self.INSTRUMENT_QUERY_ID:
            raise ValueError(f"Instrument {instrument} not supported.")
        if product_type not in self.PRODUCT_TYPE or level not in self.LEVEL:
            raise ValueError(f"Level {level} not supported for {instrument}.")
        url = self.URL_SEARCH + self.INSTRUMENT_FILE_ID[instrument] + '/search.json'
        instrument_params = dict(instrument=self.INSTRUMENT_QUERY_ID[instrument],
                                 productType=self.PRODUCT_TYPE[product_type],
                                 processingLevel=self.LEVEL[level])
        # Add column to points of interest data frame
        pois['image_names'] = [[] for _ in range(len(pois))]
        pois['urls'] = [[] for _ in range(len(pois))]
        for i, poi in pois.iterrows():
            if verbose:
                print(f"[{i + 1}/{len(pois)}] Querying {self.NAME} {instrument} {level} "
                      f"{poi.id} {poi['dt']} {poi.lat:.5f} {poi.lon:.5f}")
            w, s, e, n = self.get_bounding_box(poi, bounding_box_size)
            day_st, day_end = self.get_datetime_window(poi, time_window)
            params = dict(**instrument_params, box=f'{w:.5f},{s:.5f},{e:.5f},{n:.5f}',
                          startDate=day_st.strftime("%Y-%m-%d"), completionDate=day_end.strftime("%Y-%m-%d"))
            r = requests.get(url, params=params).json()
            pois.at[i, 'image_names'] = [i['properties']['title'] + '.zip' for i in r['features']]
            pois.at[i, 'urls'] = [i['properties']['services']['download']['url'] for i in r['features']]
        return pois

    def get_access_token(self):
        """
        Log in CREODIAS to get access token
        :return: access_token
        """
        login_data = {'client_id': 'CLOUDFERRO_PUBLIC', 'grant_type': 'password',
                      'username': self.username, 'password': self.password}
        response = requests.post(self.URL_AUTH, data=login_data).json()
        if 'access_token' not in response:
            raise RuntimeError(f"Unable to get access token.\n{response}")
        # Wait for access token to be valid
        sleep(5)
        return response['access_token']

    def request_platform(self, s, url, *args, **kwargs):
        image_name = args[0] if args else kwargs['image_name'] if 'image_name' in kwargs.keys() else None
        if image_name is None:
            raise ValueError('Missing argument image_name')
        access_token = args[1] if len(args) > 1 else kwargs['access_token'] if 'access_token' in kwargs.keys() else None
        if access_token is None:
            raise ValueError('Missing argument access_token')
        headers = {'Range': f'bytes={os.stat(image_name).st_size}-'}
        r = s.get(url, params=dict(token=access_token), stream=True, timeout=900, headers=headers)
        if r.status_code != 200 and r.status_code != 206:
            if r.text == 'Expired signature!':
                print('Login expired, reconnection ...')
                # get login key to include it into url
                access_token = self.get_access_token()
                r = s.get(url, params=dict(token=access_token), stream=True, timeout=900, headers=headers)
            else:
                print(r.status_code)
                print(r.text)
                print('Unable to download from https://auth.creodias.eu/\n'
                      '\t- Check login/username\n'
                      '\t- Invalid image name?')
        return r, access_token

    def download_images(self, image_names, urls):
        """
        Login to platform and download each image if not on disk
        :param image_names:
        :param urls:
        :return:
        """
        if not urls and not image_names:
            if verbose:
                print('No image to download.')
            return False
        access_token = self.get_access_token()
        # Loop through each image
        for image_name, url in zip(image_names, urls):
            if os.path.isfile(image_name):
                if verbose:
                    print('Skip ' + image_name)
            else:
                for j in range(self.MAX_RETRIES):
                    try:
                        # Open session
                        with requests.Session() as s:
                            handle = open('tmp_' + image_name, "wb")
                            r, access_token = self.request_platform(s, url, 'tmp_' + image_name, access_token)
                            r.raise_for_status()
                            expected_length = int(r.headers.get('Content-Length'))
                            # complete the file even if connection is cut while downloading and file is incomplete
                            while os.stat('tmp_' + image_name).st_size < expected_length:
                                r, access_token = self.request_platform(s, url, 'tmp_' + image_name, access_token)
                                r.raise_for_status()
                                trump_shutup = 0
                                with open('tmp_' + image_name, "ab") as handle:
                                    for chunk in r.iter_content(chunk_size=16 * 1024):
                                        if chunk:
                                            handle.write(chunk)
                                            if verbose:
                                                biden_president = round(
                                                    float(os.stat('tmp_' + image_name).st_size) / expected_length * 100,
                                                    -1)
                                                if biden_president > trump_shutup:
                                                    sys.stdout.write(
                                                        f"\rDownloading {image_name}\t\t{biden_president:.0f}%")
                                                    trump_shutup = biden_president
                                if handle.closed:
                                    handle = open('tmp_' + image_name, "ab")
                                handle.flush()
                            actual_length = os.stat('tmp_' + image_name).st_size
                            if actual_length < expected_length:
                                raise IOError(f'incomplete read ({actual_length} bytes read, '
                                              f'{expected_length - actual_length} more expected)')
                            handle.close()
                            os.rename('tmp_' + image_name, image_name)
                            sys.stdout.write('\n')  # Needed after Downloading...
                            break
                    except requests.exceptions.RequestException as e:
                        handle.close()
                        print(f"{e}\n\tAttempt [{j + 2}/{self.MAX_RETRIES}] reconnection ...")
                    except socket.timeout:
                        handle.close()
                        print(
                            f"Connetion lost: download failed\n\tAttempt [{j + 2}/{self.MAX_RETRIES}] reconnection ...")
                    if j + 2 == self.MAX_RETRIES:
                        return False
                    print(f'Retrying in {self.WAIT_SECONDS} seconds')
                    sleep(self.WAIT_SECONDS)
                else:
                    print('All connection attempts failed, download aborted.\n'
                          '\t- Did you accept the End User License Agreement for this dataset ?\n'
                          '\t- Check login/username.\n'
                          '\t- Check image name/url in *.csv file\n'
                          '\t- Check for connection problems \n'
                          '\t- Check for blocked IP \n')
                    # for Earthdata download:
                    #   + check https://oceancolor.gsfc.nasa.gov/forum/oceancolor/topic_show.pl?tid=6447
                    #   + connection_problems@oceancolor.gsfc.nasa.gov
                    return False
        return True


class PlatformCMR(Platform):
    NAME = 'CMR'
    URL_SEARCH = 'https://cmr.earthdata.nasa.gov/search/granules.json'
    URL_GET_FILE = 'https://oceandata.sci.gsfc.nasa.gov/cmr/getfile/'
    INSTRUMENT_NAME = {'SeaWiFS': 'SEAWIFS', 'MODIS-Aqua': 'MODISA', 'MODIS-Terra': 'MODIST',
                       'OCTS': 'OCTS', 'CZCS': 'CZCS', 'VIIRSN': 'VIIRSN', 'VIIRSJ1': 'VIIRSJ1', 'GOCI': 'GOCI'}

    def get_image_list(self, pois, instrument, level='L2', product=None, bounding_box_size=60, time_window=12,
                       l3_resolution=None, l3_binning_period=None, **kwargs):
        # https://cmr.earthdata.nasa.gov/search/granules.json?provider=OB_DAAC&short_name=MODISA_L2_OC&temporal=2016-08-21T00:00:01Z,2016-08-22T00:00:01Z&page_size=2000&page_num=1
        # https://cmr.earthdata.nasa.gov/search/granules.json?provider=OB_DAAC&short_name=MODISA_L1&temporal=2020-08-16T00:00:01Z,2020-08-17T00:00:01Z&page_size=2000&page_num=1
        # if level not in ['L2', 'L3m']:
        #     raise ValueError(f"Level {level} not supported by platform {self.NAME}.")
        # Get query constants
        if product is None:
            if 'L3' in level:
                product = 'CHL'  # POC
            elif level == 'L2':
                product = 'OC'
        if 'L1' in level:
            short_name = f'{self.INSTRUMENT_NAME[instrument]}_{level[0:2]}'
        else:  # GOCI at level 1B uses this short_name
            short_name = f'{self.INSTRUMENT_NAME[instrument]}_{level}_{product}'
        # Add column to points of interest data frame
        pois['image_names'] = [[] for _ in range(len(pois))]
        pois['urls'] = [[] for _ in range(len(pois))]
        for i, poi in pois.iterrows():
            if verbose:
                print(f"[{i + 1}/{len(pois)}] Querying {self.NAME} {instrument} {level} "
                      f"{poi.id} {poi['dt']} {poi.lat:.5f} {poi.lon:.5f}")
            # Get Bounding Box around point of interest and time window
            w, s, e, n = self.get_bounding_box(poi, bounding_box_size)
            day_st, day_end = self.get_datetime_window(poi, time_window)
            # Build Query
            params = dict(provider='OB_DAAC', page_size=2000, page_num=1, short_name=short_name,
                          bounding_box=f'{w:.5f},{s:.5f},{e:.5f},{n:.5f}',
                          temporal=f"{day_st.isoformat()}Z,{day_end.isoformat()}Z")
            pois.at[i, 'image_names'], pois.at[i, 'urls'] = self._query_search(params)
            if datetime.utcnow() - day_st < timedelta(days=60):
                params['short_name'] += '_NRT'
                foo, bar = self._query_search(params)
                pois.at[i, 'image_names'] += foo
                pois.at[i, 'urls'] += bar
            # Further filter Level 3
            if level == 'L3m':
                idx2keep = []
                for k, img in enumerate(pois.at[i, 'image_names']):
                    if l3_resolution in img and l3_binning_period in img:
                        idx2keep.append(k)
                pois.at[i, 'image_names'] = [v for k, v in enumerate(pois.at[i, 'image_names']) if k in idx2keep]
                pois.at[i, 'urls'] = [v for k, v in enumerate(pois.at[i, 'urls']) if k in idx2keep]
            # Reformat VIIRS image name
            if instrument == 'VIIRSN' and product == 'SST':
                idx2keep = []
                for k, img in enumerate(pois.at[i, 'image_names']):
                    if "SNPP_VIIRS." in img:
                        idx2keep.append(k)
                pois.at[i, 'image_names'] = [v for k, v in enumerate(pois.at[i, 'image_names']) if k in idx2keep]
                pois.at[i, 'urls'] = [v for k, v in enumerate(pois.at[i, 'urls']) if k in idx2keep]
        return pois

    def _query_search(self, params):
        r = requests.get(self.URL_SEARCH, params=params)
        r.raise_for_status()
        result = r.json()
        image_names = [i['producer_granule_id'] for i in result['feed']['entry']]
        urls = [i['links'][0]['href'] for i in result['feed']['entry']]
        return image_names, urls


class PlatformOC(Platform):
    """
    Documentation of Ocean Color Data Format Specification:  https://oceancolor.gsfc.nasa.gov/products/
    """
    NAME = 'Ocean Color Level 1&2 Browser'
    URL_SEARCH = 'https://oceancolor.gsfc.nasa.gov/cgi/browse.pl'
    URL_GET_FILE = 'https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/'

    @staticmethod
    def get_datetime_window(poi, **kwargs):
        raise NotImplementedError('Method not available for OC Platform.')

    def get_image_list(self, pois, instrument, level='L2', product='OC', bounding_box_size=60, query_delay=1, **kwargs):
        # Set static query parameters
        instrument_params = dict(sen=self.INSTRUMENT_QUERY_ID[instrument],
                                 sub='level1or2list')
        if level in ['L2']:
            if product in ['OC', 'IOP']:
                instrument_params['dnm'] = 'D'
                instrument_params['prm'] = 'CHL'
            elif product in ['SST']:
                instrument_params['dnm'] = 'D@N'
                instrument_params['prm'] = 'SST'
            elif product in ['SST4']:
                instrument_params['dnm'] = 'N'
                instrument_params['prm'] = 'SST4'
            else:
                raise ValueError(f"Product {product} not supported by {instrument}.")
        elif level in ['GEO', 'L0', 'L1', 'L1A', 'L1B']:
            # Level 1A specify daily data only
            instrument_params['dnm'] = 'D'
            instrument_params['prm'] = 'TC'
        else:
            raise ValueError(f"Level {level} not supported by {instrument}.")
        # Add column to points of interest data frame
        pois['image_names'] = [[] for _ in range(len(pois))]
        pois['urls'] = [[] for _ in range(len(pois))]
        for i, poi in pois.iterrows():
            if verbose:
                print(f"[{i + 1}/{len(pois)}] Querying {self.NAME} {instrument} {level} "
                      f"{poi.id} {poi['dt']} {poi.lat:.5f} {poi.lon:.5f}")
            # Get Bounding Box around point of interest and day of matchup
            w, s, e, n = self.get_bounding_box(poi, bounding_box_size)
            day = (poi['dt'] - datetime(1970, 1, 1)).days
            # Build Query
            params = dict(**instrument_params, w=f'{w:.5f}', s=f'{s:.5f}', e=f'{e:.5f}', n=f'{n:.5f}',
                          per='DAY', day=f'{day}')
            r = requests.get(self.URL_SEARCH, params=params)
            # extract image name from response
            if 'href="https://oceandata.sci.gsfc.nasa.gov/ob/getfile/' in r.text:  # if one image
                if 'MERIS' in instrument:
                    if level == 'L1':
                        imlistraw = re.findall(r'href="https://oceandata.sci.gsfc.nasa.gov/ob/getfile/(.*?)">', r.text)
                    elif level == 'L2':
                        imlistraw = re.findall(r'href="https://oceandata.sci.gsfc.nasa.gov/echo/getfile/(.*?)">',
                                               r.text)
                    else:
                        raise ValueError(f"Level {level} not supported by MERIS.")
                else:
                    imlistraw = re.findall(r'href="https://oceandata.sci.gsfc.nasa.gov/ob/getfile/(.*?)">', r.text)
                    imlistraw = [x for x in imlistraw if level in x]
            else:  # if multiple images
                imlistraw = re.findall(r'title="(.*?)"\nwidth="70"', r.text)
                if instrument == 'MODIS-Aqua' or instrument == 'MODIS-Terra' and level == 'L1A':
                    # add missing extension when multiple reuslts
                    imlistraw = [s + '.bz2' for s in imlistraw]
                    # remove duplicates
                    imlistraw = list(dict.fromkeys(imlistraw))
            # append VIIRS GEO file names at the end of the list
            if 'VIIRS' in instrument and level == 'L1A':
                imlistraw = imlistraw + [sub.replace('L1A', 'GEO-M') for sub in imlistraw]
            # Delay next query (might get kicked by server otherwise)
            sleep(query_delay)
            pois.at[i, 'image_names'] = imlistraw
            pois.at[i, 'urls'] = [self.URL_GET_FILE + s for s in pois.at[i, 'image_names']]
        return pois


def read_dataset(filename):
    df = pd.read_csv(filename, header=None, parse_dates=[1])
    if 4 <= len(df.columns) <= 7:
        df.columns = ['id', 'dt', 'lat', 'lon', 'image_names', 'urls', 'prod_entity'][:len(df.columns)]
    else:
        raise ValueError('Invalid number of columns in file.')
    if 'image_names' in df.columns.to_list():
        df.dropna(subset=['image_names'], axis=0, inplace=True)
    return df


if __name__ == "__main__":
    from optparse import OptionParser
    from configparser import ConfigParser

    parser = OptionParser(usage="Usage: getOC.py [options] [filename]", version="getOC " + __version__)
    parser.add_option("-i", "--instrument", action="store", dest="instrument",
                      help="specify instrument, available options are: VIIRSJ1, VIIRSN, MODIS-Aqua, MODIS-Terra, "
                           "OCTS, CZCS, MERIS, HICO, SeaWiFS, OLCI, SLSTR, MSI (L1C and L2A < 12 month)")
    parser.add_option("-l", "--level", action="store", dest="level", default='L2',
                      help="specify processing level, available options are: GEO, L1*, L2*, L3m")
    # Level 2 specific option
    parser.add_option("-p", "--product", action="store", dest="product", default='OC',
                      help="specify product identifier (only for L2), available options are: OC, SST, and IOP, "
                           "not available for CREODIAS queries (OLCI, SLSTR, and MSI)")
    parser.add_option("-d", "--delay", action="store", dest="query_delay", type='float', default=1,
                      help="Delay between queries only needed to query L1L2_browser")
    # Level 3 specific options
    parser.add_option("-b", "--binning-period", action="store", dest="binning_period", default='8D',
                      help="specify binning period (only for L3), available options are: DAY, 8D, MO, and YR")
    parser.add_option("--res", "--spatial-resolution", action="store", dest="sresol", default='4km',
                      help="specify spatial resolution (only for L3), available options are: 4km, 9km")
    # credential specific options
    parser.add_option("-u", "--username", action="store", dest="username", default=None,
                      help="specify username to login Creodias (OLCI / SLSTR / MSI) or EarthData (any other sensor). "
                           "Note needed if credentials.ini is present in working directory.")
    # Other options
    parser.add_option("-w", "--write-image-links", action="store_true", dest="write_image_links", default=False,
                      help="Write query results image names and corresponding urls into csv file.")
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

    # Read list of points of interest to download
    filename = args[0]
    if options.read_image_list:
        filename = f'{os.path.splitext(filename)[0]}_{options.instrument}_{options.level}_{options.product}.csv'
    pois = read_dataset(filename)
    # Setup downloading platform
    if os.path.isfile('credentials.ini'):
        credentials = ConfigParser()
        credentials.read('credentials.ini')
        platform = get_platform(pois.dt.max(), options.instrument, options.level, credentials)
    else:
        platform = get_platform(pois.dt.max(), options.instrument, options.level)
        platform.username = options.username
        platform.password = getpass(prompt=f'{platform.NAME} Password: ', stream=None)
    # Query image list if necessary
    if 'image_names' not in pois.columns.to_list() or 'urls' not in pois.columns.to_list():
        # Query image list
        pois = platform.get_image_list(pois, options.instrument, options.level, product=options.product,
                                       bounding_box_size=options.bounding_box_sz, query_delay=options.query_delay,
                                       l3_resolution=options.sresol, l3_binning_period=options.binning_period)
    else:
        # Reformat image list
        pois.image_names = pois.image_names.apply(lambda r: r.split(';'))
        pois.urls = pois.urls.apply(lambda r: r.split(';'))
        if 'prod_entity' in pois.columns.to_list():
            pois.prod_entity = pois.prod_entity.apply(lambda r: r.split(';'))
    # Write list of images with urls to csv
    if options.write_image_links:
        foo = pois.copy()
        foo.image_names = foo.image_names.apply(lambda r: ';'.join(r))
        foo.urls = foo.urls.apply(lambda r: ';'.join(r))
        if 'prod_entity' in foo.columns.to_list():
            foo.prod_entity = foo.prod_entity.apply(lambda r: ';'.join(r))
        foo.to_csv(f'{os.path.splitext(filename)[0]}_{options.instrument}_{options.level}_{options.product}.csv',
                   date_format='%Y/%m/%d %H:%M:%S', header=False, index=False, float_format='%.5f')
    # Flatten lists
    image_names = [item for sublist in pois.image_names.to_list() for item in sublist]
    urls = [item for sublist in pois.urls.to_list() for item in sublist]
    if platform.download_images(image_names, urls) and verbose:
        print('Download completed')
