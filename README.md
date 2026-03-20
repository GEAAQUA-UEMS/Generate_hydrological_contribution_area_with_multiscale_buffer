
# README - Generate_hydrological_contribution_area_with_multiscale_buffer.py

## General Description

This script was developed to be executed exclusively in the QGIS environment (version 3.34.5).

It was developed to generate Exclusive Contribution Areas (ECAs) from multiple environmental monitoring points and, 
subsequently, create multiscale Buffers within each ECA.

## More Specifically

It delineates watersheds using multiple outlet points within the stream segment.

Based on the delineated basins, the "Difference" tool is executed iteratively between intersecting polygons, prioritizing those with a higher elevation value.

As a result, polygons that previously encompassed the areas of others are reduced in size, ensuring that none have overlapping areas 
(thus generating multiple Exclusive Contribution Areas (ECAs)).

It executes the "Buffer" tool using a spreadsheet (.xls), allowing the user to add as many rows as needed for each buffer type.

As a result, delineations are generated at various scales: Riparian Buffer (RB), Local Contributing Area (LCA), and Riparian Buffer in Local Contributing Area (RBLCA).

This is made possible by iteratively using existing tools (r.watershed, r.water.outlet, Polygonize, Fix Geometries, Dissolve, Zonal Statistics, Difference, Buffer, 
Split Vector Layer, Convert Format, and Clip) in QGIS, combined with additional commands.

**Important:** This script cannot be executed outside the QGIS environment. It utilizes internal libraries and tools, such as the QGIS `processing` framework.

## Authors

- Henrique Ledo Lopes Pinho
- Jéssica Bassani de Oliveira
- Yzel Rondon Suarez

## Requirements

- **QGIS:** Version 3.34.5
- **Operating Systems:** Windows or Linux.

## Installation and Setup

1. In QGIS, install and/or enable the GRASS plugin:
   - Go to: `Plugins` > `Manage and Install Plugins`
   - Search for "GRASS GIS provider" and install it.

## Required Files

All input files must be in the same planar projection system (we used UTM).

- **DEM (Digital Elevation Model):** A `.tif` file; pre-processed (mosaicked, clipped, corrected for negative values, filled no-data pixels, and removed spurious depressions).
- **Plot the data collected in the field** and generate the stream segment to obtain the outlet points near the actual collection points (if you encounter issues generating the stream segment in version 3.34, perform this step in version 3.16).
- **Outlet Coordinates:** A `.txt` file with coordinates in `x,y` format.
- **Point Shapefile within the stream segment:** A `.shp` file containing a column named "Pontos" with the names of the points.
- **Points in Shapefile format** (in this case, referring to the field monitoring sites and not necessarily within the stream segment).
- **Spreadsheet in ".xlsx" format,** containing user-defined parameters with the buffer type and necessary distances.
- **Line or polygon file in Shapefile format** (in this case, representing the drainage network, river, lake, etc.).

## Project Structure

- `DEM.tif` - Digital elevation model raster.
- `EXUTORY_COORDINATES.txt` - File with the coordinates of the outlets.
- `points_in_stream_segments.shp` - Shapefile with points on the stream segments.
- `stream_segment.tif` - (Optional) The script does not require this layer to be saved in a specific directory to work. However, we recommend that the user saves this layer to disk, as this makes it easier to visually check that the points are correctly positioned in the pixel corresponding to the stream segment.
- `INTERMEDIARY_FILES/` - Folder for intermediate output files.
- `FINAL_POLYGONS/` - Folder for the final output files (Exclusive Contribution Areas).
- `/multiscale_parameters.xlsx` - Excel spreadsheet with parameters (buffer distances).
- `/RESULT_MULTI` - Folder for the output files, where the results are stored.
- `/Collected_on_site.shp` - Points from the monitoring collection site.
- `/DRAINAGE` - Folder containing the hydrological representation file (line or polygon).
- `apply_difference = ` # True --> apply difference; False --> do not apply (generally used when the user uses a polygon as the water representation layer and wishes to exclude the water body from the analysis).

## Running the Script

1. Open QGIS.
2. Go to `Plugins` > `Python Console`.
3. Copy and paste the content of the `Script.py` file into the QGIS Python console, or open the .py file through the console.
4. Select all commands (CTRL+A) and press `Enter` to execute.

## Generated Outputs

**The number of outputs will depend on the quantity and type of parameters defined by the user, but the complete process consists of:**
**(here, "x" represents a value in meters to be defined by the user, and [Point] identifies a specific point)**

