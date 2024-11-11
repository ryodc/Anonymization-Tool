# anonymization_tool/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
import time
import os
import pandas as pd
import numpy as np
import random
from datetime import datetime
from .anonymization.anonymizationEngine import create_consistent_swap_mapping
import zipfile
from .observer.logging_observer import LoggingObserver
from .anonymization.anonymization_factory import AnonymizationFactory
from werkzeug.utils import secure_filename

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html')


@main.route('/upload', methods=['GET', 'POST'])
def upload_file():
    log_observer = LoggingObserver(current_app.config['LOG_FOLDER'])
    
    if request.method == 'POST':
        if 'files' not in request.files:
            flash('No file part', 'danger') 
            log_observer.update('upload_error', 'No file part')
            return redirect(request.url)

        files = request.files.getlist('files')
        if not files or any(f.filename == '' for f in files):
            flash('No selected files', 'danger')  # Error message
            log_observer.update('upload_error', 'No selected files')
            return redirect(request.url)

        combined_columns = {}
        allowed_extensions = {'.xlsx', '.csv'}
        max_file_size = 10 * 1024 * 1024  # 10 MB

        for file in files:
            filename = secure_filename(file.filename)
            file_ext = os.path.splitext(filename)[1].lower()
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)


            if file_ext not in allowed_extensions:
                flash(f'Unsupported file format for {filename}. Please upload only .xlsx or .csv files.', 'danger') 
                log_observer.update('upload_error', f'Unsupported file format for {filename}')
                return redirect(url_for('main.home'))

            # Check file size
            file.seek(0, os.SEEK_END)
            file_length = file.tell()
            file.seek(0, 0)
            if file_length > max_file_size:
                flash(f'File {filename} exceeds the maximum allowed size of 10 MB.', 'danger')
                log_observer.update('upload_error', f'File {filename} exceeds the maximum allowed size')
                return redirect(url_for('main.home'))

            file.save(file_path)

            if file_ext == '.xlsx':
                xls = pd.ExcelFile(file_path)
                for sheet_name in xls.sheet_names:
                    sheet_df = xls.parse(sheet_name)
                    for column in sheet_df.columns:
                        if column not in combined_columns:
                            combined_columns[column] = []
                        combined_columns[column].append(sheet_df[column])

            elif file_ext == '.csv':
                csv_df = pd.read_csv(file_path)
                for column in csv_df.columns:
                    if column not in combined_columns:
                        combined_columns[column] = []
                    combined_columns[column].append(csv_df[column])

        for column_name, columns in combined_columns.items():
            reference_values = columns[0].dropna().sort_values().reset_index(drop=True)
            for i in range(1, len(columns)):
                current_values = columns[i].dropna().sort_values().reset_index(drop=True)
                if not reference_values.equals(current_values):
                    flash(f'Error: "{column_name}" does not contain the same values across all files.', 'danger')  # Error message
                    log_observer.update('upload_error', f'Column inconsistency for {column_name}')
                    return redirect(url_for('main.home'))

        log_observer.update('upload_success', f'Files uploaded successfully: {[f.filename for f in files]}')
        return render_template('select_columns.html', columns=list(combined_columns.keys()), filenames=[f.filename for f in files])

    return render_template('upload.html')

