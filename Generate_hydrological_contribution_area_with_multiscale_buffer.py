"""
**********************************************************************************************************************
    Generate hydrological contribution area with multiscale buffer.py                                                *
    -----------------------------------------------------------------------------------------------------------------*
    Date                 : September 2025                                                                            *
    Copyright            : (C) 2025 by Henrique Ledo Lopes Pinho, Jéssica Bassani de Oliveira, Yzel Rondon Súarez    *
    Email                : geaaqua@uems.br                                                                           *
**********************************************************************************************************************
*                                                                                                                    *
*   This program is free software; you can redistribute it and/or modify it under the terms of the GNU General       *
*   Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option)*
*   any later version.                                                                                               *
*                                                                                                                    *
**********************************************************************************************************************
"""

# =====================================================================================================================
#
# GENERAL DESCRIPTION:
# This script automates an end-to-end workflow in QGIS (v3.34.5) for hydrological studies.
# It integrates a module for delineation into Exclusive Contribution Areas (ECAs) and a buffer generation module.
# Starting from a layer of monitoring points (outlets), it performs watershed delineation, overlap correction
# to generate ECAs, and finally, the creation of multiscale analysis buffers.
#
# WORKFLOW:
# 1. ECA DELINEATION AND GENERATION:
#    - Delineates watersheds for each input point (supports multiple points).
#    - Resolves overlaps between basins using a hierarchical "Difference" approach, which prioritizes
#      upstream (higher elevation) areas.
#    - The result is a set of individual polygons, where each represents a non-overlapping Exclusive Contribution Area (ECA).
#
# 2. BATCH MULTISCALE ANALYSIS:
#    - Uses the ECAs as the primary analysis units.
#    - Reads a spreadsheet (.xls) to batch-generate various buffers and scales, such as:
#      - Riparian Buffer (RB)
#      - Local Contributing Area (LCA)
#      - Riparian Buffer in Local Contributing Area (RBLCA)
#
# OBJECTIVE:
# To transform monitoring points into consistent, non-overlapping spatial analysis units (ECAs),
# while applying multiscale analyses in a standardized, automated, and replicable manner.
#
# DEPENDENCIES & REQUIREMENTS:
# - Execution Environment: QGIS (v3.34.5)
# - Core Libraries/Plugins: 'processing' (with GRASS and GDAL enabled)
# - Processing Tools Used: r.watershed, r.water.outlet, Polygonize, Fix Geometries,
#   Dissolve, Zonal Statistics, Difference, Buffer, Split Vector Layer,
#   Convert Format, and Clip.
# ======================================================================================================================
# =====================================================================================================================
# Initial configuration: Paths and Global Parameters
# ====================================================
# PATHS RELATED TO THE GENERATION OF EXCLUSIVE CONTRIBUTION AREA
# ==============================================================
# Directory where the digital elevation model raster is stored
dem_path = "C:/EXAMPLE/3/ELEVATION_RASTER/DEM.tif"
# Directory where this coordinates of the exutory are stored
exutory_txt = "C:/EXAMPLE/3/EXUTORY_COORDINATES/EXUTORY_COORDINATES.txt"
# Directory where the shapefile with the points in stream segments is stored
collection_shp = "C:/EXAMPLE/3/POINTS_IN_STREAM_SEGMENTS/points_in_stream_segments.shp"
# Defines the output directory for the intermediate layers (generates a new folder)
intermediary_layers_dir = "C:/EXAMPLE/3/INTERMEDIARY_FILES/"
# Defines the output directory containing the contribution areas(generates a new folder)
final_polygon_dir = "C:/EXAMPLE/3/FINAL_POLYGONS/"
# Directory where the stream segment this stored (Optional)
stream_segments_path = "C:/EXAMPLE/3/STREAM_SEGMENTS/stream_segments.tif"
# Threshold parameter for basins outside the main watercourse
threshold = 1000
# Convergence factor for multiple flow direction
convergence = 5
# Maximum memory to be used (in MB)
memory = 300
# ===============================================================
# ==== PATHWAYS RELATED TO MULTISCALE BUFFER GENERATION====
# ================================================================
# Path to the Excel spreadsheet with parameters (buffer distances)
spreadsheet_path = r"C:/EXAMPLE/3/PARAMETERS/multiscale_parameters.xlsx"
# Directory where the results will be saved
result_dir = r"C:/EXAMPLE/3/RESULT_MULTI"
# Path to the shapefile archive of collected points on site
points = r"C:/EXAMPLE/3/COLLECTED_ON_SITE/Collected_on_site.shp"
# Directory containing files (rivers, dams, etc.)
# The script automatically adjusts to the type of .shp file (whether polygon or line)
line_or_polygon_dir = r"C:/EXAMPLE/3/REGISTER/DRAINAGE"
# Directory containing polygons (watersheds, contribution areas, etc.)
polygon_dir = r"C:/EXAMPLE/3/FINAL_POLYGONS/"
# CONFIGURATION: DIFFERENCE OPERATIONS
apply_difference = False  # True = apply difference, False = not apply
# =======================================================================
import os
import processing
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsProject

# Function to add layers to the project
# ========================================
def add_layer_to_project(layer, name):
    """
    Adds layers to the QGIS project.
    Checks if the layer is valid and, if so, adds it to the project.
    """
    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        print(f"Layer '{name}' loaded into the project.")
    else:
        print(f"Error: Layer '{name}' is not valid and has not been loaded.")


