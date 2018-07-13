import pandas as pd
import os
import matplotlib.pyplot as plt
from gmplot import gmplot
import pandas as pd
import io 
filename = "my_map.html"
data = pd.read_json('/Users/amarapalli.u/work/hacks/Hackday9-legion/scraped/profile/muk.soumi/*', lines=True)
filtered = data[data['loc_id']!=0]
last_day_nona = filtered.dropna()
# last_day_nona = last_day_nona.encode('ascii',errors='ignore')
# location_info = [info_box_template.format(**elem) for i,elem in last_day_nona.to_dict('index').items()]
lat=[]
lon=[]
gmap = gmplot.GoogleMapPlotter(0, 0, 10)
for elem in last_day_nona.itertuples():
	gmap.marker(elem.loc_lat, elem.loc_lon, 'cornflowerblue', title=elem.caption.encode('ascii',errors='ignore'))
try:
	os.remove(filename)
except Exception as e:
	pass

gmap.draw(filename)

