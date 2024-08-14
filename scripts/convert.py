import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, LineString
from pyproj import CRS

def line_to_polygon(line):
    """Convert a closed LineString to a Polygon"""
    if line.is_closed:
        return Polygon(line.coords)
    else:
        return None

def convert_dxf_to_shapefile(dxf_file, xlsx_file, output_shapefile, crs_code):
    print(f"Loading DXF file: {dxf_file}")

    # Check if the DXF file exists
    if not os.path.isfile(dxf_file):
        raise FileNotFoundError(f"DXF file not found at {dxf_file}")

    # Read the DXF file
    dxf_data = gpd.read_file(dxf_file)
    print(f"DXF file loaded successfully. Number of geometries: {len(dxf_data)}")
    print(f"Columns in DXF file: {dxf_data.columns.tolist()}")

    # Check if the Excel file exists
    print(f"Loading Excel file: {xlsx_file}")
    if not os.path.isfile(xlsx_file):
        raise FileNotFoundError(f"Excel file not found at {xlsx_file}")

    # Read the Excel file
    try:
        xlsx_data = pd.read_excel(xlsx_file)
    except Exception as e:
        raise RuntimeError(f"Failed to read Excel file: {e}")

    print(f"Excel file loaded successfully. Number of records: {len(xlsx_data)}")
    print(f"Columns in Excel file: {xlsx_data.columns.tolist()}")

    # Define the schema for the final GeoDataFrame
    schema = {
        'geometry': 'Polygon',
        'properties': {
            'REALESTATE': 'str',
            'ISACTIVE': 'int',
            'REALESTA_1': 'int',
            'NEIGHBOURH': 'str',
            'REGION_ID': 'str',
            'CITY_ID': 'str',
            'ADDRESS': 'str',
            'UNIT_DETAI': 'str',
            'USAGE': 'str',
            'ISBUILDING': 'int',
            'BUILDINGTY': 'int',
            'REMARKS': 'str',
            'LAYOUT': 'str',
            'PLOT_ID': 'str',
            'BLOCK_NO': 'str',
            'PLAN_NO': 'str',
            'PLOT_NO1': 'str',
            'PLOT_NO2': 'str',
            'PLOT_NO3': 'str',
            'PLOT_NO4': 'str',
            'PLOT_NO5': 'str',
            'PLOT_NO6': 'str',
            'PARENT_ID': 'str',
            'AREA_SQM': 'float',
            'REQUEST_TY': 'str',
            'REQUEST_NO': 'str',
            'REPORT_NO': 'str',
            'Shape_Leng': 'float',
            'Shape_Area': 'float'
        }
    }

    # Create an empty GeoDataFrame with the defined schema
    final_gdf = gpd.GeoDataFrame(columns=list(schema['properties'].keys()) + ['geometry'])
    final_gdf = final_gdf.astype({col: dtype for col, dtype in schema['properties'].items()})

    # Convert the geometry column to appropriate type
    final_gdf['geometry'] = None

    # Process geometries and merge with Excel data
    geometries = []
    for index, row in dxf_data.iterrows():
        geom = row['geometry']
        if geom.geom_type == 'LineString':
            polygon = line_to_polygon(geom)
            if polygon:
                geometries.append(polygon)
        elif geom.geom_type == 'Polygon':
            geometries.append(geom)
        elif geom.geom_type == 'MultiLineString':
            try:
                polygon = Polygon([p for line in geom for p in line.coords])
                if polygon.is_valid:
                    geometries.append(polygon)
            except Exception as e:
                print(f"Failed to convert MultiLineString to Polygon: {e}")
        else:
            print(f"Unsupported geometry type: {geom.geom_type}")

    # Create GeoDataFrame from processed geometries
    processed_data = pd.DataFrame({'geometry': geometries})

    # Add the Excel data to the processed data
    final_gdf = gpd.GeoDataFrame(processed_data, geometry='geometry')

    # Merge DXF and Excel data
    final_gdf = final_gdf.merge(xlsx_data, left_index=True, right_index=True, how='left')

    # Ensure data types match the schema and handle null values
    for col, dtype in schema['properties'].items():
        if col in final_gdf.columns:
            if dtype == 'int':
                final_gdf[col] = pd.to_numeric(final_gdf[col], errors='coerce').astype('Int64')  # Convert to nullable integer
            elif dtype == 'float':
                final_gdf[col] = pd.to_numeric(final_gdf[col], errors='coerce').astype('float64')
            elif dtype == 'str':
                final_gdf[col] = final_gdf[col].astype('str').fillna(pd.NA).replace('nan', '')  # Replace NaNs with empty string
                # Remove decimal places from numeric strings
                final_gdf[col] = final_gdf[col].str.replace('.0', '')
            else:
                raise ValueError(f"Unsupported data type: {dtype}")

    # Remove any extra columns that are not in the schema
    final_gdf = final_gdf[[col for col in list(schema['properties'].keys()) + ['geometry'] if col in final_gdf.columns]]

    # Assign original CRS and reproject to target CRS
    original_crs = CRS.from_string(crs_code)
    target_crs = CRS("EPSG:4326")
    final_gdf.crs = original_crs

    print("Reprojecting to target CRS...")
    final_gdf = final_gdf.to_crs(target_crs.to_string())

    # Save to Shapefile
    print(f"Saving data to Shapefile: {output_shapefile}")
    final_gdf.to_file(output_shapefile, driver='ESRI Shapefile', encoding='utf-8')
    print(f"Shapefile saved successfully at {output_shapefile}")
