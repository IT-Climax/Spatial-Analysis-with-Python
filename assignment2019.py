"""

Specific Tasks
    1. Create a single polygon from the Union of all the polygons.
    2. Compute the centroid of the single polygon.
    3. Extract the points that lie within the single polygon.
    4. Compute a convex hull and centroid for the extracted points
    5. Compute the distance between the centroid of the single polygon and the
    centroid of the points that lie within the single polygon.
    6. Create a representation of the line joining the two centroids
    7. Geocode both centroids and add their names to the appropriate point as an
    attribute
    8. Create shapefiles to store the results of the above. Bear in mind that a shapefile
    contains a single geometry type and is a set of thematically related features.
    Therefore you will need to create shapefiles as follows:
        • Combined polygon from Union
        • Points that lie within Combined Polygon
        • Convex hull of the points from above
        • Both centroids. Each should have an attribute to hold its name returned
        from the geocoding process.
        • Linestring representing the distance between the centroids

Process
Data Downloads
dit data preview using LEGAL TOWN GEOM
Format in Geojos
url: http://mf2.dit.ie:8080/geoserver/cso/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=cso:ltgeom&maxFeatures=50&outputFormat=json

"""


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
OUTPUT_DIR = ".cache"

# Source shapefile for non-GUI version
Source_file = "data/uss.json"

from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from tkinter import TclError
from tkinter import scrolledtext as st


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


def shp_to_geojson(shapefile):
    """
    Takes a Shapefile name, opens the shapefile and returns its GeoJSON-like equivalent as a
    dictionary.

    :param shapefile: Full path/to/shapefile as string
    :return: GeoJSON-like representation of the shapefile as dictionary
    """

    # Ceate outline geojson structure
    geojson = {"type": "FeatureCollection", "features": [], "crs": {"type": "EPSG", "properties": {"code": None}},
               "bbox": []}

    try:
        with fiona.Env():
            with fiona.open(shapefile, "r") as fh:
                # Add crs and bbox properties to the geojson structure
                geojson["crs"]["properties"]["code"] = int(fh.crs["init"].split(":")[1])
                geojson["bbox"] = fh.bounds

                for feature in fh:
                    # add each feature to geojson structure, Fiona gives it to us in a suitable format so no further processing
                    # required
                    geojson["features"].append(feature)

            # OPTIONAL bit: get the name of the incoming shapefile and replace the '.shp' bit with '.json' so that we can
            # write this to disk in case we want touse it later.
            output = shapefile.split("/")[-1]
            with open("{}/{}.json".format(OUTPUT_DIR, output.split(".")[-2]), "w") as json_out:
                json_out.write(json.dumps(geojson))


    except Exception as e:
        print(e)
        quit()

    # Return the GeoJSON that we have just made.
    return geojson


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



# def original_geojson(geojson):


