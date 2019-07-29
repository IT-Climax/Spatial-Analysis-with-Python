
from collections import OrderedDict
import fiona
from fiona.crs import from_epsg
from shapely.geometry import mapping, shape
from shapely.ops import cascaded_union
import matplotlib.pyplot as plt
import geopy as my_geocoder  # fixed geocoder using geopy
import json
import geopandas as gp

# Directory in local project to hold data. Note the '.'. This indicates that this directory is temporary and/or
# sacrificial.

def geojson_to_shp(geojson, shapefile):
    """
    Takes a GeoJSON-like data structure and writes it to storage as a Shapefile

    :param geojson: Incoming GeoJSON
    :param shapefile: Full path to required shapefile
    :return: Normally None except when there is an error.
    """
    try:
        # Before we can create a shapefile we need to make a 'schema' which describes the structure of the required
        # shapefile. For this we need to know its CRS, its geometry type and the types of any elements in the properties
        # list.

        crs_code = geojson["crs"]["properties"]["code"]

        # To figure out the required data types in properties we get the values in the first feature and make
        # assumptions based on this. 'my_schema' will hold the key and the value will be the TYPE (str, int, float
        # etc.) of the data value.
        my_schema = OrderedDict()

        for k, v in geojson["features"][0]["properties"].items():
            if str(type(v)).split("'")[1] in ("str", "int", "float"):
                my_schema[k] = str(type(v)).split("'")[1]

        # We can now open the output shapefile as we have all the information that we need to describe it.
        with fiona.Env():
            with fiona.open(
                    shapefile, "w", driver="ESRI Shapefile",
                    schema={"geometry": geojson["features"][0]["geometry"]["type"], "properties": my_schema},
                    crs=from_epsg(crs_code)) as fh:
                # We can now take our criteria-matching list of features and add them to the shapefile.
                for feature in geojson["features"]:
                    # We set up a skeleton feature and selectivelt add properties to it (see next).
                    outgoing_feature = {"type": "Feature", "id": feature["id"], "geometry": feature["geometry"],
                                        "properties": {}}
                    for k, v in feature["properties"].items():
                        # We only take property items where the key is alraedy in our schema, we ignore anything else.
                        if k in my_schema:
                            outgoing_feature["properties"][k] = v
                    fh.write(outgoing_feature)


    except Exception as e:
        print(e)
        quit()

def make_centroid(geojson):
    """
    Takes a GeoJSON structure, finds its centroid, geocodes the centroid and returns a new GeoJSON stucture with the
    centroid details.

    :param geojson: GeoJSON structure
    :return: New geoJSON structure
    """
    try:
        # Make blank GeoJSON template with CRS filled in as this won't be different from the input
        centroid_geojson = {"type": "FeatureCollection", "features": [], "crs": geojson["crs"], "bbox": []}

        # Make a Shapely geometry object from a GeoJSON geometry object
        centroid_feature = shape(geojson["features"][0]["geometry"])

        # Get the centroid of the Shapely object
        centroid_point = centroid_feature.centroid

        # Geocode the Shapely centroid. We end up filtering the Geocoder result to get body only as we don't need the
        # rest of its output
        geocoded_point = my_geocoder.geocode_location("{}, {}".format(centroid_point.x, centroid_point.y),
                                                      int(geojson["crs"]["properties"]["code"]))
        geocoded_point = geocoded_point["body"]

        # Add a blank GeoJSON feature to my GeoJSON 'template'
        centroid_geojson["features"].append({"type": "feature", "id": 0, "geometry": None, "properties": OrderedDict()})

        # Convert the Shapely centroid to GeoJSON using 'mapping' and stoire this in the GeoJSON geometry
        centroid_geojson["features"][0]["geometry"] = mapping(centroid_point)

        # Get the 'display_name' from the Geocoder result and store this as a GeoJSON property called 'address'
        centroid_geojson["features"][0]["properties"]["address"] = "{}".format(geocoded_point["result"]["display_name"])

        # Store the bounding box. As it's a point it will be the same as the point coordinates.
        centroid_geojson["bbox"] = centroid_point.x, centroid_point.y

        # Send back the completed GeoJSON structure
        return centroid_geojson
    except Exception as e:
        print(e)
        quit()