# Part 1: River Basin Delimitation
# ============================================
def process_basin_delimitation():
    """
     Part 1: River Basin Delimitation in QGIS.
    Performs the basin delimitation process using the digital elevation model (DEM)
    and the specified outflow points.
    """
    print("Executing Part 1: Basin Delimitation")

    # Create the output directories if they don't exist
    os.makedirs(intermediary_layers_dir, exist_ok=True)
    os.makedirs(final_polygon_dir, exist_ok=True)

    # Reading the coordinates from the exits file
    outlet_coords = []
    with open(exutory_txt, mode='r') as txtfile:
        for line in txtfile:
            # Ignore header and edit coordinates (x, y)
            if 'x' in line.lower() and 'y' in line.lower():
                continue
            x, y = map(float, line.strip().split(','))
            outlet_coords.append({'x': x, 'y': y})

    # Load the Digital Elevation Model (DEM)
    print("Loading the Digital Elevation Model (DEM)...")
    dem_layer = QgsRasterLayer(dem_path, "Digital Elevation Model")
    if not dem_layer.isValid():
        raise RuntimeError(f"Erro: The raster could not be loaded in the path {dem_path}")
    add_layer_to_project(dem_layer, "Digital Elevation Model")

    # Load the collection points
    print("Loading collection points...")
    collection_layer = QgsVectorLayer(collection_shp, "Collected Points", "ogr")
    if not collection_layer.isValid():
        raise RuntimeError(f"Error: Unable to load point shapefile on path {collection_shp}")
    add_layer_to_project(collection_layer, "Collected Points")

    # Extract the names of the points collected
    collection_features = collection_layer.getFeatures()
    collection_names = [feature['Points'] for feature in collection_features]

    # If the path of the flow segment has been entered, load the layer
    if stream_segments_path:
        print("Loading stream segments...")
        segments_layer = QgsRasterLayer(stream_segments_path, "Stream Segments")
        if segments_layer.isValid():
            add_layer_to_project(segments_layer, "Stream Segments")
        else:
            print(f"Erro: Could not load flow segment in path {stream_segments_path}")

    # Run r.watershed to calculate drainage direction and stream segments
    print("Executing r.watershed...")
    drainage_output = os.path.join(intermediary_layers_dir, "drainage_direction.tif")
    processing.run("grass7:r.watershed", {
        'elevation': dem_path,
        'threshold': threshold,
        'convergence': convergence,
        'memory': memory,
        'drainage': drainage_output,
        'GRASS_REGION_PARAMETER': f"{dem_path}",
        'GRASS_REGION_CELLSIZE_PARAMETER': 0
    })

    # Load the drainage direction into the project
    drainage_layer = QgsRasterLayer(drainage_output, "Drainage Direction")
    if drainage_layer.isValid():
        add_layer_to_project(drainage_layer, "Drainage Direction")
    else:
        print(f"Error: Unable to load drainage direction raster in {drainage_output}")

    # Generate watersheds for each exutory of points
    corrected_outputs = []
    for coord, collection_name in zip(outlet_coords, collection_names):
        raster_output = os.path.join(intermediary_layers_dir, f"basin_{collection_name}.tif")
        vector_output = os.path.join(intermediary_layers_dir, f"basin_{collection_name}.shp")
        corrected_output = os.path.join(intermediary_layers_dir, f"corrected_basin_{collection_name}.shp")

        # Execute r.water.outlet to delimit the basin of the exutory point
        print(f"Running r.water.outlet for the point {collection_name}...")
        processing.run("grass7:r.water.outlet", {
            'input': drainage_output,
            'coordinates': f"{coord['x']},{coord['y']}",
            'output': raster_output,
            'GRASS_REGION_PARAMETER': f"{dem_path}",
            'GRASS_REGION_CELLSIZE_PARAMETER': 0
        })

        # Convert the output raster to vector (polygonize)
        print("Correcting geometry...")
        processing.run("gdal:polygonize", {
            'INPUT': raster_output,
            'FIELD': "DN",
            'OUTPUT': vector_output
        })
        processing.run("native:fixgeometries", {
            'INPUT': vector_output,
            'OUTPUT': corrected_output
        })
        corrected_outputs.append(corrected_output)

    # Dissolve the geometries of the corrected basins
    dissolved_outputs = []
    for corrected_output, collection_name in zip(corrected_outputs, collection_names):
        dissolved_output = os.path.join(intermediary_layers_dir, f"dissolved_basin_{collection_name}.shp")

        print(f"Dissolving geometries for the point {collection_name}...")
        processing.run("native:dissolve", {
            'INPUT': corrected_output,
            'OUTPUT': dissolved_output
        })
        dissolved_outputs.append(dissolved_output)

    print("Part 1 successfully completed!")


# Part 2: Calculating Zonal Statistics
# ========================================
def calculate_zonal_statistics():
    """
    Part 2: Calculating Zonal Statistics.
    Calculates digital elevation model statistics for each basin.
    """
    print("Executing Part 2: Zonal Statistics")

    # Identify shapefiles in the temporary polygon directory
    shapefiles = [
        os.path.join(intermediary_layers_dir, file)
        for file in os.listdir(intermediary_layers_dir)
        if file.startswith("dissolved_basin_") and file.endswith(".shp")
    ]

    if not shapefiles:
        print("No shapefile found to process.")
        return

    print(f"Shapefiles found: {shapefiles}")

    # Load the Collected Points layer
    points_layer = QgsVectorLayer(collection_shp, "Collected Points", "ogr")
    if not points_layer.isValid():
        print("Erro: The file could not be uploaded Collected_Points.shp.")
        return

    points_nomes = [feature["Points"] for feature in points_layer.getFeatures()]
    if len(points_nomes) != len(shapefiles):
        print("Error: The number of collected points does not match the number of shapefiles.")
        return

    for shapefile in shapefiles:
        # Extract the shapefile suffix
        suffix = os.path.basename(shapefile).split("dissolved_basin_")[1].replace(".shp", "")

        output_path = os.path.join(intermediary_layers_dir, f"zonal_basin_{suffix}.shp")
        print(f"Processing {shapefile} for the suffix {suffix}...")

        # Calculating zonal statistics
        print("alculating zonal statistics...")
        try:
            processing.run("native:zonalstatisticsfb", {
                'INPUT': shapefile,
                # The shapefile containing the basins for which the zonal statistics will be calculated.
                'INPUT_RASTER': dem_path,  # The input raster (in this case, the Digital Elevation Model - DEM).
                'RASTER_BAND': 1,
                # The number of the raster band that will be used for the calculation (usually 1 for rasters with a single band).
                'COLUMN_PREFIX': '_',
                # Prefix added to the names of the output columns in the shapefile to identify the results of the statistics.
                'STATISTICS': [5],
                # List of statistics to be calculated. The value 5 indicates that the **minimum value** of the elevations in the raster within each polygon of the shapefile will be calculated.
                'OUTPUT': output_path
                # Path where the output shapefile will be saved, containing the calculated statistics as additional attributes.
            })
            print(f"Zonal statistics calculated for {shapefile}. Output: {output_path}")
        except Exception as e:
            print(f"Error in calculating zonal statistics for {shapefile}: {e}")

    print("Part 2 successfully completed!")


