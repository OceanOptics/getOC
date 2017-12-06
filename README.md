getOC
=====

_Bulk download Ocean Color images._

This utility is made to easily bulk download Ocean Color images from [NASA Ocean Data](https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/) API. Provide a list of positions and dates in a csv file (ex: test.csv), select an instrument (MODIS, VIIRS, OLCI), a processing level (L1A or L2), and a product (OC, IOP, or SST for L2 only) and the utility will get the images. Note that a strong internet connection is recommended.

    python -Om getOC -i <instrument> -l <level> -p <product> <filename>

If you only need to download images in a given time frame without specifying a position, the [File Search](https://oceandata.sci.gsfc.nasa.gov/api/file_search) utility from NASA might be a better tool. The NASA utility also provides a few wget examples on this [Ocean Color Forum Post](https://oceancolor.gsfc.nasa.gov/forum/oceancolor/topic_show.pl?pid=12520).

More informations in the header of getOC.py.