def merge_polys(geojson, filter_key="", filter_value=""):
    """
    takes a GeoJSON structure of (Multi)Polygons, finds specific features based on a filter key/value pair and returns a
    new GeoJSON structure with only the required features merged to one feature.

    :param geojson: Incoming GeoJSON structure
    :param filter_key: Property key such as countyname
    :param filter_value: Specific required value such as 'Dublin'
    :return: New GeoJSON structure containing the merged feature.
    """

    # List of features which meet the filter criteria
    my_features = []
    # List of geometries which meet the filter criteria. We use these in the Shapely geometry calculations.
    my_geometries = []

    # Make blank GeoJSON template with CRS filled in as this won't be different from the input
    merged_polys_geojson = {"type": "FeatureCollection", "features": [], "crs": geojson["crs"], "bbox": []}

    try:
        # Check each incoming feature to see if it matches the filter criteria and if so, store the feature and geometry
        # in separate lists. Note the use of 'shape' to convert the GeoJSON geometry to Shapely geometry.
        for feature in geojson["features"]:
            if filter_key in feature["properties"] and filter_value in feature["properties"][filter_key]:
                my_features.append(feature)
                my_geometries.append(shape(feature["geometry"]))

        # Merge the geometries in the filter-matching criteria list
        merged_geometry = cascaded_union(my_geometries)

        merged_polys_geojson["bbox"] = merged_geometry.bounds

        # Make an 'ordered dictionary' to store the required properties, in this case filter key and value
        merged_properties = OrderedDict()
        merged_properties[filter_key] = filter_value

        # Add any numeric totals
        for feature in my_features:
            for k,v in feature["properties"].items():
                if type(v) == float:
                    if k in merged_properties:
                        merged_properties[k] += v
                    else:
                        merged_properties[k] = v

        # make the finished feature (note that 'mapping' below converts Shapely geometry to GeoJSON structure).
        merged_feature = {
            "type": "feature",
            "id": 0,
            "geometry": mapping(merged_geometry),
            "properties": merged_properties
        }

        merged_polys_geojson["features"].append(merged_feature)

        # Return completed GeoJSON structure
        return merged_polys_geojson


    except Exception as e:
        print(e)
        quit()

def geojson_to_shp(geojson, shapefile):
    """
    Takes a GeoJSON-like data structure and writes it to storage as a Shapefile

    :param geojson: Incoming GeoJSON
    :param shapefile: Full path to required shapefile
    :return: Normally None except when there is an error.
    """
    try:
        # Before we can create a shapefile we need to make a 'schema' which describes the structure of the required
        # shapefile. For this we need to know its CRS, its geometry type and the types of any elements in the properties
        # list.

        crs_code = geojson["crs"]["properties"]["code"]

        # To figure out the required data types in properties we get the values in the first feature and make
        # assumptions based on this. 'my_schema' will hold the key and the value will be the TYPE (str, int, float
        # etc.) of the data value.
        my_schema = OrderedDict()

        for k, v in geojson["features"][0]["properties"].items():
            if str(type(v)).split("'")[1] in ("str", "int", "float"):
                my_schema[k] = str(type(v)).split("'")[1]

        # We can now open the output shapefile as we have all the information that we need to describe it.
        with fiona.Env():
            with fiona.open(
                    shapefile, "w", driver="ESRI Shapefile",
                    schema={"geometry": geojson["features"][0]["geometry"]["type"], "properties": my_schema},
                    crs=from_epsg(crs_code)) as fh:
                # We can now take our criteria-matching list of features and add them to the shapefile.
                for feature in geojson["features"]:
                    # We set up a skeleton feature and selectivelt add properties to it (see next).
                    outgoing_feature = {"type": "Feature", "id": feature["id"], "geometry": feature["geometry"],
                                        "properties": {}}
                    for k, v in feature["properties"].items():
                        # We only take property items where the key is alraedy in our schema, we ignore anything else.
                        if k in my_schema:
                            outgoing_feature["properties"][k] = v
                    fh.write(outgoing_feature)


    except Exception as e:
        print(e)
        quit()



# def original_geojson(geojson):

from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from tkinter import TclError
from tkinter import scrolledtext as st