# Part 3: Processing Differences between Basins.
# ==================================================
def process_basin_difference():
    """
    Part 3: Processing differences between basins.
    Sorts shapefiles based on minimum elevation, calculates differences between basins
    to generate unique basins.
    """
    print("Executing Part 3: Differences between Basins")

    shapefiles = [
        os.path.join(intermediary_layers_dir, file)
        for file in os.listdir(intermediary_layers_dir)
        if file.startswith("zonal_basin_") and file.endswith(".shp")
    ]

    if not shapefiles:
        print("No zonal basin shapefile found to process.")
        return

    elevation_stats = []
    for shapefile in shapefiles:
        suffix = os.path.basename(shapefile).split("zonal_basin_")[1].replace(".shp", "")

        layer = QgsVectorLayer(shapefile, "", "ogr")
        for feature in layer.getFeatures():
            if '_min' in feature.fields().names():
                elevation_stats.append({'path': shapefile, 'min': feature['_min'], 'suffix': suffix})

    elevation_stats = sorted(elevation_stats, key=lambda x: x['min'], reverse=True)

    output_files = []

    for i, current_stat in enumerate(elevation_stats):
        suffix = current_stat['suffix']
        # Save exclusive_contribution_area_ files in the FINAL_POLYGON directory
        output_path = os.path.join(final_polygon_dir, f"exclusive_contribution_area_{suffix}.shp")

        if i == 0:
            processing.run("native:savefeatures", {
                'INPUT': current_stat['path'],
                'OUTPUT': output_path
            })
        else:
            temp_base_path = current_stat['path']
            for j in range(i):
                overlay_layer_path = elevation_stats[j]['path']
                # INTERMEDIARY files remain in INTERMEDIARY LAYERS directory
                temp_output = os.path.join(intermediary_layers_dir, f"temp_diff_{i}_{j}.shp")
                processing.run("native:difference", {
                    'INPUT': temp_base_path,
                    'OVERLAY': overlay_layer_path,
                    'OUTPUT': temp_output
                })
                temp_base_path = temp_output

            processing.run("native:savefeatures", {
                'INPUT': temp_base_path,
                'OUTPUT': output_path
            })

        output_files.append(output_path)

    # Load all layers to the project (including exclusive_contribution_area_ files from FINAL_POLYGON)
    project = QgsProject.instance()

    # Load final exclusive_contribution_area_ files from FINAL_POLYGON directory
    for output_file in output_files:
        layer_name = os.path.basename(output_file).replace(".shp", "")
        layer = QgsVectorLayer(output_file, layer_name, "ogr")
        if layer.isValid():
            project.addMapLayer(layer)

    print("Part 3 successfully completed!")


# ==================================================
# Execute all parts
process_basin_delimitation()
calculate_zonal_statistics()
process_basin_difference()

print("Processing completed successfully! All the parts have been executed.")
# ======================================================================
#                               MULTIPLE SCALES
# ======================================================================
# Importing libraries
import os
import processing
from qgis.core import (QgsVectorLayer, QgsProject, QgsVectorFileWriter, QgsFillSymbol,
                       QgsWkbTypes, QgsRectangle, QgsGeometry, QgsPointXY, QgsFeature, QgsField)
import pandas as pd
from PyQt5.QtCore import QVariant


def calculate_shapefile_area(input_path, output_path, field_area='area_calc'):
    """Calculates the area of each polygon in the shapefile"""
    try:
        layer = QgsVectorLayer(input_path, "temp", "ogr")
        if not layer.isValid():
            print(f"ERROR: Unable to load {input_path}")
            return None

        provider = layer.dataProvider()

        # Add area field if it does not exist
        fields = [field.name() for field in layer.fields()]
        if field_area not in fields:
            layer.startEditing()
            layer.addAttribute(QgsField(field_area, QVariant.Double))
            layer.commitChanges()

        layer.updateFields()

        # Calculates the area for each feature
        layer.startEditing()
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom.type() == QgsWkbTypes.PolygonGeometry:
                area = geom.area()
                layer.changeAttributeValue(feature.id(), layer.fields().indexFromName(field_area), area)

        layer.commitChanges()

        QgsVectorFileWriter.writeAsVectorFormat(
            layer,
            output_path,
            "UTF-8",
            layer.crs(),
            "ESRI Shapefile"
        )

        print(f"Area calculated and saved in: {output_path}")
        return output_path

    except Exception as e:
        print(f"ERROR when calculating area for {input_path}: {e}")
        return None


def get_total_area(shapefile_path, field_area='area_calc'):
    """Get the total area of a shapefile"""
    try:
        layer = QgsVectorLayer(shapefile_path, "temp", "ogr")
        if not layer.isValid():
            return None

        total_area = 0
        for feature in layer.getFeatures():
            area_feature = feature[field_area]
            if area_feature is not None:
                total_area += area_feature

        return total_area
    except Exception as e:
        print(f"ERROR when obtaining area of {shapefile_path}: {e}")
        return None


def find_field_id_points(layer_points):
    """Finds the ID field in the point layer"""
    fields = [field.name() for field in layer_points.fields()]
    if not fields:
        return None
    return fields[0]


def extract_identifier_from_name(file_name):
    """Extracts an identifier from the file name"""
    base_name = os.path.splitext(file_name)[0]
    if '_' in base_name:
        parts = base_name.split('_')
        return parts[-1]
    return base_name


def obtain_unique_field_values(layer, field_name):
    """Get all unique values from a field"""
    values = []
    for feature in layer.getFeatures():
        value = feature[field_name]
        if value is not None and value not in values:
            values.append(str(value))
    return values


def detect_file_line(line_or_polygon_dir):
    """Automatically detects the line file"""
    if not line_or_polygon_dir or not os.path.exists(line_or_polygon_dir):
        return None

    files_shp = []
    for file in os.listdir(line_or_polygon_dir):
        if file.endswith(".shp"):
            files_shp.append(os.path.join(line_or_polygon_dir, file))

    if not files_shp:
        print(f"No .shp files found in: {line_or_polygon_dir}")
        return None

    chosen_file = files_shp[0]
    print(f"Line file detected: {os.path.basename(chosen_file)}")

    if len(files_shp) > 1:
        print(f"Multiple files found. Using the first: {os.path.basename(chosen_file)}")

    return chosen_file


