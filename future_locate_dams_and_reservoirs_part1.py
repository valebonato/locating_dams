# FIRST PART OF THE SCRIPT THAT CORRECTS DAMS POSITION
# PCRaster: Python package for spatial modeling

import os
import sys
import shutil

import pcraster as pcr
import virtualOS as vos

# table/column input file - this should be sorted based on reservoir capacities (the largest the lower ids)
column_input_file = "../aha_hydropowers/future_reservoir_v2024-04-26_no-headers.csv"

# ~ # - for testing with 74 and 85 (multiple pixel problem)
# ~ column_input_file = "../aha_hydropowers/existing_reservoirs_v2024-04-10_selected_no-headers-test74and85.csv"


# set the clone (your map grid system and extent)
clone_map_file = "../pcrglobwb_maps/lddsound_05min_version_20210330.map"
pcr.setclone(clone_map_file)

# ldd map (river network)
ldd_map_file = "../pcrglobwb_maps/lddsound_05min_version_20210330.map"
ldd_map = pcr.readmap(ldd_map_file)

# cell area
cell_area_file = "../pcrglobwb_maps/cdo_gridarea_clone_global_05min_correct_lats.nc.map"
cell_area = pcr.readmap(cell_area_file)

# Calculate catchment area (in km2) based on pcrglobwb ldd
# catchmenttotal calculates for each cell the accumulated amount of material that flows out of the cell into its neighbouring downstream cell
# this accumulated amount is the amount of material in the cell itself plus the amount of material in upstream cells of the cell 
catchment_area_km2 = pcr.catchmenttotal(cell_area, ldd_map) / (1000.*1000.)

# Convert table/column to a pcraster map of catchment areas based on AHA
# -x -y are the column numbers of the x,y coordinates in columnfile
# -v is the column number of the cell values in columnfile
# -s to specify the separator in the columnfile is ;
# -S is to assign the datatype "scalar" to the result
# -M to assign lowest value found for the cell (so the biggest catchment area value is choosen)
cmd = "col2map --clone " + clone_map_file + " -M -x 4 -y 3 -v 2 -S -s ',' " + column_input_file + " aha_catchment_area_km2.map"
print(cmd); os.system(cmd)
# - read aha_catchment_area_km2 as a variable
aha_catchment_area_km2 = pcr.readmap("aha_catchment_area_km2.map") 

# convert table/column to a pcraster map of dam ids
cmd = "col2map --clone " + clone_map_file + " -M -x 4 -y 3 -v 1 -S -s ',' " + column_input_file + " dam_ids.map" 
print(cmd); os.system(cmd)
# - read dam ids as a variable
dam_ids = pcr.readmap("dam_ids.map") 

# convert table/column to a pcraster map of the latitude coordinates based on AHA
cmd = "col2map --clone " + clone_map_file + " -M -x 4 -y 3 -v 3 -S -s ',' " + column_input_file + " aha_latitudes.map"
print(cmd); os.system(cmd)
# - read as a variable
aha_latitudes = pcr.readmap("aha_latitudes.map") 

# convert table/column to a pcraster map of the latitude coordinates based on AHA
cmd = "col2map --clone " + clone_map_file + " -M -x 4 -y 3 -v 4 -S -s ',' " + column_input_file + " aha_longitudes.map"
print(cmd); os.system(cmd)
# - read as a variable
aha_longitudes = pcr.readmap("aha_longitudes.map") 

# get the pcrglobwb catchment area for every dam id
dam_ids_pcrglobwb_catchment_area_km2 = pcr.ifthen(pcr.defined(dam_ids), catchment_area_km2)

# calculate the relative difference between two catchment areas
rel_dif_catchment_area = pcr.abs(aha_catchment_area_km2 - dam_ids_pcrglobwb_catchment_area_km2) / dam_ids_pcrglobwb_catchment_area_km2

# loop through all dams (from the largest to the smallest), if rel_dif_catchment_area > threshold, we have to reposition it
threshold = 0.1
number_of_dams = 124

# ~ # for testing
# ~ number_of_dams = 10
# ~ number_of_dams = 2

# Spherical distance (or geodesic distance) on the Earth's sphere, calculated using the arch formula. 
# the distance between points in metres is returned by multiplying the fraction of the Earth's circumference represented by the calculated angle by the Earth's radius (approximately 6371 km).
def get_distances_to_a_reference_latlon_coodinate_in_meter(lon_pcrmap, lat_pcrmap, lon_ref, lat_ref):
    pcr_distance_map = pcr.scalar(pcr.acos(pcr.sin(lat_pcrmap)*pcr.sin(lat_ref) + pcr.cos(lat_pcrmap)*pcr.cos(lat_ref)*pcr.cos(lon_ref - lon_pcrmap)))/360.*6371000. 
    return pcr_distance_map


