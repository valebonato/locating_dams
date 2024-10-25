
1. Input files:

-	clone map, ldd map (river network), cell area map, and hydrolakes map
-	“existing_reservoirs_v2024-04-26_no-headers.csv” "future_reservoirs_v2024-04-26_no-headers.csv” with the sorted reservoirs.
The file “existing_reservoirs_v2024-04-26_no-headers.csv” takes into consideration only the existing dams with reservoir size > 0. We didn’t consider the dams with NULL capacity because they are either run of the river hydropower (their interference with the hydrology is assumed negligible) or we don’t have their coordinates. 
The file “existing_reservoirs_v2024-04-26_no-headers.csv” contains ID, catchment, lat, long, reservoir size and surface area. We save it as a csv file, all data have maximum 5 decimals and there are no headers as it would interfere with some commands. 
The data are sorted based on two criteria from the AHA_UpdatedArea_v2024-04-26.xlsx:
1)	Catchment area
2)	Reservoir size 
After the sorting we gave an ID for each dam, where the smallest ID has the largest value of catchment area.


2. Scripts:

locate_dams_and_reservoirs-part1_existing.py
-converts specific columns from the input file into PCRaster maps. These columns contain information about dam IDs, catchment areas, latitudes, longitudes, surface areas of reservoirs.
- Over each dam ID:
-	Evaluates the relative difference in catchment areas between the input data and the catchment area from the model. 
-	Corrects the location of the dam if the difference exceeds a certain threshold by expanding the search to the surrounding 3x3 window to find a new location with a more similar catchment area.
-	If there are several candidate positions, choose the one closest to the original coordinates provided.
- It saves the corrected dam IDs and their catchment areas into PCRaster maps. It also generates a text file with the corrected dam IDs and their catchment areas.

existing_locate_dams_and_reservoirs_2nd_part.py: 
- defines the number of grid cells per reservoirs.
- overlay of PCR-GLOBWB water bodies with AHA, so those reservoirs that are already present in the model with the correct number of grid cells will be selected.
- for those that are not in the PCR-GLOBWB water bodies file (some of the existing ones and all future ones) we would fetch the appropriate number of grid cells. Reservoirs larger than one grid cell will be expanded to more grid cells following the river network (thus taking upstream grid cells).

The same process is done for the future reservoirs with the other two scripts

