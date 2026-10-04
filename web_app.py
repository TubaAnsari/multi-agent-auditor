from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import os
import sys
import json
import subprocess
from werkzeug.utils import secure_filename
import shutil
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'py', 'js', 'java', 'cpp', 'c', 'h', 'html', 'css', 'rb', 'go', 'rs', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def run_analysis(filepath):
    """Run the multi-agent system on the uploaded file"""
    try:
        # Import the main function dynamically
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        # Run the analysis
        main_module.run_multi_agent_system(filepath)
        return True, "Analysis completed successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"

@app.route('/')
def index():
    return render_template('index_new.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Run analysis
        success, message = run_analysis(filepath)
        
        if success:
            # Check if output files exist
            outputs = []
            for out_file in ['review_report.md', 'test_suite.py', 'README.md']:
                if os.path.exists(out_file):
                    outputs.append(out_file)
            
            return jsonify({
                'success': True,
                'message': message,
                'filename': filename,
                'outputs': outputs
            })
        else:
            return jsonify({'success': False, 'error': message}), 500
    
    else:
        return jsonify({'success': False, 'error': 'Invalid file type'}), 400

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Security: only allow specific output files
        allowed_outputs = ['review_report.md', 'test_suite.py', 'README.md']
        if filename in allowed_outputs and os.path.exists(filename):
            return send_file(filename, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)