class MyGUI:
    """
    Class that defines the GUI. This approach helps partition GUI-related elements from other parts of the program.
    Also avoids the use of global variables later.
    Ultimately reduces complexity.

    """
    def __init__(self, my_parent):
        #Set up some instances variable interaction between the application and the window handler

        self.single_plot = object()
        self.first_shp_geojson = StringVar()
        self.merge_from_shp = StringVar()
        self.extract_points = object()

        self.my_parent = my_parent

        self.my_parent.title("GIS Programming - Supplement 2019")

        my_parent.protocol("WM_DELETE", self.catch_destroy)

        self.frame1 = ttk.Frame(my_parent, padding=5, border=1)
        self.frame1.grid(row=0, column=0)

        self.tasks_frame = LabelFrame(self.frame1, padx=15, pady=15, text="Tasks")
        self.tasks_frame.grid(row=0, column=0, stick=NW)

        Label(self.tasks_frame, text="1.").grid(row=0, column=0, sticky=W)
        Button(self.tasks_frame, text="Please select Source Geojson", command=self.get_jsonFile)\
            .grid(row=0, column=1, sticky=NW, pady=5)

        Label(self.tasks_frame, text="2.").grid(row=1, column=0, sticky=W)
        Button(self.tasks_frame, text="Plot Single Polygon", command=self.get_single_plot) \
            .grid(row=1, column=1, sticky=NW, pady=5)

        Label(self.tasks_frame, text="3.").grid(row=2, column=0, sticky=W)
        Button(self.tasks_frame, text="Compute Centroids", command= self.centroid_from_merge) \
            .grid(row=2, column=1, sticky=NW, pady=5)

        Label(self.tasks_frame, text="4.").grid(row=3, column=0, sticky=W)
        Button(self.tasks_frame, text="Extract points", command= self.extract_points) \
            .grid(row=3, column=1, sticky=NW, pady=5)

        Label(self.tasks_frame, text="5.").grid(row=4, column=0, sticky=W)
        Button(self.tasks_frame, text="Convex Hull") \
            .grid(row=4, column=1, sticky=NW, pady=5)

        Label(self.tasks_frame, text="6.").grid(row=5, column=0, sticky=W)
        Button(self.tasks_frame, text="Distance Between Centroids") \
            .grid(row=5, column=1, sticky=NW, pady=5)

        Label(self.tasks_frame, text="7.").grid(row=6, column=0, sticky=W)
        Button(self.tasks_frame, text="Line Between Centroids") \
            .grid(row=6, column=1, sticky=NW, pady=5)

        Label(self.tasks_frame, text="8.").grid(row=7, column=0, sticky=W)
        Button(self.tasks_frame, text="Geocode Centroids") \
            .grid(row=7, column=1, sticky=NW, pady=5)

        Label(self.tasks_frame, text="9.").grid(row=8, column=0, sticky=W)
        Button(self.tasks_frame, text="Generate Shapefiles") \
            .grid(row=8, column=1, sticky=NW, pady=5)

        self.log_frame = LabelFrame(self.frame1, padx=15, pady=15, text="Log")
        self.log_frame.grid(row=0, column=1, sticky=NW)

        self.log_text = st.ScrolledText(self.log_frame, width=80, height=50, wrap=WORD)
        self.log_text.grid(row=0, column=0)

    def catch_destroy(self):
        if messagebox.askokcancel("Quit", "Do you really wantto terminate the processs"):
            self.my_parent.destroy()

    def get_jsonFile(self):
        # Can run file dialogue from anywhere
        first_json = filedialog.askopenfilename(filetypes=(("Geojson File", "*.json"),))
        if not first_json:
            return
        try:
            self.log_text.insert(END, "-" * 80 + "\n")
            self.log_text.insert(END, "Geojson selected: {}\n".format(first_json))

            # The 'active ingredient' is shp_to_geojson which hasn't changed with the introduction of the GUI
            self.first_shp_geojson = shp_to_geojson(first_json)

            self.log_text.insert(END, "-" * 80 + "\n")
            self.log_text.insert(END, "Feature properties:\n")
            for k, v in self.first_shp_geojson["features"][0]["properties"].items():
                self.log_text.insert(END, "... {}\n".format(k))
            self.log_text.insert(END, "-" * 80 + "\n")

        except Exception as e:
            self.log_text.insert(END, "-" * 80 + "\n")
            self.log_text.insert(END, "Ops there is an error please check the file you are trying upload: {}\n".format(e))
            self.log_text.insert(END, "-" * 80 + "\n")
            return


    def get_single_plot(self):
        try:
            source = gp.read_file(Source_file)
            # print(source.head())
            source.plot(figsize=(10, 10), alpha=.7, edgecolor='k')
            plt.show()

        except Exception as e:
            print(e)
            quit()

    def merge_from_shp(self):
        try:
            self.log_text.insert(END, "-" * 80 + "\n")
            # Active ingredient...
            self.merged = merge_polys(Source_file)

            self.log_text.insert(END,
                                 "Creating new shapefile: {}/{}.shp\n".format(OUTPUT_DIR, self.merged_shp_name.get()))

            # Active ingredient...
            geojson_to_shp(self.merged, "{}/{}.shp".format(OUTPUT_DIR, self.merged_shp_name.get()))

            self.log_text.insert(END, "Finished creating new shapefile: {}/{}.shp\n".format(OUTPUT_DIR,
                                                                                            self.merged_shp_name.get()))
            self.log_text.insert(END, "-" * 80 + "\n")
            return
        except Exception as e:
            self.log_text.insert(END, "-" * 80 + "\n")
            self.log_text.insert(END, "Ops there is an Error: {}\n".format(e))
            self.log_text.insert(END, "-" * 80 + "\n")
            return

    def centroid_from_merge(self):
        try:
            # if not self.merged:
            #     raise ValueError("Couldn't find merged GeoJSON.")
            #
            # self.log_text.insert(END, "-" * 80 + "\n")

            # Active ingredient...
            self.merged = merge_polys(Source_file)
            self.centroid = make_centroid(self.merged)

            self.log_text.insert(
                END, "Centroid: {}\n{}\n"
                    .format(
                    self.centroid["features"][0]["geometry"]["coordinates"],
                    self.centroid["features"][0]["properties"]["address"]
                )
            )

            # Active ingredient...
            geojson_to_shp(self.centroid, "{}/{}.shp".format(OUTPUT_DIR, self.centoid_shp_name.get()))

            self.log_text.insert(END, "Finished creating new shapefile: {}/{}.shp\n".format(OUTPUT_DIR,
                                                                                            self.centoid_shp_name.get()))
            self.log_text.insert(END, "-" * 80 + "\n")
            return
        except Exception as e:
            self.log_text.insert(END, "-" * 80 + "\n")
            self.log_text.insert(END, "Ops there is an Error: {}\n".format(e))
            self.log_text.insert(END, "-" * 80 + "\n")
            return


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