for dam_id in range(1, number_of_dams + 1):
    
    
    # Make a point map of this dam by assigning the Boolean value 1.0 to the cell where the dam_ids map matches the specified dam_id
    this_dam_point = pcr.ifthen(dam_ids == dam_id, pcr.boolean(1.0))
    
    # evaluate relative difference for this particular dam
    rel_dif_catchment_area_this_dam = pcr.ifthen(this_dam_point, rel_dif_catchment_area)
    # - get its cell value
    rel_dif_catchment_area_this_dam_cell_value = pcr.cellvalue(pcr.mapmaximum(rel_dif_catchment_area_this_dam),1)[0]
    
    # Correcting the location of dam
    if rel_dif_catchment_area_this_dam_cell_value < threshold:
        
        # return a map in which only the cell corresponding to the dam position has the dam ID as its value
        location_corrected_dam_id = pcr.ifthen(this_dam_point, pcr.nominal(dam_id))
        
    else:
    
        # Expanding the point to its neighbours
        
        # 5 arcminutes are 5/60 of one degree and the resolution of the model, multiplying by 3 we have a 3*3 search window
        # the command windowmajority is needed only to inizialize the window: since we only have one value in the middle of the window, all the 9 cells will get the same number
        # we could have used other commands as windowmaximum and the results would be the same
        
        # windowmajority: for each cell a square window with the cell in its centre is defined by windowlength 
        # the most often occurring cell value within its window is determined and assigned to the corresponding cell in the centre
        # both cells entirely or partly in the window are considered
        # if two or more values occur the same (largest) number of times in its window, the windowlength at that cell is increased with two times the celllength of expression
        # just to inizialize, it gives all the same values inside the 9 cells since there is only one ell with a value in this_dam_point
        print(dam_id)
        
        search_window = pcr.windowmajority(this_dam_point, 5./60. * 3.)
        # - note using the window_length = 2 to avoid 'too large' window size
        
        # Get the pcrglobwb catchment area within this search_window
        # the cells in the search_window have values taken from the corresponding catchment_area_km2 map, and all other cells are set to null.
        catchment_area_within_search_window = pcr.ifthen(pcr.defined(search_window), catchment_area_km2)
        
        # compare the above to aha catchment_area
        aha_catchment_area_km2_this_dam = pcr.ifthen(this_dam_point, aha_catchment_area_km2)
        aha_catchment_area_km2_this_dam = pcr.windowmaximum(aha_catchment_area_km2_this_dam, 5./60 * 3.)

        # calculate the absolute difference
        difference_catch_area = pcr.abs(catchment_area_within_search_window - aha_catchment_area_km2_this_dam)
        
        location_corrected_dam_id = pcr.ifthen(difference_catch_area == pcr.mapminimum(difference_catch_area), pcr.nominal(dam_id))
        

        # make sure that there is only one pixel in location_corrected_dam_id; if this is NOT the case, we just find the closest one to the original coordinates 

        # - get the latitude and longitude coordinates based on AHA, and transfer them to single values maps (using mapmaximum)
        lat_aha_coordinate = pcr.mapmaximum(pcr.ifthen(dam_ids == dam_id, aha_latitudes))
        lon_aha_coordinate = pcr.mapmaximum(pcr.ifthen(dam_ids == dam_id, aha_longitudes))
        
        # - calculate the distance of every candidate point to the AHA coordinate
        distance_map = get_distances_to_a_reference_latlon_coodinate_in_meter(lon_pcrmap = pcr.xcoordinate(pcr.defined(location_corrected_dam_id)),\
                                                                              lat_pcrmap = pcr.ycoordinate(pcr.defined(location_corrected_dam_id)),\
                                                                              lon_ref = lon_aha_coordinate,\
                                                                              lat_ref = lat_aha_coordinate)
        area_order = pcr.areaorder(distance_map, location_corrected_dam_id)
        # - choose the one with shortest distance (order/rank = 1)
        location_corrected_dam_id = pcr.ifthen(area_order == 1, pcr.nominal(dam_id))
        
    if dam_id == 1:    
        all_location_corrected_dam_ids = location_corrected_dam_id
    else:
        all_location_corrected_dam_ids = pcr.cover(all_location_corrected_dam_ids, location_corrected_dam_id)

# save the all_location_corrected_dam_ids to a pcraster map
pcr.report(all_location_corrected_dam_ids, "corrected_dam_ids_future.map")

# obtain the catchment areas of all_location_corrected_dam_ids
corrected_dam_catchment_area_km2 = pcr.ifthen(pcr.defined(all_location_corrected_dam_ids), catchment_area_km2)
pcr.report(corrected_dam_catchment_area_km2, "corrected_dam_catchment_area_km2_future.map")

# obtain a table/column format for all_location_corrected_dam_ids and corrected_dam_catchment_area_km2
cmd = "map2col corrected_dam_ids_future.map corrected_dam_catchment_area_km2_future.map corrected_dams_future.txt"
print(cmd); os.system(cmd)        


