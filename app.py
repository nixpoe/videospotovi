from flask import Flask, render_template, jsonify, request, make_response
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime

app = Flask(__name__)

DB_CONFIG = {
    "dbname": "YTspotovi",
    "user": "postgres",
    "password": "1354",
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def create_response(data, message="Uspješno", status=200):
    return make_response(jsonify({
        "status": "OK" if status < 400 else "Error",
        "message": message,
        "response": data
    }), status)

@app.errorhandler(404)
def not_found(e):
    return create_response(None, "Resurs nije pronađen", 404)

@app.errorhandler(500)
def server_error(e):
    return create_response(None, f"Serverska pogreška: {str(e)}", 500)


# a. GET - Dohvati sve spotove
@app.route('/api/spotovi', methods=['GET'])
def get_all_spotovi():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute('SELECT * FROM "Spotovi"')
        data = cur.fetchall()
        return create_response(data)
    except Exception as e:
        return create_response(None, str(e), 500)
    finally:
        cur.close()
        conn.close()

# b. GET - Dohvati pojedinačni spot po ID-u
@app.route('/api/spotovi/<int:id>', methods=['GET'])
def get_spot_by_id(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute('SELECT * FROM "Spotovi" WHERE id = %s', (id,))
        spot = cur.fetchone()
        if spot:
            return create_response(spot)
        return create_response(None, "Spot s tim ID-em ne postoji", 404)
    finally:
        cur.close()
        conn.close()

# d. POST - Unos novog spota
@app.route('/api/spotovi', methods=['POST'])
def create_spot():
    data = request.json
    if not data:
        return create_response(None, "Nedostaju podaci", 400)
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        sql = """
            INSERT INTO "Spotovi" ("Naslov", "Redatelj", "Label", "Datum", "Trajanje_sekunde", "Zanr", "Pregledi", "Komentari", "Lajkovi")
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """
        cur.execute(sql, (
            data.get('Naslov'), data.get('Redatelj'), data.get('Label'),
            data.get('Datum'), data.get('Trajanje_sekunde'), data.get('Zanr'),
            data.get('Pregledi', 0), data.get('Komentari', 0), data.get('Lajkovi', 0)
        ))
        new_id = cur.fetchone()[0]
        conn.commit()
        return create_response({"id": new_id}, "Spot uspješno kreiran", 201)
    except Exception as e:
        conn.rollback()
        return create_response(None, str(e), 500)
    finally:
        cur.close()
        conn.close()

# e. PUT - Ažuriranje spota
@app.route('/api/spotovi/<int:id>', methods=['PUT'])
def update_spot(id):
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('UPDATE "Spotovi" SET "Naslov"=%s, "Zanr"=%s, "Pregledi"=%s WHERE id=%s RETURNING id',
                    (data.get('Naslov'), data.get('Zanr'), data.get('Pregledi'), id))
        if cur.fetchone():
            conn.commit()
            return create_response({"id": id}, "Spot uspješno ažuriran")
        return create_response(None, "Spot nije pronađen", 404)
    finally:
        cur.close()
        conn.close()

# f. DELETE - Brisanje spota
@app.route('/api/spotovi/<int:id>', methods=['DELETE'])
def delete_spot(id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM "Spotovi" WHERE id = %s RETURNING id', (id,))
        if cur.fetchone():
            conn.commit()
            return create_response({"id": id}, "Spot obrisan")
        return create_response(None, "Spot nije pronađen", 404)
    finally:
        cur.close()
        conn.close()

# c. DODATNE GET TOČKE (3 komada)

# 1. Pretraga po žanru
@app.route('/api/spotovi/zanr/<string:zanr_name>', methods=['GET'])
def get_by_zanr(zanr_name):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM "Spotovi" WHERE "Zanr" ILIKE %s', (f'%{zanr_name}%',))
    return create_response(cur.fetchall())

# 2. Top 5 najgledanijih
@app.route('/api/spotovi/top', methods=['GET'])
def get_top_spots():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT "Naslov", "Pregledi" FROM "Spotovi" ORDER BY "Pregledi" DESC LIMIT 5')
    return create_response(cur.fetchall())

# 3. Osnovna statistika
@app.route('/api/spotovi/statistika', methods=['GET'])
def get_stats():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT COUNT(*) as ukupno_spotova, AVG("Trajanje_sekunde") as prosjecno_trajanje FROM "Spotovi"')
    res = cur.fetchone()
    if res['prosjecno_trajanje']: res['prosjecno_trajanje'] = round(float(res['prosjecno_trajanje']), 2)
    return create_response(res)

if __name__ == '__main__':
    app.run(debug=True)