def verify_line_geometry(layer_path):
    """Checks whether the layer contains line geometries"""
    layer = QgsVectorLayer(layer_path, "temp", "ogr")
    if not layer.isValid():
        return False

    geometry_type = layer.wkbType()
    return QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.LineGeometry


def make_polygons_points_match(paths_polygons, layer_points, field_id_points):
    """Match the polygon files to the points"""
    matching = {}

    points_ids = obtain_unique_field_values(layer_points, field_id_points)
    print(f"IDs found at the points: {points_ids}")

    for path_polygon in paths_polygons:
        file_name = os.path.basename(path_polygon)
        polygon_identifier = extract_identifier_from_name(file_name)

        print(f"File: {file_name} -> Identifier extracted: {polygon_identifier}")

        # Exact match
        match_found = False
        for point_id in points_ids:
            if str(point_id).lower() == str(polygon_identifier).lower():
                matching[point_id] = path_polygon
                match_found = True
                print(f"Correspondência exata: {point_id} -> {file_name}")
                break

        # Partial correspondence
        if not match_found:
            for point_id in points_ids:
                if (str(polygon_identifier).lower() in str(point_id).lower() or
                        str(point_id).lower() in str(polygon_identifier).lower()):
                    matching[point_id] = path_polygon
                    match_found = True
                    print(f"Partial match: {point_id} -> {file_name}")
                    break

        if not match_found:
            print(f"No match found for: {file_name}")

    print(f"\nFinal associations found: {len(matching)}")
    for point_id, path in matching.items():
        print(f" {point_id} -> {os.path.basename(path)}")

    return matching


def apply_difference_operation(input_path, mask_path, output_path):
    """Applies the difference operation"""
    try:
        params = {
            'INPUT': input_path,
            'OVERLAY': mask_path,
            'OUTPUT': output_path
        }

        processing.run("native:difference", params)
        print(f"Applied difference: {os.path.basename(output_path)}")
        return output_path

    except Exception as e:
        print(f"ERROR when applying difference in {input_path}: {e}")
        return None


# Create the directories
print("Creating directory structure...")
if not os.path.exists(result_dir):
    os.makedirs(result_dir)

# Load the parameters from the Excel spreadsheet
print("Loading parameters from the Excel spreadsheet...")
try:
    if spreadsheet_path.endswith('.xls'):
        engine = 'xlrd'
    elif spreadsheet_path.endswith('.xlsx'):
        engine = 'openpyxl'
    else:
        engine = None

    df_parameters = pd.read_excel(spreadsheet_path, engine=engine)

    if "Step" not in df_parameters.columns or "Meters" not in df_parameters.columns:
        raise Exception(
            f"The ‘Step’ and ‘Meters’ columns are required. Columns found: {list(df_parameters.columns)}")

    # Get distances
    filter_circular_buffer = df_parameters["Step"].str.contains("1 - Buffer Circular", na=False)
    circular_distance_buffer = df_parameters.loc[filter_circular_buffer, "Meters"].dropna().tolist()

    filter_riparian_buffer = df_parameters["Step"].str.contains("6 - Riparian Buffer", na=False)
    distances_riparian_buffer = df_parameters.loc[filter_riparian_buffer, "Meters"].dropna().tolist()

    # Determines the operating mode
    tem_buffer_circular = len(circular_distance_buffer) > 0
    tem_riparian_buffer = len(distances_riparian_buffer) > 0

    if not tem_buffer_circular and not tem_riparian_buffer:
        raise Exception("The spreadsheet must contain at least one type of buffer.")

    if tem_buffer_circular and tem_riparian_buffer:
        operation_mode = "FULL"
        print("OPERATING MODE: FULL")
    elif tem_buffer_circular:
        operation_mode = "CIRCULAR"
        print("OPERATING MODE: CIRCULAR BUFFER ONLY")
    else:
        operation_mode = "RIPARIAN"
        print("OPERATING MODE: RIPARIAN BUFFER ONLY")

    if tem_buffer_circular:
        print(f"Meterss de buffer circular: {circular_distance_buffer}")
    if tem_riparian_buffer:
        print(f"Riparian buffer distances: {distances_riparian_buffer}")

    print(f"DIFFERENCE OPERATIONS: {'ENABLED' if apply_difference else 'DISABLED'}")

except Exception as e:
    print(f"ERROR: Unable to load Excel spreadsheet parameters. Details: {e}")
    raise Exception("Error loading spreadsheet. Processing interrupted.")

# Creates directory structure based on operating mode
if operation_mode in ["CIRCULAR", "FULL"]:
    buffer_circular_dir = os.path.join(result_dir, "1BUFFER_CIRCULAR")
    if not os.path.exists(buffer_circular_dir):
        os.makedirs(buffer_circular_dir)

    split_layers_dir = os.path.join(result_dir, "2SPLIT_LAYERS")
    if not os.path.exists(split_layers_dir):
        os.makedirs(split_layers_dir)

    convert_format_dir = os.path.join(result_dir, "3CONVERT_FORMAT")
    if not os.path.exists(convert_format_dir):
        os.makedirs(convert_format_dir)

    buffer_circ_area_dir = os.path.join(result_dir, "4LCA_Temporary")
    if not os.path.exists(buffer_circ_area_dir):
        os.makedirs(buffer_circ_area_dir)

    final_polygons_area_dir = os.path.join(result_dir, "ECA_WITH_AREA")
    if not os.path.exists(final_polygons_area_dir):
        os.makedirs(final_polygons_area_dir)

    extrapolated_areas_dir = os.path.join(result_dir, "LCA_EXTRAPOLATED_AREAS")
    if not os.path.exists(extrapolated_areas_dir):
        os.makedirs(extrapolated_areas_dir)

    lca_dir = os.path.join(result_dir, "5LCA_Definitive")
    if not os.path.exists(lca_dir):
        os.makedirs(lca_dir)

