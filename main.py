import geopandas
import pandas
import matplotlib.pyplot as plt
from cartopy import crs as ccrs
from shapely.wkt import loads as load_wkt
import fiona
import numpy
import shapely.geometry as geom
from shapely.geometry import Point, LineString
import warnings
warnings.filterwarnings('ignore')
plt.style.use('bmh')

import PySimpleGUI as sg


#declaring variables

layout = [[sg.Text('Supplemental Assigment', size=(30, 1), font=("Helvetica", 25), text_color='blue')],
	[sg.Text('Paste your data set full url here')],
	[sg.InputText()],[sg.Submit('Upload', button_color=('white', 'green')), sg.Cancel('Reset')]
	
]

data_source = 'http://mf2.dit.ie:8080/geoserver/topp/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=topp:states&maxFeatures=50&outputFormat=json'

##Reading the dataset from server
states =geopandas.read_file(data_source)

states.plot(figsize = (10,10), alpha=.7, edgecolor='k')
# plt.show()
plt.savefig('Figure 1 US Population.png')
##Print the head of states with unique names
# print(states.head())
# print(states['STATE_NAME'])

# Plot Union of polygons
ax = states.plot(figsize = (10,10), alpha=.7, edgecolor='k')

##Compute the Centroid of the polygon
states_centroids = states.centroid
states_centroids.plot(ax=ax, color='red')
# plt.show()
plt.savefig('Figure 2 CentroidsPolygon1.png')
# print(states_centroids.keys())
print(states_centroids.geometry.name)
## Option two
states['centroid_column'] = states.centroid
states = states.set_geometry('centroid_column')
states.plot(color='black')
# plt.show()
plt.savefig('Figure2 CentroidsPolygon2.png')

##Extract the points that lie with the single polygon
cents=states.centroid
centroid_values = cents.to_json
# print(centroid_values)

##distance between the centroid of the single polygon
lines = geopandas.GeoSeries(states_centroids[10])
n = 10
points = geopandas.GeoSeries([geom.Point(x,y) for x, y in numpy.random.uniform(0,3, (n,2))])
dis_points = geopandas.GeoDataFrame(numpy.array([points, numpy.random.randn(n)]).T)
dis_points.columns = ['Geometry', 'Property12']
dis_points.head(3)
p_coords = dis_points['Geometry']
points.plot()
plt.savefig('Figure 3 Distance between Centroids')
lines.plot()
plt.savefig('Figure 4 joining lines between centroids')

min_dist = numpy.empty(n)
for i, point in enumerate(points):
    min_dist[i] = numpy.min([point.distance(line) for line in lines])
dis_points['min_dist_to_lines'] = min_dist

# print(dis_points)

##convex hull and centroid for the extracted points
# hulls = dis_points.convex_hull
# print(hulls)
# hulls.plot(ax=states_centroids.plot())
# plt.show()
plt.savefig('Figure 5 convexHull.png')

##Create a representation of the line joining the two centroids
lines.plot()
plt.savefig('Figure 6 Join line.png')
##Geocode both centroids and add their names to the appropriate point as 
states_centroids["x"] = states.centroid.x
states_centroids["y"] = states.centroid.y

## save the GeoDataFrame
# states.to_file("states.shp")
# states.to_file("states.geojson", driver='GeoJSON')
# or directly

event, values  = sg.Window('Geopandas Polygon', layout, auto_size_text=True, default_element_size=(40, 1)).Read()