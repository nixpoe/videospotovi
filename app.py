from flask import Flask, render_template, jsonify, request, send_file
import psycopg2
import csv
import json
import datetime
import os

app = Flask(__name__)

conn = psycopg2.connect(
    dbname="YTspotovi",
    user="postgres",
    password="1354",
    host="localhost",
    port="5432"
)

def get_filtered_data(query='', attribute='all'):
    cur = conn.cursor()
    try:
        base_sql = """
        SELECT 
            s."Naslov", 
            s."Redatelj", 
            s."Label", 
            s."Datum", 
            s."Trajanje_sekunde", 
            s."Zanr", 
            s."Pregledi", 
            s."Komentari", 
            s."Lajkovi", 
            json_agg(i."Ime") AS "Izvodaci"
        FROM "Spotovi" AS s
        JOIN "spotizvodac" AS si ON s."Naslov" = si."naslovspota"
        JOIN "Izvodaci" AS i ON i."Ime" = si."izvodac"
        GROUP BY 
            s."Naslov", 
            s."Redatelj", 
            s."Label", 
            s."Datum", 
            s."Trajanje_sekunde", 
            s."Zanr", 
            s."Pregledi", 
            s."Komentari", 
            s."Lajkovi"
        """

        if query:
            if attribute == "all":
                sql = f"{base_sql} HAVING s.\"Naslov\" ILIKE %s OR s.\"Redatelj\" ILIKE %s OR s.\"Label\" ILIKE %s OR s.\"Zanr\" ILIKE %s OR json_agg(i.\"Ime\")::text ILIKE %s"
                cur.execute(sql, (f"%{query}%",) * 5)
            elif attribute == "Izvodac":
                sql = f"{base_sql} HAVING json_agg(i.\"Ime\")::text ILIKE %s"
                cur.execute(sql, (f"%{query}%",))
            else:
                sql = f"{base_sql} HAVING s.\"{attribute}\" ILIKE %s"
                cur.execute(sql, (f"%{query}%",))
        else:
            cur.execute(base_sql)

        columns = [desc[0] for desc in cur.description]
        data = [dict(zip(columns, row)) for row in cur.fetchall()]

        cur.close()
        return data

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        cur.close()
        return []



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/datatable')
def datatable():
    return render_template('datatable.html')

@app.route('/api/data', methods=['GET'])
def api_data():
    query = request.args.get('query', '')
    attribute = request.args.get('attribute', 'all')
    data = get_filtered_data(query, attribute)
    return jsonify(data)


def custom_json_converter(obj):
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

@app.route('/api/download/json', methods=['GET'])
def download_json():
    query = request.args.get('query', '')
    attribute = request.args.get('attribute', 'all')
    data = get_filtered_data(query, attribute)
    filename = "filtered_data.json"
    with open(filename, 'w') as f:
        json.dump(data, f, default=custom_json_converter)
    return send_file(filename, as_attachment=True)


@app.route('/api/download/csv', methods=['GET'])
def download_csv():
    query = request.args.get('query', '')
    attribute = request.args.get('attribute', 'all')
    data = get_filtered_data(query, attribute)
    filename = "filtered_data.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