if operation_mode in ["RIPARIAN", "FULL"]:
    clipped_line_dir = os.path.join(result_dir, "6TARGET_LAYER_FOR_RIPARIAN_BUFFER")
    if not os.path.exists(clipped_line_dir):
        os.makedirs(clipped_line_dir)

    riparian_buffer_dir = os.path.join(result_dir, "7RB_Temporary")
    if not os.path.exists(riparian_buffer_dir):
        os.makedirs(riparian_buffer_dir)

    amortec_recort_dir = os.path.join(result_dir, "8RB_Definitive")
    if not os.path.exists(amortec_recort_dir):
        os.makedirs(amortec_recort_dir)

    if apply_difference:
        amortec_recort_dif_dir = os.path.join(result_dir, "8RB_Definitive_Dif")
        if not os.path.exists(amortec_recort_dif_dir):
            os.makedirs(amortec_recort_dif_dir)

if operation_mode == "FULL":
    riparian_lca_dir = os.path.join(result_dir, "9RBLCA")
    if not os.path.exists(riparian_lca_dir):
        os.makedirs(riparian_lca_dir)

    if apply_difference:
        amortec_lca_dif_dir = os.path.join(result_dir, "9RBLCA_ Dif")
        if not os.path.exists(amortec_lca_dif_dir):
            os.makedirs(amortec_lca_dif_dir)

# Checks the input layers
print("Checking input layers...")
points_layer = QgsVectorLayer(points, "Points_Collected", "ogr")
if not points_layer.isValid():
    raise Exception(f"ERROR: Could not load the points in {points}")

file_line_detected = None
if operation_mode in ["RIPARIAN", "FULL"]:
    print("Detecting line file...")
    file_line_detected = detect_file_line(line_or_polygon_dir)

    if not file_line_detected:
        raise Exception("ERROR: Could not find line file for riparian buffer.")

    layer_line = QgsVectorLayer(file_line_detected, "temp_line", "ogr")
    if not layer_line.isValid():
        raise Exception(f"ERROR: Invalid line file: {file_line_detected}")

    if not verify_line_geometry(file_line_detected):
        print(f"WARNING: The file {os.path.basename(file_line_detected)} might not contain line geometries.")

    print(f"✓ Validated line file: {os.path.basename(file_line_detected)}")

# AUTOMATIC POLYGON DETECTION AND MATCHING WITH POINTS
print("\n" + "=" * 50)
print("STARTING AUTOMATIC DETECTION OF POLYGONS AND POINTS")
print("=" * 50)

print("Searching for polygon files...")
paths_polygons = []
for file in os.listdir(polygon_dir):
    if file.endswith(".shp"):
        paths_polygons.append(os.path.join(polygon_dir, file))

if not paths_polygons:
    raise Exception(f"ERROR: No .shp files were found in {polygon_dir}")

print(f"Found {len(paths_polygons)} .shp files in the polygon directory.")

field_id = find_field_id_points(points_layer)
if not field_id:
    raise Exception("ERROR: Could not find a suitable ID field in the point layer.")

print(f"ID field identified in the point layer: '{field_id}'")

polygons_points_match = make_polygons_points_match(paths_polygons, points_layer, field_id)

if not polygons_points_match:
    raise Exception("ERROR: Could not match polygons and points.")

point_names = list(polygons_points_match.keys())
print(f"\nPoints to be processed: {point_names}")

# Initialization of control variables
circular_buffers = {}
split_buffers = {}
clipped_buffers_temp = {}
polygon_areas = {}
lca_buffers = {}
extrapolated_areas = {}
clipped_line = {}
riparian_buffers = {}
cropped_riparian = {}
cropped_riparian_dif = {}
riparian_lca_dif = {}

# Calculation of polygon area
if operation_mode in ["CIRCULAR", "FULL"]:
    print("\nCalculating polygon areas...")

    for point_id in point_names:
        poligono_path = polygons_points_match.get(point_id)

        if not poligono_path:
            print(f"ERROR: Polygon to point {point_id} not found!")
            continue

        output_area = os.path.join(final_polygons_area_dir, f"ECA_{point_id}.shp")
        area_calculada = calculate_shapefile_area(poligono_path, output_area)

        if area_calculada:
            polygon_areas[point_id] = {
                'path': output_area,
                'total_area': get_total_area(output_area)
            }

