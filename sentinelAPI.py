from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt
from datetime import date
import os 

ws = "/content/sentinel2_utility/raw"
os.chdir(ws)

api = SentinelAPI('username goes here', 'password goes here', 'https://scihub.copernicus.eu/dhus')


footprint = "/content/sentinel2_utility/vector_data/footprints/overTbeinya.json" # must be GeoJSON
start_date = date(2018, 5, 19)
end_date = date(2018, 5, 29)
platform_name = 'Sentinel-2'
cloud_cover_percentage = '[0 TO 30]'

def getSentinelData(productID="",  footprint=footprint, begin=start_date, end=end_date, platform=platform_name , clouds=cloud_cover_percentage):
  if productID:
    api.download(productID)
    return
  fp = geojson_to_wkt(read_geojson(footprint))
  products = api.query(footprint, date=(begin, end), platformname=platform, cloudcoverpercentage = clouds)
  api.download_all(products)
  return

getSentinelData(productID="") # don't pass parameters when using querry
                              # in case you want to download a certain product just pass it's ID in the provided parameter

