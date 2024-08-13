from flask import Flask, render_template, request, send_from_directory, abort
from werkzeug.utils import secure_filename
import os
import tempfile
import pandas as pd
from convert import convert_dxf_to_shapefile
from convert00 import convert_dxfBorder_to_shapefile

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # إنشاء مجلد output إذا لم يكن موجودًا

@app.route('/')
def index():
    return send_from_directory(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static')), 'index.html')

@app.route('/convert', methods=['POST'])
def convert_files():
    try:
        parcel_file = request.files['parcel_file']
        border_file = request.files['border_file']
        excel_file = request.files['excel_file']

        # حفظ الملفات بشكل مؤقت
        parcel_path = os.path.join(tempfile.gettempdir(), 'parcel.dxf')
        border_path = os.path.join(tempfile.gettempdir(), 'border.dxf')
        excel_path = os.path.join(tempfile.gettempdir(), 'table.xlsx')

        parcel_file.save(parcel_path)
        border_file.save(border_path)
        excel_file.save(excel_path)

        # تعريف مسارات المخرجات
        parcel_shapefile = os.path.join(UPLOAD_FOLDER, 'parcel.shp')
        border_shapefile = os.path.join(UPLOAD_FOLDER, 'border.shp')

        # تحويل الملفات
        convert_dxf_to_shapefile(parcel_path, excel_path, parcel_shapefile)
        convert_dxfBorder_to_shapefile(border_path, excel_path, border_shapefile)

        # إرسال ملفات المخرجات للمستخدم
        return f'''
            <h1>Files converted successfully!</h1>
            <p><a href="/download/parcel">Download Parcel Shapefile</a></p>
            <p><a href="/download/border">Download Border Shapefile</a></p>
        '''

    except Exception as e:
        return str(e)

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        if filename == 'parcel':
            file_path = 'parcel.shp'
        elif filename == 'border':
             file_path = 'border.shp'
        else:
            abort(404)

        return send_from_directory(UPLOAD_FOLDER, file_path, as_attachment=True)
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
