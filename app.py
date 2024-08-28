from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import os
import pandas as pd
import hashlib
import numpy as np
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'  # Needed for flash messages

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def pseudonymize_sha256(value):
    return hashlib.sha256(str(value).encode()).hexdigest()

def pseudonymize_md5(value):
    return hashlib.md5(str(value).encode()).hexdigest()

def pseudonymize_random_string(value, length=8):
    return ''.join(np.random.choice(list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'), length))

def swap_column_values(df, column):
    original_values = df[column].values
    np.random.shuffle(original_values)
    df[column] = original_values
    return df

def generalize_to_range(value, range_size=10):
    try:
        numeric_value = float(value)
        lower_bound = (numeric_value // range_size) * range_size
        upper_bound = lower_bound + range_size - 1
        return f"{int(lower_bound)}-{int(upper_bound)}"
    except ValueError:
        return value  # If not numeric, return the original value


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
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
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            file_ext = os.path.splitext(filename)[1].lower()

            if file_ext == '.xlsx':
                # Read the Excel file and combine all sheets
                xls = pd.ExcelFile(file_path)
                combined_columns = {}

                for sheet_name in xls.sheet_names:
                    sheet_df = xls.parse(sheet_name)
                    for column in sheet_df.columns:
                        if column not in combined_columns:
                            combined_columns[column] = []
                        combined_columns[column].append(sheet_df[column])

                # Check if columns with the same name have the same values
                for column_name, columns in combined_columns.items():
                    reference_values = columns[0].dropna().sort_values().reset_index(drop=True)
                    for i in range(1, len(columns)):
                        current_values = columns[i].dropna().sort_values().reset_index(drop=True)
                        if not reference_values.equals(current_values):
                            flash(f'Error: "{column_name}" does not contain the same values across all sheets.')
                            return redirect(url_for('home'))

                return render_template('select_columns.html', columns=list(combined_columns.keys()), filename=filename)

            elif file_ext == '.csv':
                # Read the CSV file
                csv_df = pd.read_csv(file_path)
                combined_columns = {column: [csv_df[column]] for column in csv_df.columns}

                return render_template('select_columns.html', columns=list(combined_columns.keys()), filename=filename)
            else:
                flash('Unsupported file format. Please upload a .xlsx or .csv file.')
                return redirect(url_for('home'))

    return render_template('upload.html')

@app.route('/anonymize', methods=['POST'])
def anonymize():
    selected_methods = request.form.to_dict()
    filename = request.form['filename']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file_ext = os.path.splitext(filename)[1].lower()

    # Generate timestamp once for use throughout the function
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    anonymized_sheets = {}
    random_string_mappings = {}
    swap_mappings = {}

    if file_ext == '.xlsx':
        xls = pd.ExcelFile(file_path)

        # First, determine the swap mapping for each column that needs swapping
        for sheet_name in xls.sheet_names:
            sheet_df = xls.parse(sheet_name)
            for column in sheet_df.columns:
                method = selected_methods.get(f'method_{column}')
                if method == 'swap' and column not in swap_mappings:
                    # Get the values from the first sheet where this column appears
                    original_values = sheet_df[column].copy()
                    shuffled_values = original_values.sample(frac=1).reset_index(drop=True)
                    swap_mappings[column] = dict(zip(original_values, shuffled_values))

        # Now apply the transformations, including the consistent swapping
        for sheet_name in xls.sheet_names:
            sheet_df = xls.parse(sheet_name)
            for column in sheet_df.columns:
                method = selected_methods.get(f'method_{column}')
                if method == 'sha256':
                    sheet_df[column] = sheet_df[column].apply(pseudonymize_sha256)
                elif method == 'md5':
                    sheet_df[column] = sheet_df[column].apply(pseudonymize_md5)
                elif method == 'random_string':
                    if column not in random_string_mappings:
                        unique_values = sheet_df[column].unique()
                        random_string_mappings[column] = {val: pseudonymize_random_string(str(val)) for val in unique_values}
                    sheet_df[column] = sheet_df[column].map(random_string_mappings[column])
                elif method == 'swap' and column in swap_mappings:
                    # Apply the precomputed swap mapping consistently across all sheets
                    sheet_df[column] = sheet_df[column].map(swap_mappings[column])
                elif method == 'generalize':
                    range_size = int(request.form.get(f'range_size_{column}', 10))  # Default to ranges of size 10
                    sheet_df[column] = sheet_df[column].apply(generalize_to_range, args=(range_size,))
            anonymized_sheets[sheet_name] = sheet_df

        anonymized_filename = f'Anonymized_{timestamp}_{filename}'
        anonymized_file_path = os.path.join(app.config['UPLOAD_FOLDER'], anonymized_filename)

        with pd.ExcelWriter(anonymized_file_path) as writer:
            for sheet_name, df in anonymized_sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    elif file_ext == '.csv':
        df = pd.read_csv(file_path)

        for column in df.columns:
            method = selected_methods.get(f'method_{column}')
            if method == 'sha256':
                df[column] = df[column].apply(pseudonymize_sha256)
            elif method == 'md5':
                df[column] = df[column].apply(pseudonymize_md5)
            elif method == 'random_string':
                if column not in random_string_mappings:
                    unique_values = df[column].unique()
                    random_string_mappings[column] = {val: pseudonymize_random_string(str(val)) for val in unique_values}
                df[column] = df[column].map(random_string_mappings[column])
            elif method == 'swap':
                # Since CSVs are single-sheet, apply the swap directly to the column
                df[column] = df[column].map(swap_mappings.get(column, {}))
            elif method == 'generalize':
                range_size = int(request.form.get(f'range_size_{column}', 10))
                df[column] = df[column].apply(generalize_to_range, args=(range_size,))

        anonymized_filename = f'Anonymized_{timestamp}_{filename}'
        anonymized_file_path = os.path.join(app.config['UPLOAD_FOLDER'], anonymized_filename)
        df.to_csv(anonymized_file_path, index=False)

    # Generate filenames for anonymized file and log file
    log_filename = f'log_{timestamp}_{filename}.txt'

    # Create a log file
    log_file_path = os.path.join(app.config['UPLOAD_FOLDER'], log_filename)
    with open(log_file_path, 'w') as log_file:
        log_file.write(f"Anonymization log for file: {filename}\n")
        log_file.write(f"Timestamp: {timestamp}\n")
        log_file.write(f"Methods applied:\n")
        for column, method in selected_methods.items():
            log_file.write(f"{column}: {method}\n")

    return render_template('download.html', filename=anonymized_filename, log_filename=log_filename)



@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

@app.route('/download_log/<log_filename>', methods=['GET'])
def download_log_file(log_filename):
    log_file_path = os.path.join(app.config['UPLOAD_FOLDER'], log_filename)
    return send_file(log_file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
