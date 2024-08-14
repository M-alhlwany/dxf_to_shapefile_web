import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from pyproj import CRS

def line_to_polygon(line):
    """تحويل خط مغلق إلى مضلع"""
    if line.is_closed:
        return Polygon(line.coords)
    else:
        return None

def convert_dxfBorder_to_shapefile(dxf_file, excel_file, output_shapefile, crs_code):
    print(f"Loading DXF file: {dxf_file}")

    # تحقق من وجود ملف DXF
    if not os.path.isfile(dxf_file):
        raise FileNotFoundError(f"DXF file not found at {dxf_file}")

    # قراءة ملف DXF
    dxf_data = gpd.read_file(dxf_file)
    print(f"DXF file loaded successfully. Number of geometries: {len(dxf_data)}")
    print(f"Columns in DXF file: {dxf_data.columns.tolist()}")

    # تحقق من وجود ملف Excel
    print(f"Loading Excel file: {excel_file}")
    if not os.path.isfile(excel_file):
        raise FileNotFoundError(f"Excel file not found at {excel_file}")

    # قراءة الشيت الثاني من ملف Excel مع تحديد الترميز إذا كان ضرورياً
    try:
        excel_data = pd.read_excel(excel_file, sheet_name=1)  # استخدام الشيت الثاني
    except Exception as e:
        raise ValueError(f"Failed to load Excel file: {e}")

    print(f"Excel file loaded successfully. Number of records: {len(excel_data)}")
    print(f"Columns in Excel file: {excel_data.columns.tolist()}")

    # توحيد أسماء الأعمدة في DXF ليتوافق مع اسم العمود في Excel
    dxf_data['Layer'] = dxf_data['Layer'].astype(str)
    excel_data['Layer'] = excel_data['Layer'].astype(str)

    # تحقق من وجود العمود 'Layer' في كل من بيانات DXF و Excel
    if 'Layer' not in dxf_data.columns:
        raise KeyError("Column 'Layer' is not found in DXF data")
    if 'Layer' not in excel_data.columns:
        raise KeyError("Column 'Layer' is not found in Excel data")

    # قائمة لتخزين البيانات المدمجة لجميع الطبقات المطلوبة
    all_merged_data = []

    # قائمة الطبقات المطلوبة (يمكن تعديلها بناءً على احتياجاتك)
    layers_to_process = dxf_data['Layer'].unique()

    for layer in layers_to_process:
        # فلترة بيانات DXF بناءً على الطبقة الحالية
        filtered_dxf_data = dxf_data[dxf_data['Layer'] == layer]
        print(f"Filtered DXF data for Layer {layer}. Number of geometries: {len(filtered_dxf_data)}")

        # تحويل الكائنات في DXF إلى النوع المناسب
        geometries = []
        for geom in filtered_dxf_data['geometry']:
            if geom.geom_type == 'LineString':
                # تحويل LineString إلى Polygon إذا كان مغلقاً
                polygon = line_to_polygon(geom)
                if polygon:
                    geometries.append(polygon)
                else:
                    # إذا لم يكن مغلقاً، نحتفظ به كـ LineString
                    geometries.append(geom)
            elif geom.geom_type == 'Polygon':
                geometries.append(geom)
            elif geom.geom_type == 'MultiLineString':
                # تحويل MultiLineString إلى Polygon إذا كان يمكن تشكيله كمضلع
                try:
                    polygon = Polygon([p for line in geom for p in line.coords])
                    if polygon.is_valid:
                        geometries.append(polygon)
                except Exception as e:
                    print(f"Failed to convert MultiLineString to Polygon: {e}")
            else:
                print(f"Unsupported geometry type: {geom.geom_type}")

        # إنشاء GeoDataFrame جديد مع الأنواع المناسبة
        filtered_dxf_data = filtered_dxf_data.copy()
        filtered_dxf_data['geometry'] = geometries
        filtered_dxf_data = gpd.GeoDataFrame(filtered_dxf_data, geometry='geometry')

        # فلترة بيانات Excel بناءً على قيمة 'Layer' المطابقة لاسم الطبقة
        filtered_excel_data = excel_data[excel_data['Layer'] == layer]
        
        if filtered_excel_data.empty:
            print(f"No matching records found in Excel for Layer {layer}")
            continue

        # دمج بيانات DXF مع Excel بناءً على المطابقة بين 'Layer' في كلا الملفين
        merged_data = filtered_dxf_data.merge(filtered_excel_data, on='Layer', how='left')
        print(f"Merging completed for Layer {layer}. Number of merged records: {len(merged_data)}")

        # الاحتفاظ فقط بالحقول من ملف Excel وعمود 'geometry'
        merged_data = merged_data[excel_data.columns.tolist() + ['geometry']]

        # حذف عمود 'Layer' بعد الدمج
        merged_data.drop(columns=['Layer'], inplace=True)
        
        # إضافة البيانات المدمجة إلى القائمة
        all_merged_data.append(merged_data)

    # دمج جميع البيانات المدمجة في DataFrame واحد
    final_data = pd.concat(all_merged_data, ignore_index=True)
    
    # تحويل DataFrame إلى GeoDataFrame
    gdf = gpd.GeoDataFrame(final_data, geometry='geometry')

    # تعيين CRS الأصلي
    original_crs = CRS.from_string(crs_code)  # EPSG:32637 هو EPSG الخاص بنظام الإحداثيات الأصلي
    target_crs = CRS("EPSG:4326")  # EPSG:4326 هو EPSG لنظام الإحداثيات المطلوب
    gdf.crs = original_crs  # تعيين CRS الأصلي

    # تحويل CRS من 32637 إلى 4326
    print("Reprojecting to target CRS...")
    gdf = gdf.to_crs(target_crs.to_string())

    # حفظ البيانات كملف Shapefile مع دعم اللغة العربية
    print(f"Saving data to Shapefile: {output_shapefile}")
    gdf.to_file(output_shapefile, driver='ESRI Shapefile', encoding='utf-8')
    print(f"Shapefile saved successfully at {output_shapefile}")
