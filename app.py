from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import os
import pandas as pd
import hashlib
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'  # Needed for flash messages

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def pseudonymize_sha256(value):
    return hashlib.sha256(value.encode()).hexdigest()

def pseudonymize_md5(value):
    return hashlib.md5(value.encode()).hexdigest()

def pseudonymize_random_string(value, length=8):
    return ''.join(np.random.choice(list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'), length))

def swap_column_values(df, column):
    original_values = df[column].values
    np.random.shuffle(original_values)
    df[column] = original_values
    return df

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.csv')):
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            sheets_info = {}

            if file.filename.endswith('.xlsx'):
                xls = pd.ExcelFile(file_path)
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    sheets_info[sheet_name] = df.columns.tolist()
            elif file.filename.endswith('.csv'):
                df = pd.read_csv(file_path)
                sheets_info['Sheet1'] = df.columns.tolist()

            return render_template('select_columns.html', sheets_info=sheets_info, filename=filename)
        else:
            flash('Please upload a valid CSV or Excel file.', 'danger')
            return redirect(url_for('upload_file'))

    return render_template('upload.html')

from datetime import datetime

@app.route('/pseudonymize', methods=['POST'])
def pseudonymize_file():
    filename = request.form['filename']
    file_ext = filename.split('.')[-1].lower()
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if file_ext == 'xlsx':
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        sheets_dict = {sheet: xls.parse(sheet) for sheet in sheet_names}
    elif file_ext == 'csv':
        sheets_dict = {'Sheet1': pd.read_csv(file_path)}

    original_vs_pseudonymized = []

    for sheet_name, df in sheets_dict.items():
        for column in df.columns:
            method = request.form.get(f'method_{sheet_name}_{column}')
            if method == 'swap':
                df = swap_column_values(df, column)
            elif method == 'sha256':
                original_vs_pseudonymized.append({
                    'sheet': sheet_name,
                    'column': column,
                    'original': df[column].tolist(),
                    'pseudonymized': df[column].apply(lambda x: pseudonymize_sha256(str(x))).tolist()
                })
                df[column] = df[column].apply(lambda x: pseudonymize_sha256(str(x)))
            elif method == 'md5':
                original_vs_pseudonymized.append({
                    'sheet': sheet_name,
                    'column': column,
                    'original': df[column].tolist(),
                    'pseudonymized': df[column].apply(lambda x: pseudonymize_md5(str(x))).tolist()
                })
                df[column] = df[column].apply(lambda x: pseudonymize_md5(str(x)))
            elif method == 'random_string':
                original_vs_pseudonymized.append({
                    'sheet': sheet_name,
                    'column': column,
                    'original': df[column].tolist(),
                    'pseudonymized': df[column].apply(lambda x: pseudonymize_random_string(str(x))).tolist()
                })
                df[column] = df[column].apply(lambda x: pseudonymize_random_string(str(x)))

    # Generate a unique filename using the current timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    anonymized_filename = f'Anonymized_{timestamp}_{filename}'
    output_file_path = os.path.join(app.config['UPLOAD_FOLDER'], anonymized_filename)

    if file_ext == 'xlsx':
        with pd.ExcelWriter(output_file_path) as writer:
            for sheet_name, df in sheets_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    elif file_ext == 'csv':
        sheets_dict['Sheet1'].to_csv(output_file_path, index=False)

    if not os.path.exists(output_file_path):
        flash('An error occurred while trying to save the pseudonymized file.', 'danger')
        return redirect(url_for('upload_file'))

    # Generate a unique log filename using the current timestamp
    log_filename = f'log_{timestamp}_{filename}.txt'
    log_file_path = os.path.join(app.config['UPLOAD_FOLDER'], log_filename)
    with open(log_file_path, 'w') as log_file:
        for item in original_vs_pseudonymized:
            log_file.write(f"Sheet: {item['sheet']}, Column: {item['column']}\n")
            log_file.write("Original -> Pseudonymized\n")
            for original, pseudonymized in zip(item['original'], item['pseudonymized']):
                log_file.write(f"{original} -> {pseudonymized}\n")
            log_file.write("\n")

    return render_template('download.html', filename=anonymized_filename, log_filename=log_filename)


@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('File not found.', 'danger')
        return redirect(url_for('home'))

@app.route('/download_log/<log_filename>')
def download_log(log_filename):
    log_path = os.path.join(app.config['UPLOAD_FOLDER'], log_filename)
    if os.path.exists(log_path):
        return send_file(log_path, as_attachment=True)
    else:
        flash('Log file not found.', 'danger')
        return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