@main.route('/anonymize', methods=['POST'])
def anonymize():
    log_observer = LoggingObserver(current_app.config['LOG_FOLDER'])
    
    try:
        selected_methods = request.form.to_dict()
        filenames = request.form.getlist('filenames')
        anonymized_files = []  
        swap_mappings = {}

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        for filename in filenames:
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file_ext = os.path.splitext(filename)[1].lower()

            if file_ext == '.xlsx':
                xls = pd.ExcelFile(upload_path)

                for sheet_name in xls.sheet_names:
                    sheet_df = xls.parse(sheet_name)
                    for column in sheet_df.columns:
                        method = selected_methods.get(f'method_{column}')
                        if method == 'swap' and column not in swap_mappings:
                            all_values = pd.concat([xls.parse(sheet)[column].dropna() for sheet in xls.sheet_names if column in xls.parse(sheet).columns])
                            swap_mappings[column] = create_consistent_swap_mapping(all_values)

                anonymized_sheets = {}
                for sheet_name in xls.sheet_names:
                    sheet_df = xls.parse(sheet_name)
                    for column in sheet_df.columns:
                        method = selected_methods.get(f'method_{column}')
                        anonymization_method = AnonymizationFactory.get_anonymization_method(method, swap_mapping=swap_mappings.get(column), range_size=int(request.form.get(f'range_size_{column}', 10)))
                        sheet_df[column] = sheet_df[column].apply(anonymization_method)

                    anonymized_sheets[sheet_name] = sheet_df

                anonymized_filename = f'Anonymized_{timestamp}_{filename}'
                anonymized_path = os.path.join(current_app.config['ANONYMIZED_FOLDER'], anonymized_filename)

                with pd.ExcelWriter(anonymized_path) as writer:
                    for sheet_name, df in anonymized_sheets.items():
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

                anonymized_files.append(anonymized_filename)

            elif file_ext == '.csv':
                df = pd.read_csv(upload_path)

                for column in df.columns:
                    method = selected_methods.get(f'method_{column}')
                    if method == 'swap' and column not in swap_mappings:
                        all_values = df[column].dropna()
                        swap_mappings[column] = create_consistent_swap_mapping(all_values)

                for column in df.columns:
                    method = selected_methods.get(f'method_{column}')
                    anonymization_method = AnonymizationFactory.get_anonymization_method(method, swap_mapping=swap_mappings.get(column), range_size=int(request.form.get(f'range_size_{column}', 10)))
                    df[column] = df[column].apply(anonymization_method)

                anonymized_filename = f'Anonymized_{timestamp}_{filename}'
                anonymized_path = os.path.join(current_app.config['ANONYMIZED_FOLDER'], anonymized_filename)
                df.to_csv(anonymized_path, index=False)

                anonymized_files.append(anonymized_filename)

            os.remove(upload_path)

        zip_filename = f'anonymized_{timestamp}.zip'
        zip_path = os.path.join(current_app.config['ANONYMIZED_FOLDER'], zip_filename)

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for anonymized_file in anonymized_files:
                file_path = os.path.join(current_app.config['ANONYMIZED_FOLDER'], anonymized_file)
                zipf.write(file_path, anonymized_file)

        log_filename = f'log_{timestamp}.txt'
        log_path = os.path.join(current_app.config['LOG_FOLDER'], log_filename)

        with open(log_path, 'w') as log_file:
            log_file.write(f"Anonymization Log for files: {', '.join(filenames)}\n")
            log_file.write(f"Timestamp: {timestamp}\n\n")
            log_file.write(f"Columns and Applied Methods:\n")
            log_file.write(f"{'-'*40}\n")

            for column, method in selected_methods.items():
                display_method = None
                if method == 'sha256':
                    display_method = 'Pseudonymization'
                elif method == 'swap':
                    display_method = 'Swapping'
                elif method == 'generalize':
                    range_size = request.form.get(f'range_size_{column}', 10)
                    display_method = f'Generalization (Range: {range_size})'
                elif method == 'none':
                    display_method = 'None'

                log_file.write(f"{column:<15}: {display_method}\n")

        log_observer.update('anonymize_success', f'Files anonymized successfully: {anonymized_files}')
        flash('Anonymization log created successfully.', 'success')

        return render_template('download.html', filename=zip_filename, log_filename=log_filename)

    except Exception as e:
        log_observer.update('anonymize_error', str(e))
        flash(f'An error occurred during the anonymization process: {str(e)}', 'danger')
        return redirect(url_for('main.upload_file'))

@main.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(current_app.config['ANONYMIZED_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

@main.route('/download_log/<log_filename>', methods=['GET'])
def download_log_file(log_filename):
    log_file_path = os.path.join(current_app.config['LOG_FOLDER'], log_filename)
    return send_file(log_file_path, as_attachment=True)