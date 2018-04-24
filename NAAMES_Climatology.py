#!/usr/bin/env python
# Download Level 3 SMI files needed to build NAAMES Climatology
# created: April 24, 2018

from getOC import get_image_list_from_search_api, download
import os

path2data = '/Users/nils/Data/NAAMES/climatology/nc/'
geophysical_product = 'GSM_chl_gsm'
binning_period = '8D'
binning_area = '9km'
sensors = ['MODIS-Aqua', 'VIIRS', 'SeaWiFS']
first_years = [2002, 2011, 1997]
last_years = [2018, 2018, 2010]

for sensor, first_year, last_year in zip(sensors, first_years, last_years):
    print('=================')
    print('Downloading ' + sensor)
    print('=================')
    dir_data = os.path.join(path2data,
                            sensor + '_L3SMI_' + binning_period + '_' + geophysical_product + '_' + binning_area)
    if not os.path.exists(dir_data):
        os.makedirs(dir_data)
    os.chdir(dir_data)
    for y in range(first_year, last_year):
        print('%s %d' % (sensor, y))
        img_list = get_image_list_from_search_api(sensor, '%d0101' % y, '%d1231' % y, binning_period,
                                                  geophysical_product + '_' + binning_area, write_image_list=False)
        download(img_list)
    print(sensor + ' DONE\n')
