from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt
api = SentinelAPI('user name goes here', 'password goes here', 'https://scihub.copernicus.eu/dhus')

# download single scene by known product id
api.download("Sentinel product id goes here")