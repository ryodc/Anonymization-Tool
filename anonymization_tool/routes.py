# anonymization_tool/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
import os
import pandas as pd
import numpy as np
import random
from datetime import datetime
from .utils import (
    pseudonymize_sha256,
    pseudonymize_md5,
    pseudonymize_random_string,
    swap_column_values,
    generalize_to_range,
    create_enhanced_swap_mapping,
    create_custom_swap_mapping,
    create_robust_swap_mapping,
    create_consistent_swap_mapping,
    apply_methods
)

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html')

@main.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = file.filename
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            file_ext = os.path.splitext(filename)[1].lower()

            if file_ext == '.xlsx':
                xls = pd.ExcelFile(file_path)
                combined_columns = {}

                for sheet_name in xls.sheet_names:
                    sheet_df = xls.parse(sheet_name)
                    for column in sheet_df.columns:
                        if column not in combined_columns:
                            combined_columns[column] = []
                        combined_columns[column].append(sheet_df[column])

                for column_name, columns in combined_columns.items():
                    reference_values = columns[0].dropna().sort_values().reset_index(drop=True)
                    for i in range(1, len(columns)):
                        current_values = columns[i].dropna().sort_values().reset_index(drop=True)
                        if not reference_values.equals(current_values):
                            flash(f'Error: "{column_name}" does not contain the same values across all sheets.')
                            return redirect(url_for('main.home'))

                return render_template('select_columns.html', columns=list(combined_columns.keys()), filename=filename)

            elif file_ext == '.csv':
                csv_df = pd.read_csv(file_path)
                combined_columns = {column: [csv_df[column]] for column in csv_df.columns}

                return render_template('select_columns.html', columns=list(combined_columns.keys()), filename=filename)
            else:
                flash('Unsupported file format. Please upload a .xlsx or .csv file.')
                return redirect(url_for('main.home'))

    return render_template('upload.html')



@main.route('/anonymize', methods=['POST'])
def anonymize():
    selected_methods = request.form.to_dict()
    filename = request.form['filename']
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file_ext = os.path.splitext(filename)[1].lower()

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    anonymized_sheets = {}
    swap_mappings = {}

    if file_ext == '.xlsx':
        xls = pd.ExcelFile(file_path)

        # First pass: Create swap mappings across all sheets for each column that needs swapping
        for sheet_name in xls.sheet_names:
            sheet_df = xls.parse(sheet_name)
            for column in sheet_df.columns:
                method = selected_methods.get(f'method_{column}')
                if method == 'swap' and column not in swap_mappings:
                    # Collect all values across all sheets for this column
                    all_values = pd.concat([xls.parse(sheet)[column].dropna() for sheet in xls.sheet_names if column in xls.parse(sheet).columns])
                    swap_mappings[column] = create_consistent_swap_mapping(all_values)

        # Second pass: Apply the swap mappings consistently across all sheets
        for sheet_name in xls.sheet_names:
            sheet_df = xls.parse(sheet_name)
            for column in sheet_df.columns:
                method = selected_methods.get(f'method_{column}')
                if method == 'swap' and column in swap_mappings:
                    sheet_df[column] = sheet_df[column].map(swap_mappings[column])

            anonymized_sheets[sheet_name] = sheet_df

        anonymized_filename = f'Anonymized_{timestamp}_{filename}'
        anonymized_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], anonymized_filename)

        with pd.ExcelWriter(anonymized_file_path) as writer:
            for sheet_name, df in anonymized_sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    elif file_ext == '.csv':
        df = pd.read_csv(file_path)

        for column in df.columns:
            method = selected_methods.get(f'method_{column}')
            if method == 'swap' and column not in swap_mappings:
                swap_mappings[column] = create_consistent_swap_mapping(df[column])

            if method == 'swap' and column in swap_mappings:
                df[column] = df[column].map(swap_mappings[column])

        anonymized_filename = f'Anonymized_{timestamp}_{filename}'
        anonymized_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], anonymized_filename)
        df.to_csv(anonymized_file_path, index=False)

    log_filename = f'log_{timestamp}_{filename}.txt'
    log_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], log_filename)
    with open(log_file_path, 'w') as log_file:
        log_file.write(f"Anonymization log for file: {filename}\n")
        log_file.write(f"Timestamp: {timestamp}\n")
        log_file.write(f"Methods applied:\n")
        for column, method in selected_methods.items():
            log_file.write(f"{column}: {method}\n")

    return render_template('download.html', filename=anonymized_filename, log_filename=log_filename)




@main.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

@main.route('/download_log/<log_filename>', methods=['GET'])
def download_log_file(log_filename):
    log_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], log_filename)
    return send_file(log_file_path, as_attachment=True)