class MyGUI:
    def __init__(self, my_parent):

        host_name = StringVar()
        layer_id = StringVar()
        srs_id = int()
        property_id = StringVar()
        geom_id = StringVar()
        fproperty_id = StringVar()
        fvalue_id1 = StringVar()
        fvalue_id2 = StringVar()

        PARAMS = {
            "host": host_name,
            "layer": layer_id,
            "srs_code": srs_id,
            "properties": [property_id],
            "geom_field": geom_id,
            "filter_property": fproperty_id,
            "filter_values": [fvalue_id1]
            # "filter_values": [self.fvalue_id1, self.fvalue_id2]
        }

        self.my_parent = my_parent

        self.my_parent.title("GIS Programming - Supplement 2019")

        my_parent.protocol("WM_DELETE", self.catch_destroy)

        self.frame1 = ttk.Frame(my_parent, padding=5, border=1)
        self.frame1.grid(row=0, column=0)

        self.tasks_frame = LabelFrame(self.frame1, padx=15, pady=15, text="Tasks")
        self.tasks_frame.grid(row=0, column=0, sticky=NW)

        Label(self.tasks_frame, text="1.", justify=LEFT).grid(row=0, column=0, sticky=W)
        Label(self.tasks_frame, text="Host Name", justify=LEFT).grid(row=0, column=1, sticky=W)
        Entry(self.tasks_frame, width=30, textvariable=host_name).grid(row=1, column=1, sticky=W)

        Label(self.tasks_frame, text="2.", justify=LEFT).grid(row=2, column=0, sticky=W)
        Label(self.tasks_frame, text="Layer", justify=LEFT).grid(row=2, column=1, sticky=W)
        Label(self.tasks_frame, text="Source Code", justify=LEFT).grid(row=2, column=2, sticky=W)
        Entry(self.tasks_frame, width=20, textvariable=layer_id).grid(row=3, column=1, sticky=W)
        Entry(self.tasks_frame, width=20, textvariable=srs_id).grid(row=3, column=2, sticky=W)

        Label(self.tasks_frame, text="3", justify=LEFT).grid(row=4, column=0, sticky=W)
        Label(self.tasks_frame, text="Properties", justify=LEFT).grid(row=4, column=1, sticky=W)
        Label(self.tasks_frame, text="Geometry field", justify=LEFT).grid(row=4, column=2, sticky=W)
        Entry(self.tasks_frame, width=20, textvariable=property_id).grid(row=5, column=1, sticky=W)
        Entry(self.tasks_frame, width=20, textvariable=geom_id).grid(row=5, column=2, sticky=W)

        Button(self.tasks_frame, text="Download Geojson File", command=self.download_geojson_file) \
            .grid(row=6, column=1, sticky=NW, pady=5)
        Button(self.tasks_frame, text="Plot Single Polygon", command=self.single_plot) \
            .grid(row=6, column=2, sticky=NW, pady=5)

        Label(self.tasks_frame, text="", justify=LEFT).grid(row=9, column=0, sticky=W)
        Label(self.tasks_frame, text="4", justify=LEFT).grid(row=11, column=0, sticky=W)
        Label(self.tasks_frame, text="Filter property Name", justify=LEFT).grid(row=11, column=1, sticky=W)
        Entry(self.tasks_frame, width=20, textvariable=fproperty_id).grid(row=12, column=1, sticky=W)
        Label(self.tasks_frame, text="5", justify=RIGHT).grid(row=13, column=0, sticky=W)
        Label(self.tasks_frame, text="Filter Value 1", justify=LEFT).grid(row=13, column=1, sticky=W)
        Label(self.tasks_frame, text="Filter Value 2", justify=LEFT).grid(row=13, column=2, sticky=W)
        Entry(self.tasks_frame, width=20, textvariable=fvalue_id1).grid(row=14, column=1, sticky=W)
        Entry(self.tasks_frame, width=20, textvariable=fvalue_id2).grid(row=14, column=2, sticky=W)

        Button(self.tasks_frame, text="Plot Centroid") \
            .grid(row=15, column=2, sticky=NW, pady=5)

        Label(self.tasks_frame, text="", justify=LEFT).grid(row=16, column=0, sticky=W)
        Label(self.tasks_frame, text="6.").grid(row=17, column=0, sticky=W)
        Button(self.tasks_frame, text="Convex Hull & Centroid") \
            .grid(row=17, column=1, sticky=NW, pady=5)
        Label(self.tasks_frame, text="7.").grid(row=18, column=0, sticky=W)
        Button(self.tasks_frame, text="Distance btw Centroids") \
            .grid(row=18, column=1, sticky=NW, pady=5)

        Label(self.tasks_frame, text="8.").grid(row=19, column=0, sticky=W)
        Button(self.tasks_frame, text="Joining Line") \
            .grid(row=19, column=1, sticky=NW, pady=5)
        Label(self.tasks_frame, text="9.").grid(row=20, column=0, sticky=W)
        Button(self.tasks_frame, text="Geocode Centroid") \
            .grid(row=20, column=1, sticky=NW, pady=5)

        Label(self.tasks_frame, text="10.").grid(row=21, column=0, sticky=W)
        Button(self.tasks_frame, text="Create Shapefiles") \
            .grid(row=21, column=1, sticky=NW, pady=5)


        self.log_frame = LabelFrame(self.frame1, padx=10, pady=10, text="Log")
        self.log_frame.grid(row=0, column=1, sticky=NW)

        self.log_text = st.ScrolledText(self.log_frame, width=50, height=40, wrap=WORD)
        self.log_text.grid(row=0, column=0)

    def catch_destroy(self):
        if messagebox.askokcancel("Quit", "Do you really wantto terminate the processs"):
            self.my_parent.destroy()

    def download_geojson_file(params):

        import urllib.parse
        import httplib2
        import os, os.path
        import json
        import xml.etree.ElementTree as etree

        if "host" not in params:
            raise ValueError("Value for 'host' required")
            self.log_text.insert(END,
                                   "PLEASE INSERT VALID HOST NAME")
        if "layer" not in params:
            raise ValueError("Value for 'layer' required")
        if "srs_code" in params and params["srs_code"]:
            srs_text = "&srsName=epsg:{}".format(params["srs_code"])
        else:
            srs_text = ""
        if "properties" in params and params["properties"]:
            item_string = ""
            for item in params["properties"]:
                item_string += str(item) + ","
            if "geom_field" in params and params["geom_field"]:
                item_string += str(params["geom_field"])
            property_text = "&PROPERTYNAME={}".format(item_string)
        else:
            property_text = ""
        if "filter_property" in params and params["filter_property"] and params["filter_values"]:
            filter_text = "{filter_property} LIKE '%{filter_values}%'".format(filter_property=params["filter_property"],
                                                                              filter_values=params["filter_values"][0])
            for item in range(1, len(params["filter_values"])):
                filter_text += "OR {filter_property} LIKE '%{filter_values}%'".format(
                    filter_property=params["filter_property"], filter_values=params["filter_values"][item])
            filter_text = urllib.parse.quote(filter_text)
            filter_text = "&CQL_FILTER=" + filter_text
        else:
            filter_text = ""

        url = "http://{host}/geoserver/ows?" \
              "service=WFS&version=1.0.0&" \
              "request=GetFeature&" \
              "typeName={layer}&" \
              "outputFormat=json".format(host=params["host"], layer=params["layer"])
        url += srs_text
        url += property_text
        url += filter_text

        #
        # Make a directory to hold downloads so that we don't have to repeatedly download them later, i.e. they already
        # exist so we get them from a local directory. This directory is called .httpcache".
        #
        scriptDir = os.path.dirname(__file__)
        cacheDir = os.path.normpath(os.path.join(scriptDir, ".httpcache"))
        if not os.path.exists(cacheDir):
            os.mkdir(cacheDir)

        #
        # Go to the web and attempt to get the resource
        #
        try:
            h = httplib2.Http()
            response_headers, response = h.request(url)
            response = response.decode()
            params.log_text.insert(END,
                                 "succesfuly Downloaded file")

            if response[:5] == "<?xml":
                response = etree.fromstring(response)
                xml_error = ""
                for element in response:
                    xml_error += element.text
                raise Exception(xml_error)
            else:
                return json.loads(response)

        except httplib2.HttpLib2Error as e:
            print(e)
            params.log_text.insert(END,
                                   "FAILED TO DOWNLOAD FILES")

    def single_plot(self):
        try:
            # Can run file dialogue from the .cache directory
            jfile = filedialog.askopenfilename(filetypes=(("Geojson File", "*.json"),))
            source = gp.read_file(jfile)
            source.plot(figsize=(10, 10), alpha=.7, edgecolor='k')
            plt.show()
            self.log_text.insert(
                END, " Single polygon Successful ploted\n"
            )

        except Exception as e:
            print(e)
            quit()


    def extract_points(self):
        # Ceate outline geojson structure
        geojson = {"type": "FeatureCollection", "features": [], "crs": {"type": "EPSG", "properties": {"code": None}},
                   "bbox": []}
        try:
            if not self.centroid:
                raise ValueError("Couldn't find merged GeoJSON.")
            self.log_text.insert(END, "-" * 80 + "\n")


            self.log_text.insert(END, "-" * 80 + "\n")
            return
        except Exception as e:
            self.log_text.insert(END, "-" * 80 + "\n")
            self.log_text.insert(END, "Ops there is an Error: {}\n".format(e))
            self.log_text.insert(END, "-" * 80 + "\n")
            return

def main_gui():
    root = Tk()
    MyGUI(root)
    root.mainloop()


if __name__=="__main__":
    main_gui()