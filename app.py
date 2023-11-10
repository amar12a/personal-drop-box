# File: app.py

from flask import Flask, request, jsonify, send_file, render_template, g
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DATABASE = 'file_metadata.db'
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Set up SQLite3 database
conn = sqlite3.connect('file_metadata.db')
c = conn.cursor()

# Create table for file metadata
c.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY,
        filename TEXT,
        created_at TEXT,
        size INTEGER,
        file_type TEXT
    )
''')

@app.route('/')
def index():
    return render_template('index.html')

# Endpoint to upload a file
@app.route('/files/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    filename = file.filename
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    file_path = os.getcwd() + "/uploads/" + filename
    file.save(os.path.join(file_path))

    file_size = os.path.getsize(file_path)
    file_type = file_path.split(".")[-1]
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO files (filename, created_at, size, file_type)
        VALUES (?, ?, ?, ?)
    ''', (filename, created_at, file_size, file_type))
    conn.commit()
    conn.close()
    return jsonify({"message": "File uploaded successfully"})

# Endpoint to retrieve a file
@app.route('/files/<int:file_id>', methods=['GET'])
def retrieve_file(file_id):
    c = get_db().cursor()
    file_data = c.execute('SELECT filename FROM files WHERE id = ?', (file_id,)).fetchone()
    if file_data:
        filename = file_data[0]
        response = send_file('uploads/' + filename, as_attachment=True)
        response.headers["Custom-Message"] = "File downloaded successfully."
        return response
    else:
        return jsonify({"message": "File not found"})

# Endpoint to get file metadata
@app.route('/files', methods=['GET'])
def get_files():
    c = get_db().cursor()
    data = c.execute('SELECT * FROM files').fetchall()
    files = [{'id': row[0], 'filename': row[1], 'created_at': row[2], "type": row[3]} for row in data]
    return jsonify({"files": files})

# Endpoint to delete a file
@app.route('/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    conn = get_db()
    c = conn.cursor()
    file_data = c.execute('SELECT filename FROM files WHERE id = ?', (file_id,)).fetchone()
    if file_data:
        try:
            filename = file_data[0]
            file_path = file_path = os.getcwd() + "/uploads/" + filename
            os.remove(file_path)
            c.execute('DELETE FROM files WHERE id = ?', (file_id,))
            conn.commit()
            return jsonify({"message": "File deleted"})
        except Exception as e:
            return jsonify({"message": "File not found or check error", "Error": str(e)})
    else:
        return jsonify({"message": "File not found"})

@app.route('/files/<int:file_id>', methods=['PUT'])
def update_file(file_id):
    try:
        conn = get_db()
        c = conn.cursor()
        file_data = c.execute('SELECT filename FROM files WHERE id = ?', (file_id,)).fetchone()
        if file_data:
            new_metadata = request.json.get('metadata')
            if new_metadata:
                # Create a list of column-value pairs for the SET clause
                set_clause = ', '.join([f"{field} = ?" for field in new_metadata.keys()])
                # Update metadata in the database using parameterized query
                query = f"UPDATE files SET {set_clause} WHERE id = ?"
                # Execute the query with the parameterized values
                values = list(new_metadata.values()) + [file_id]
                c.execute(query, values)
                conn.commit()  # Commit the changes after updating metadata

            return jsonify({"message": "File updated successfully"}), 200
        else:
            return jsonify({"error": "File not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