- `drainage_direction.tif` - Drainage direction.
- `basin_[Point].shp` - Delimited basins for each outlet point.
- `dissolved_basin_[Point].shp` - Basins with corrected geometries.
- `zonal_basin_[Point].shp` - Shapefile with zonal statistics.
- `influence_area_[Point].shp` - Individual basins after applying the difference between overlapping areas (influence area of each point).
- `RESULT_MULTI/1BUFFER_CIRCULAR/circular_"x"m.shp` - Circle around the point.
- `RESULT_MULTI/2SPLIT_LAYERS/circular"x"m_buffer/point_Point"x".gpkg` - Split circular layers for each point.
- `RESULT_MULTI/3CONVERT_FORMAT/"x"m_circ/"x"m_circPoint"x".shp` - Converts circular buffer layers from ".gpkg" to ".shp".
- `RESULT_MULTI/4LCA_Temporary/area_buffer_"x"m_Point"x".shp` - Clips the circular buffers by the contribution area polygon of each point and calculates the area.
- `RESULT_MULTI/5LCA_Definitive/LCA_"x"m_Point"x".shp` - Stores only the LCAs with an area value smaller than the general delineation polygon.
- `RESULT_MULTI/6TARGET_LAYER_FOR_RIPARIAN_BUFFER/layer_pointPoint"x".shp` - Clips the hydrological representation file within the delineation of each point.
- `RESULT_MULTI/7RB_Temporary/temp_RB_"x"_Point"x"` - Generates a riparian buffer from the hydrological representation file.
- `RESULT_MULTI/8RB_Definitive/RB_"x"_Point"x"` - Clips the excess riparian buffer by the general delineation of each point.
- `RESULT_MULTI/9RBLCA/LCA_"x"_RB_"x"_Point"x"` - Stores the RBLCA.
- `RESULT_MULTI/ECA_WITH_AREA` - Stores the area calculation data for each polygon corresponding to the general delineation of each point.
- `RESULT_MULTI/LCA_EXTRAPOLATED_AREAS/LCA_"x"m_Point"x"` - Stores only the LCAs with an area value greater than their general delineation polygon.

## Priority Outputs

- `FINAL_POLYGONS/`
- `RESULT_MULTI/5LCA_Definitive/LCA_"x"m_Point"x".shp` --> LCA
- `RESULT_MULTI/8RB_Definitive/RB_"x"_Point"x"` --> RB
- `RESULT_MULTI/9RBLCA/LCA_"x"_RB_"x"_Point"x"` --> RBLCA

## Recommendations and Precautions

1.  **Do not change the code's indentation:** Changes can cause errors.
2.  **Correct the geometry of all input files** before starting the process.
3.  **Ensure that each point is within its respective general delineation.**
4.  **Check that the names and number of points match the general delineations.**
5.  **Verify the configuration paths:** Use forward slashes `/` to avoid system errors.
6.  **Do not use spaces or special characters** (ç, ã, é, #, @, etc.) in filenames or paths.
7.  **Avoid very long names** (more than 30 characters may cause issues).
8.  **Correct Formats:**
    - Coordinate file: `.txt` with `x,y` separated by a comma.
    - Point Shapefile: Must contain a column named "Pontos".
9.  **Permissions:** Ensure that the output directory has write permissions.
10. **If the study area has flat slopes with low variation in elevation,** the stream segment will be less accurately aligned with the actual water course, and this is due to the limited spatial resolution of the DEM and not due to algorithmic limitations.
11. This script cannot be executed outside the QGIS environment. It uses internal libraries and tools, such as QGIS `processing` and the GRASS and GDAL modules.

## Troubleshooting

1.  **Error loading point layer:** Check the file path and its integrity (planar projection).
2.  **Error in coordinates:** Confirm the `x,y` format without extra spaces.

## Situations Where the Algorithm WILL NOT WORK:

- Using versions prior to 3.34-Prizren to run the script.
- Non-planar Coordinate Reference Systems.
- Different Coordinate Reference Systems among the input files.
- Outlet coordinates located outside the stream segment's pixel.
- Spaces in the `.txt` coordinate file.
- Column names that are different from the example file.
- The coordinates of the outlet points are different from those in the .shp file.
- Trying to run it a second time without deleting the "INTERMEDIARY_FILES" and "FINAL_POLYGONS" folders.
- Trying to run it a second time without deleting the "RESULT_MULTI" folder.
- Not following the "## Recommendations and Precautions" section.

## Institutional Support and Partnerships

- State University of Mato Grosso do Sul (UEMS), Dourados, Brazil
- Center for Natural Resources Studies (CERNA-UEMS), Dourados, Brazil
- Graduate Program in Natural Resources (PGRN-UEMS), Dourados, Brazil
- Bachelor's Course in Information Systems (UEMS), Dourados, Brazil
- Laboratory of Studies in Aquatic Environments (GEAAQUA - UEMS), Dourados, Brazil
- Technological Innovation Center of the State University of Mato Grosso do Sul (NIT-UEMS), Brazil

## Funding Agencies

- Coordination for the Improvement of Higher Education Personnel (CAPES), Brazil
- National Council for Scientific and Technological Development (CNPq), Brazil
- Foundation for the Support of Education, Science and Technology of the State of Mato Grosso do Sul (Fundect), Brazil

## Contact

For support or questions, please contact one of the authors via email: geaaqua@uems.br

---

## License

This program is free software; you can redistribute it and/or modify it under the terms of the GNU 
General Public License as published by the Free Software Foundation; either version 2 of the License, 
or (at your option) any later version.