# STEPS 1-3: Buffer Circular
if operation_mode in ["CIRCULAR", "FULL"]:
    # STEP 1: Generate buffer circular
    print("\n1. Generating circular buffers...")

    for distance in circular_distance_buffer:
        print(f"Creating a circular buffer of {distance}m...")
        output_buffer = os.path.join(buffer_circular_dir, f"circular_{int(distance)}m.shp")

        params = {
            'INPUT': points,
            'DISTANCE': distance,
            'SEGMENTS': 5,
            'END_CAP_STYLE': 0,
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'DISSOLVE': False,
            'OUTPUT': output_buffer
        }

        processing.run("native:buffer", params)
        circular_buffers[distance] = output_buffer

    # STEP 2 e 3: Split layers and convert format
    print("\n2 e 3. Splitting layers and converting formats...")

    for distance, buffer_path in circular_buffers.items():
        print(f"Processing buffer from {distance}m...")

        buffer_dist_dir = os.path.join(split_layers_dir, f"circular{int(distance)}m_buffer")
        if not os.path.exists(buffer_dist_dir):
            os.makedirs(buffer_dist_dir)

        buffer_convert_dir = os.path.join(convert_format_dir, f"{int(distance)}m_circ")
        if not os.path.exists(buffer_convert_dir):
            os.makedirs(buffer_convert_dir)

        try:
            params_dividir = {
                'INPUT': buffer_path,
                'FIELD': field_id,
                'PREFIX': '',
                'OUTPUT': buffer_dist_dir
            }

            processing.run("native:splitvectorlayer", params_dividir)
            print(f"Layer successfully split using field '{field_id}'")

            for point_id in point_names:
                if point_id not in split_buffers:
                    split_buffers[point_id] = {}

                gpkg_found = False
                for file in os.listdir(buffer_dist_dir):
                    if file.endswith(".gpkg") and str(point_id) in file:
                        gpkg_path = os.path.join(buffer_dist_dir, file)
                        converted_output = os.path.join(buffer_convert_dir, f"{int(distance)}m_circ{point_id}.shp")

                        print(f"Converting {file} for shapefile...")

                        layer = QgsVectorLayer(gpkg_path, "temp", "ogr")
                        if not layer.isValid():
                            print(f"WARNING: Invalid GPKG layer: {gpkg_path}")
                            continue

                        QgsVectorFileWriter.writeAsVectorFormat(
                            layer,
                            converted_output,
                            "UTF-8",
                            layer.crs(),
                            "ESRI Shapefile"
                        )

                        split_buffers[point_id][distance] = converted_output
                        gpkg_found = True
                        break

                if not gpkg_found:
                    print(f"WARNING: Using an alternative approach for the point {point_id}")

                    individual_buffer = os.path.join(buffer_convert_dir, f"{int(distance)}m_circ{point_id}.shp")

                    try:
                        params_buffer = {
                            'INPUT': points,
                            'DISTANCE': distance,
                            'SEGMENTS': 5,
                            'END_CAP_STYLE': 0,
                            'JOIN_STYLE': 0,
                            'MITER_LIMIT': 2,
                            'DISSOLVE': False,
                            'OUTPUT': individual_buffer
                        }

                        processing.run("native:buffer", params_buffer)
                        split_buffers[point_id][distance] = individual_buffer

                    except Exception as e_buffer:
                        print(f"ERROR creating individual buffer for {point_id}: {e_buffer}")

        except Exception as e:
            print(f"ERROR when splitting/converting buffer from {distance}m: {e}")

    # STEP 4: Crop circular buffer by polygon
    print("\n4. Clipping circular buffer by polygon...")

    for point_id in point_names:
        if point_id not in clipped_buffers_temp:
            clipped_buffers_temp[point_id] = {}

        poligono_path = polygons_points_match.get(point_id)

        if not poligono_path:
            print(f"ERROR: Polygon to point {point_id} not found!")
            continue

        for distance in circular_distance_buffer:
            if point_id not in split_buffers or distance not in split_buffers[point_id]:
                print(f"ERRO: Buffer circular de {distance}m to point {point_id} not found!")
                continue

            buffer_path = split_buffers[point_id][distance]
            temp_output = os.path.join(buffer_circ_area_dir, f"temp_recorte_{int(distance)}m_circ{point_id}.shp")

            params_recortar = {
                'INPUT': buffer_path,
                'OVERLAY': poligono_path,
                'OUTPUT': temp_output
            }

            processing.run("native:clip", params_recortar)
            clipped_buffers_temp[point_id][distance] = temp_output

    # STEP 5: Calculate area and classify
    print("\n5. Calculating areas and classifying buffers...")

    for point_id in point_names:
        if point_id not in lca_buffers:
            lca_buffers[point_id] = {}
        if point_id not in extrapolated_areas:
            extrapolated_areas[point_id] = {}

        for distance in circular_distance_buffer:
            if point_id not in clipped_buffers_temp or distance not in clipped_buffers_temp[point_id]:
                continue

            buffer_temp_path = clipped_buffers_temp[point_id][distance]

            buffer_area_path = os.path.join(buffer_circ_area_dir, f"area_buffer_{int(distance)}m_{point_id}.shp")
            area_calculada = calculate_shapefile_area(buffer_temp_path, buffer_area_path)

            if not area_calculada:
                continue

            area_buffer = get_total_area(buffer_area_path)

            if point_id not in polygon_areas:
                print(f"ERRO: Área do polígono to point {point_id} not found!")
                continue

            area_poligono = polygon_areas[point_id]['total_area']

            if area_buffer is not None and area_poligono is not None:
                if abs(area_buffer - area_poligono) < 0.01:
                    # Extrapolated area
                    extrapolated_output = os.path.join(extrapolated_areas_dir, f"LCA_{int(distance)}m_{point_id}.shp")

                    layer = QgsVectorLayer(buffer_area_path, "temp", "ogr")
                    QgsVectorFileWriter.writeAsVectorFormat(
                        layer,
                        extrapolated_output,
                        "UTF-8",
                        layer.crs(),
                        "ESRI Shapefile"
                    )

                    extrapolated_areas[point_id][distance] = extrapolated_output
                    print(f"EXTRAPOLATED AREA: {point_id} - {distance}m")

                elif area_buffer < area_poligono:
                    # Valid area (LCA)
                    lca_output = os.path.join(lca_dir, f"LCA_{int(distance)}m_{point_id}.shp")

                    layer = QgsVectorLayer(buffer_area_path, "temp", "ogr")
                    QgsVectorFileWriter.writeAsVectorFormat(
                        layer,
                        lca_output,
                        "UTF-8",
                        layer.crs(),
                        "ESRI Shapefile"
                    )

                    lca_buffers[point_id][distance] = lca_output
                    print(f"VALID AREA (LCA): {point_id} - {distance}m")
                else:
                    print(f"WARNING: Buffer area larger than polygon area for {point_id} - {distance}m")

