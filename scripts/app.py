import os
import zipfile
import tempfile
from flask import Flask, request, send_from_directory, after_this_request
from werkzeug.utils import secure_filename
from convert import convert_dxf_to_shapefile
from convert00 import convert_dxfBorder_to_shapefile

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure output folder exists

@app.route('/')
def index():
    return send_from_directory(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static')), 'index.html')

@app.route('/convert', methods=['POST'])
def convert_files():
    try:
        # Retrieve files and CRS code from request
        parcel_file = request.files.get('parcel_file')
        border_file = request.files.get('border_file')
        excel_file = request.files.get('excel_file')
        crs_code = request.form.get('crs_code')

        if not all([parcel_file, border_file, excel_file, crs_code]):
            return "Missing one or more required files or fields.", 400

        # Save files temporarily
        parcel_filename = secure_filename(parcel_file.filename)
        border_filename = secure_filename(border_file.filename)
        excel_filename = secure_filename(excel_file.filename)

        parcel_path = os.path.join(tempfile.gettempdir(), parcel_filename)
        border_path = os.path.join(tempfile.gettempdir(), border_filename)
        excel_path = os.path.join(tempfile.gettempdir(), excel_filename)

        parcel_file.save(parcel_path)
        border_file.save(border_path)
        excel_file.save(excel_path)

        # Define output file paths directly in the output folder
        parcel_shapefile_base = os.path.join(tempfile.gettempdir(), 'parcel')
        border_shapefile_base = os.path.join(tempfile.gettempdir(), 'border')

        # Create directories if they don't exist
        os.makedirs(parcel_shapefile_base, exist_ok=True)
        os.makedirs(border_shapefile_base, exist_ok=True)

        # Convert files
        convert_dxf_to_shapefile(parcel_path, excel_path, parcel_shapefile_base, crs_code)
        convert_dxfBorder_to_shapefile(border_path, excel_path, border_shapefile_base, crs_code)

        # Create a ZIP file
        zip_path = os.path.join(UPLOAD_FOLDER, 'shape.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Add all files of the shapefile (shp, shx, dbf, prj, etc.) to the ZIP
           for shapefile_base in [parcel_shapefile_base, border_shapefile_base]:
                for ext in ['shp', 'shx', 'dbf', 'prj', 'cpg', 'qix']:
                    file_path = f"{shapefile_base}.{ext}"
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.relpath(file_path, tempfile.gettempdir()))
                        print(f"Adding {file_path} to zip")
                    else:
                        print(f"File {file_path} not found, skipping...")

        # Cleanup temporary files
        os.remove(parcel_path)
        os.remove(border_path)
        os.remove(excel_path)

        # Schedule deletion of the ZIP file and output files after request is complete
        @after_this_request
        def remove_files(response):
            try:
                os.remove(zip_path)
                # Remove individual files
                for shapefile_base in [os.path.join(UPLOAD_FOLDER, 'parcel'), os.path.join(UPLOAD_FOLDER, 'border')]:
                    for ext in ['shp', 'shx', 'dbf', 'prj', 'cpg', 'qix']:
                        file_path = f"{shapefile_base}.{ext}"
                        if os.path.exists(file_path):
                            os.remove(file_path)
                print("Temporary files removed successfully.")
            except Exception as e:
                print(f"Error removing files: {e}")
            return response

        # Send ZIP file to user
        return send_from_directory(UPLOAD_FOLDER, 'shape.zip', as_attachment=True)

    except Exception as e:
        # Return a generic error message and log the error
        print(f"Error: {e}")
        return f"An error occurred: {e}", 500
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
