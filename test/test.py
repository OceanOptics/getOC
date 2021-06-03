import getOC
import os
import configparser

TEST_WK_DIR = 'images'
TEST_FILES = {'CZCS': '../test_CZCS.csv', 'GOCI': '../test_GOCI.csv', 'OCTS': '../test_OCTS.csv',
              'MERIS-RR': '../test_MERIS.csv', 'MERIS-FRS': '../test_MERIS.csv', 'SeaWiFS': '../test_SeaWiFS.csv',
              'other': '../test.csv'}
TEST_INSTRUMENTS = {'CZCS': ['L1A', 'L2', 'L3m'],  # OK
                    'GOCI': ['L1B', 'L2'],  # OK
                    'MERIS-RR': ['L1', 'L2'],  # OK
                    'MERIS-FRS': ['L1', 'L2'],  # OK
                    'MODIS-Aqua': ['L1A', 'L2', 'L3m'],  # OK
                    'MODIS-Terra': ['L1A', 'L2', 'L3m'],  # OK
                    'MSI': ['L1C', 'L2A'],  # L1C OK but L2A NOTHING
                    'OCTS': ['L1A', 'L2'],  # L1A OK (OCL12B), L2 (CMR) dubious
                    'OLCI': ['L1_EFR', 'L1_ERR', 'L2_WFR', 'L2_WRR'],  # OK
                    'SeaWiFS': ['L1A', 'L2', 'L3m'],  # L1A OK (OCL12B), L2 (CMR) dubious, L3m fails
                    'SLSTR': ['L1', 'L2_WST', 'L2_WCT'],  # L1 & L2_WST OK, L2_WCT fails
                    'VIIRSN': ['L1A', 'L2', 'L3m'],  # OK
                    'VIIRSJ1': ['L1A', 'L2', 'L3m']  # OK
                    }

# Load credentials
credentials = configparser.ConfigParser()
credentials.read('../credentials.ini')

# Update getOC parameters
getOC.verbose = True
getOC.Platform.WAIT_SECONDS = 5

# Change download direcoty (working directory)
if not os.path.exists(TEST_WK_DIR):
    os.makedirs(TEST_WK_DIR)
os.chdir(TEST_WK_DIR)

for instrument, levels in TEST_INSTRUMENTS.items():
    # Get points of interest (different to take into account specific temporal and spatial range of instruments)
    if instrument in TEST_FILES.keys():
        pois = getOC.read_dataset(TEST_FILES[instrument])
    else:
        pois = getOC.read_dataset(TEST_FILES['other'])
    for level in levels:
        print(f"\n=== {instrument} {level} ===")
        # Setup downloading platform
        platform = getOC.get_platform(pois.dt.max(), instrument, level, credentials)
        # Query image list
        pois = platform.get_image_list(pois, instrument, level,  # product=product,
                                       bounding_box_size=60,  # query_delay=options.query_delay,
                                       l3_resolution='4km', l3_binning_period='8D')
        # Download images
        image_names = [item for sublist in pois.image_names.to_list() for item in sublist]
        urls = [item for sublist in pois.urls.to_list() for item in sublist]
        if platform.download_images(image_names, urls) and getOC.verbose:
            print('Download completed')