# STEPS 6-8: Riparian Buffer
if operation_mode in ["RIPARIAN", "FULL"]:
    # STEP 6: Clip line file by polygon
    print(f"\n6. Clipping {os.path.basename(file_line_detected)} by polygon...")

    for point_id in point_names:
        poligono_path = polygons_points_match.get(point_id)

        if not poligono_path:
            print(f"ERROR: Polygon to point {point_id} not found!")
            continue

        linha_output = os.path.join(clipped_line_dir, f"layer_point{point_id}.shp")

        params_recortar = {
            'INPUT': file_line_detected,
            'OVERLAY': poligono_path,
            'OUTPUT': linha_output
        }

        processing.run("native:clip", params_recortar)
        clipped_line[point_id] = linha_output

    # STEP 7: Generate riparian buffer
    print("\n7. Generating riparian buffer...")

    for point_id, clipped_line_path in clipped_line.items():
        if point_id not in riparian_buffers:
            riparian_buffers[point_id] = {}

        for distance in distances_riparian_buffer:
            riparian_output = os.path.join(riparian_buffer_dir, f"temp_RB_{int(distance)}_{point_id}.shp")

            params_buffer = {
                'INPUT': clipped_line_path,
                'DISTANCE': distance,
                'SEGMENTS': 5,
                'END_CAP_STYLE': 0,
                'JOIN_STYLE': 0,
                'MITER_LIMIT': 2,
                'DISSOLVE': True,
                'OUTPUT': riparian_output
            }

            processing.run("native:buffer", params_buffer)
            riparian_buffers[point_id][distance] = riparian_output

    # STEP 8: Crop riparian buffer by polygon
    print("\n8. Clipping riparian buffer by polygon...")

    for point_id in point_names:
        if point_id not in cropped_riparian:
            cropped_riparian[point_id] = {}

        poligono_path = polygons_points_match.get(point_id)

        if not poligono_path:
            print(f"ERROR: Polygon to point {point_id} not found!")
            continue

        for riparian_distance in distances_riparian_buffer:
            if point_id not in riparian_buffers or riparian_distance not in riparian_buffers[point_id]:
                print(f"ERROR: Riparian buffer from {riparian_distance}m to point {point_id} not found!")
                continue

            riparian_path = riparian_buffers[point_id][riparian_distance]
            cropped_output = os.path.join(amortec_recort_dir, f"RB_{int(riparian_distance)}_{point_id}.shp")

            params_recortar = {
                'INPUT': riparian_path,
                'OVERLAY': poligono_path,
                'OUTPUT': cropped_output
            }

            processing.run("native:clip", params_recortar)
            cropped_riparian[point_id][riparian_distance] = cropped_output

    # STEP 8.1: Apply difference to clipped riparian
    if apply_difference:
        print("\n8.1. Applying difference on clipped riparian buffer...")

        for point_id in point_names:
            if point_id not in cropped_riparian_dif:
                cropped_riparian_dif[point_id] = {}

            if point_id not in clipped_line:
                print(f"AVISO: layer alvo to point {point_id} not found!")
                continue

            target_layer_path = clipped_line[point_id]

            for riparian_distance in distances_riparian_buffer:
                if point_id not in cropped_riparian or riparian_distance not in cropped_riparian[point_id]:
                    continue

                riparian_path = cropped_riparian[point_id][riparian_distance]
                dif_output = os.path.join(amortec_recort_dif_dir, f"RB_{int(riparian_distance)}_{point_id}_dif.shp")

                resultado_dif = apply_difference_operation(riparian_path, target_layer_path, dif_output)
                if resultado_dif:
                    cropped_riparian_dif[point_id][riparian_distance] = resultado_dif

# STEP 9: Cut riparian buffer by LCA
if operation_mode == "FULL":
    print("\n9. Clipping riparian buffer by LCA..")

    for point_id in point_names:
        for circular_distance in circular_distance_buffer:
            if point_id not in lca_buffers or circular_distance not in lca_buffers[point_id]:
                print(f"WARNING: Valid LCA of {circular_distance}m to point {point_id} not found!")
                continue

            lca_path = lca_buffers[point_id][circular_distance]

            for riparian_distance in distances_riparian_buffer:
                if point_id not in cropped_riparian or riparian_distance not in cropped_riparian[point_id]:
                    print(f"ERROR: Cropped riparian from {riparian_distance}m to point {point_id} not found!")
                    continue

                riparian_path = cropped_riparian[point_id][riparian_distance]
                final_output = os.path.join(riparian_lca_dir,
                                            f"LCA_{int(circular_distance)}_RB_{int(riparian_distance)}_{point_id}.shp")

                params_recortar = {
                    'INPUT': riparian_path,
                    'OVERLAY': lca_path,
                    'OUTPUT': final_output
                }

                processing.run("native:clip", params_recortar)

    # STEP 9.1: Apply difference in riparian buffer regarding LCA range
    if apply_difference:
        print("\n9.1. Applying difference in LCA riparian buffer...")

        for point_id in point_names:
            if point_id not in riparian_lca_dif:
                riparian_lca_dif[point_id] = {}

            if point_id not in clipped_line:
                print(f"WARNING: Target layer for point {point_id} not found!")
                continue

            target_layer_path = clipped_line[point_id]

            for circular_distance in circular_distance_buffer:
                for riparian_distance in distances_riparian_buffer:
                    file_amort_lca = os.path.join(riparian_lca_dir,
                                                  f"LCA_{int(circular_distance)}_RB_{int(riparian_distance)}_{point_id}.shp")

                    if not os.path.exists(file_amort_lca):
                        continue

                    dif_output = os.path.join(amortec_lca_dif_dir,
                                              f"LCA_{int(circular_distance)}_RB_{int(riparian_distance)}_{point_id}_dif.shp")

                    resultado_dif = apply_difference_operation(file_amort_lca, target_layer_path, dif_output)
                    if resultado_dif:
                        if circular_distance not in riparian_lca_dif[point_id]:
                            riparian_lca_dif[point_id][circular_distance] = {}
                        riparian_lca_dif[point_id][circular_distance][riparian_distance] = resultado_dif

# Load layers in QGIS
print("\nLoading layers in QGIS...")

QgsProject.instance().removeAllMapLayers()

# 1. Load Points_Collected
points_layer = QgsVectorLayer(points, "Points_Collected", "ogr")
QgsProject.instance().addMapLayer(points_layer)

# 2. Load polygons
print("Loading polygons...")
for point_id, path_polygon in polygons_points_match.items():
    layer_name = f"Poligono_{point_id}"
    layer = QgsVectorLayer(path_polygon, layer_name, "ogr")
    if layer.isValid():
        simbolo = QgsFillSymbol.createSimple({
            'color': '255,255,255,0',
            'outline_color': '0,0,0,255',
            'outline_width': '0.5'
        })
        layer.renderer().setSymbol(simbolo)
        QgsProject.instance().addMapLayer(layer)

# 3. Load polygon areas
if operation_mode in ["CIRCULAR", "FULL"]:
    print("Loading polygon areas...")
    if os.path.exists(final_polygons_area_dir):
        for file in os.listdir(final_polygons_area_dir):
            if file.endswith(".shp"):
                path = os.path.join(final_polygons_area_dir, file)
                layer = QgsVectorLayer(path, f"Area_{file}", "ogr")
                if layer.isValid():
                    simbolo = QgsFillSymbol.createSimple({
                        'color': '255,255,0,100',
                        'outline_color': '255,255,0,255',
                        'outline_width': '0.7'
                    })
                    layer.renderer().setSymbol(simbolo)
                    QgsProject.instance().addMapLayer(layer)

