import os
from flask import Flask, request, jsonify
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Получение URL базы данных из переменной окружения Railway
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Возвращает соединение с PostgreSQL"""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    """Создаёт таблицу notes, если она ещё не существует"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

# CRUD операции
@app.route('/api/notes', methods=['GET'])
def get_notes():
    """Получение всех заметок с пагинацией"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT * FROM notes ORDER BY created_at DESC LIMIT %s OFFSET %s',
        (per_page, offset)
    )
    notes = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({
        'page': page,
        'per_page': per_page,
        'total': len(notes),
        'notes': notes
    })

@app.route('/api/notes', methods=['POST'])
def create_note():
    """Создание заметки"""
    data = request.get_json()
    now = datetime.now().isoformat()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''INSERT INTO notes (title, content, created_at, updated_at)
           VALUES (%s, %s, %s, %s) RETURNING id''',
        (data['title'], data.get('content', ''), now, now)
    )
    note_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'id': note_id, 'message': 'Note created'}), 201

@app.route('/api/notes/<int:note_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_note(note_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'GET':
        cur.execute('SELECT * FROM notes WHERE id = %s', (note_id,))
        note = cur.fetchone()
        cur.close()
        conn.close()
        if note:
            return jsonify(note)
        return jsonify({'error': 'Note not found'}), 404

    elif request.method == 'PUT':
        data = request.get_json()
        now = datetime.now().isoformat()
        cur.execute(
            '''UPDATE notes
               SET title = %s, content = %s, updated_at = %s
               WHERE id = %s''',
            (data['title'], data.get('content', ''), now, note_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Note updated'})

    elif request.method == 'DELETE':
        cur.execute('DELETE FROM notes WHERE id = %s', (note_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Note deleted'})

# Настройка CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE')
    return response

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)