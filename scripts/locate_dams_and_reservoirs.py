#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil

import pcraster as pcr
import virtualOS as vos

# table/column input file - this should be sorted based on reservoir capacities (the largest the lower ids)
column_input_file = "../aha_hydropowers/existing_reservoirs_v2024-03-26_no-headers.csv"

# set the clone (your map grid system and extent)
clone_map_file = "/scratch-shared/edwin/valentina/ldd/lddsound_05min_version_20210330.map"
pcr.setclone(clone_map_file)

# ldd map (river network)
ldd_map_file = "/scratch-shared/edwin/valentina/ldd/lddsound_05min_version_20210330.map"
ldd_map = pcr.readmap(ldd_map_file)

# cell area
cell_area_file = "../aha_hydropowers/cdo_gridarea_clone_global_05min_correct_lats.nc.map"
cell_area = pcr.readmap(cell_area_file)

# calculate catchment area (in km2) based on pcrglobwb ldd
catchment_area_km2 = pcr.catchmenttotal(cell_area, ldd_map) / (1000.*1000.)

# convert table/column to a pcraster map of dam ids
cmd = "col2map " + clone_map_file + "-M -x 4 -y 3 -v 1 " + column_input_file + "dam_ids.map" 
print(cmd); os.system(cmd)
# - read dam ids as a variable
dam_ids = pcr.readmap("dam_ids.map") 

# convert table/column to a pcraster map of catchment areas based on AHA
cmd = "col2map " + clone_map_file + "-M -x 4 -y 3 -v 2 " + column_input_file + "aha_catchment_area_km2.map"
print(cmd); os.system(cmd)
# - read aha_catchment_area_km2 as a variable
aha_catchment_area_km2 = pcr.readmap("aha_catchment_area_km2.map") 

# get the pcrglobwb catchment area for every dam id
dam_ids_pcrglobwb_catchment_area_km2 = pcr.ifthen(pcr.defined(dam_ids), catchment_area_km2)

# calculate the relative difference between two catchment areas
rel_dif_catchment_area = pcr.abs(aha_catchment_area_km2 - dam_ids_pcrglobwb_catchment_area_km2) / dam_ids_pcrglobwb_catchment_area_km2

# loop through all dams (from the largest to the smallest), if rel_dif_catchment_area > threshold, we have to reposition it
threshold = 0.1
number_of_dams = 132
for dam_id in range(1, number_of_dams + 1):
    
    print(dam_id)
    
    # make a point map of this dam
    this_dam_point = pcr.ifthen(dam_ids == dam_id, pcr.boolean(1.0))
    
    # evaluate relative difference for this particular dam
    rel_dif_catchment_area_this_dam = pcr.ifthen(this_dam_point, rel_dif_catchment_area)
    # - get its cell value
    rel_dif_catchment_area_this_dam_cell_value = pcr.cellvalue(pcr.mapmaximum(rel_dif_catchment_area_this_dam),1)[0]
    
    if rel_dif_catchment_area_this_dam_cell_value < threshold:

        location_corrected_dam_id = pcr.ifthen(this_dam_point, pcr.nominal(dam_id))
        
    else:
    
        # expanding the point to 3 x 3 window size of 5 arcmin
        search_window = pcr.windowmajority(this_dam_point, 5./60. * 3.)
        
        # get the pcrglobwb catchment area within this search_window
        catchment_area_within_search_window = pcr.ifthen(pcr.defined(search_window), catchment_area_km2)
        
        # compare the above to aha catchment_area
        aha_catchment_area_km2_this_dam = pcr.ifthen(this_dam_point, aha_catchment_area_km2)
        aha_catchment_area_km2_this_dam = pcr.windowmaximum(aha_catchment_area_km2_this_dam, 5./60 * 3.)

        # calculate the absolute difference
        difference_catch_area = pcr.abs(catchment_area_within_search_window - aha_catchment_area_km2_this_dam)
        
        location_corrected_dam_id = pcr.ifthen(difference_catch_area == pcr.mapminimum(difference_catch_area), pcr.nominal(dam_id))
        
    if dam_id == 1:    
        all_location_corrected_dam_ids = location_corrected_dam_id
    else:
        all_location_corrected_dam_ids = pcr.cover(all_location_corrected_dam_ids, location_corrected_dam_id)

# save the all_location_corrected_dam_ids to a pcraster map
pcr.report(all_location_corrected_dam_ids, "corrected_dam_ids.map")

# obtain the catchment areas of all_location_corrected_dam_ids
corrected_dam_catchment_area_km2 = pcr.ifthen(pcr.defined(all_location_corrected_dam_ids), catchment_area_km2)
pcr.report(corrected_dam_catchment_area_km2, "corrected_dam_catchment_area_km2.map")

# obtain a table/column format for all_location_corrected_dam_ids and corrected_dam_catchment_area_km2
cmd = "map2col corrected_dam_ids.map corrected_dam_catchment_area_km2.map corrected_dams.txt"
print(cmd); os.system(cmd)        