# 4. Load target layer
if operation_mode in ["RIPARIAN", "FULL"]:
    print("Loading target layers for riparian...")
    if os.path.exists(clipped_line_dir):
        for file in os.listdir(clipped_line_dir):
            if file.endswith(".shp"):
                path = os.path.join(clipped_line_dir, file)
                layer = QgsVectorLayer(path, f"Target_{file}", "ogr")
                if layer.isValid():
                    QgsProject.instance().addMapLayer(layer)

# 5. Load specific layers based on mode
if operation_mode in ["CIRCULAR", "FULL"]:
    # Carregar LCA válidas
    print("Loading valid LCA layers...")
    if os.path.exists(lca_dir):
        for file in os.listdir(lca_dir):
            if file.endswith(".shp"):
                path = os.path.join(lca_dir, file)
                layer = QgsVectorLayer(path, f"LCA_Valid_{file}", "ogr")
                if layer.isValid():
                    simbolo = QgsFillSymbol.createSimple({
                        'color': '0,255,0,100',
                        'outline_color': '0,128,0,255',
                        'outline_width': '0.7'
                    })
                    layer.renderer().setSymbol(simbolo)
                    QgsProject.instance().addMapLayer(layer)

    # Load extrapolated areas
    print("Loading extrapolated areas...")
    if os.path.exists(extrapolated_areas_dir):
        for file in os.listdir(extrapolated_areas_dir):
            if file.endswith(".shp"):
                path = os.path.join(extrapolated_areas_dir, file)
                layer = QgsVectorLayer(path, f"Extrapolated_{file}", "ogr")
                if layer.isValid():
                    simbolo = QgsFillSymbol.createSimple({
                        'color': '255,0,0,100',
                        'outline_color': '128,0,0,255',
                        'outline_width': '0.7'
                    })
                    layer.renderer().setSymbol(simbolo)
                    QgsProject.instance().addMapLayer(layer)

if operation_mode == "FULL":
    # Load riparian LCA
    print("Loading LCA riparian layers....")
    if os.path.exists(riparian_lca_dir):
        for file in os.listdir(riparian_lca_dir):
            if file.endswith(".shp"):
                path = os.path.join(riparian_lca_dir, file)
                layer = QgsVectorLayer(path, f"RB_LCA_{file}", "ogr")
                if layer.isValid():
                    simbolo = QgsFillSymbol.createSimple({
                        'color': '0,0,255,100',
                        'outline_color': '0,0,128,255',
                        'outline_width': '0.7'
                    })
                    layer.renderer().setSymbol(simbolo)
                    QgsProject.instance().addMapLayer(layer)

    # Load LCA difference
    if apply_difference and os.path.exists(amortec_lca_dif_dir):
        print("Loading LCA riparian layers with difference...")
        for file in os.listdir(amortec_lca_dif_dir):
            if file.endswith(".shp"):
                path = os.path.join(amortec_lca_dif_dir, file)
                layer = QgsVectorLayer(path, f"RB_LCA_Dif_{file}", "ogr")
                if layer.isValid():
                    simbolo = QgsFillSymbol.createSimple({
                        'color': '128,0,128,100',
                        'outline_color': '64,0,64,255',
                        'outline_width': '0.7'
                    })
                    layer.renderer().setSymbol(simbolo)
                    QgsProject.instance().addMapLayer(layer)

elif operation_mode == "RIPARIAN":
    # Carregar riparian recortado
    print("Loading cropped riparian layers...")
    if os.path.exists(amortec_recort_dir):
        for file in os.listdir(amortec_recort_dir):
            if file.endswith(".shp"):
                path = os.path.join(amortec_recort_dir, file)
                layer = QgsVectorLayer(path, f"RB_{file}", "ogr")
                if layer.isValid():
                    simbolo = QgsFillSymbol.createSimple({
                        'color': '0,0,255,100',
                        'outline_color': '0,0,128,255',
                        'outline_width': '0.7'
                    })
                    layer.renderer().setSymbol(simbolo)
                    QgsProject.instance().addMapLayer(layer)

    # Load riparian difference
    if apply_difference and os.path.exists(amortec_recort_dif_dir):
        print("Loading cropped riparian layers with difference...")
        for file in os.listdir(amortec_recort_dif_dir):
            if file.endswith(".shp"):
                path = os.path.join(amortec_recort_dif_dir, file)
                layer = QgsVectorLayer(path, f"RB_Dif_{file}", "ogr")
                if layer.isValid():
                    simbolo = QgsFillSymbol.createSimple({
                        'color': '0,255,255,100',
                        'outline_color': '0,128,128,255',
                        'outline_width': '0.7'
                    })
                    layer.renderer().setSymbol(simbolo)
                    QgsProject.instance().addMapLayer(layer)

# Centralize view
print("Centralizing visualization...")
try:
    from qgis.utils import iface

    if iface:
        iface.mapCanvas().zoomToFullExtent()
except:
    print("WARNING: Automatic centering was not possible.")

# Final report
print("\n" + "=" * 70)
print("PROCESSING SUCCESSFULLY COMPLETED!")
print("=" * 70)
print(f"MODO: {operation_mode}")
print(f"DIFFERENCE: {'APPLIED' if apply_difference else 'NOT APPLIED'}")
print(f"Results {result_dir}")

print(f"\nMATCHINGS:")
for point_id, path_polygon in polygons_points_match.items():
    print(f"  {point_id} -> {os.path.basename(path_polygon)}")

# Statistics
if operation_mode in ["CIRCULAR", "FULL"]:
    total_lca = sum(len(buffers) for buffers in lca_buffers.values())
    total_extrapolated = sum(len(buffers) for buffers in extrapolated_areas.values())
    print(f"\nSTATISTICS:")
    print(f"- Valid LCAs: {total_lca}")
    print(f"- Areas extrapolated: {total_extrapolated}")
    print(f"- Points processed: {len(point_names)}")

if operation_mode in ["RIPARIAN", "FULL"]:
    total_riparian = sum(len(buffers) for buffers in cropped_riparian.values())
    print(f"- Riparians: {total_riparian}")

    if apply_difference:
        total_RB_dif = sum(len(buffers) for buffers in cropped_riparian_dif.values())
        print(f"- Riparian with a difference: {total_RB_dif}")

if file_line_detected:
    print(f"\nLINE ARCHIVE: {os.path.basename(file_line_detected)}")

print("\nThe layers were loaded in QGIS with customized styles.")
print("=" * 70)