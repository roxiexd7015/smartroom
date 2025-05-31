from flask import Flask, request, render_template, jsonify
import MySQLdb

app = Flask(__name__)

# ✅ Ruta care primește datele de la ESP32 și le salvează în MySQL
@app.route('/data', methods=['POST'])
def receive_data():
    try:
        conn = MySQLdb.connect(
            host="localhost",
            user="root",
            passwd="student",
            db="smartroom"
        )
        cursor = conn.cursor()

        # Extragere date trimise de ESP32
        # Transformă în float toate valorile
        temp = float(request.form.get('temperature'))
        hum = float(request.form.get('humidity'))
        light = float(request.form.get('light'))
        dust = float(request.form.get('dust'))
        dust_avg = float(request.form.get('dust_avg'))
        gas_resistance = float(request.form.get('gas_resistance'))
        gas_res_avg = float(request.form.get('gas_res_avg'))

        # 🧮 Calculează scoruri parțiale
        score_temp = 10 if 20 <= temp <= 24 else (2 if temp < 18 or temp > 26 else 6)
        score_hum = 10 if 40 <= hum <= 60 else (2 if hum < 30 or hum > 70 else 6)
        score_light = 10 if 100 <= light <= 500 else (3 if light < 50 or light > 800 else 6)
        score_dust = 10 if dust < 50 else (2 if dust > 150 else 6)
        score_gas = 10 if gas_resistance >= 30 else (2 if gas_resistance < 10 else 6)

        # 🧠 Scor total rotunjit la 1 zecimală
        comfort_score = round((score_temp + score_hum + score_light + score_dust + score_gas) / 5, 1)


        # Inserare date în tabelă (fără ID și timestamp - se generează automat)
        query = """
            INSERT INTO sensor_data (
                temperature, humidity, light, dust, gas_resistance,
                dust_avg, gas_res_avg, comfort_score
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            temp, hum, light, dust, gas_resistance,
            dust_avg, gas_res_avg, comfort_score
        )

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Data saved successfully", 200

    except Exception as e:
        print("🔥 Eroare în /data:", e)
        return f"❌ Server error: {e}", 500

# ✅ Ruta care returnează pagina cu carduri interactive
@app.route('/')
@app.route('/dashboard')
def dashboard():
    try:
        conn = MySQLdb.connect(
            host="localhost",
            user="root",
            passwd="student",
            db="smartroom"
        )
        cursor = conn.cursor()

        cursor.execute("SELECT temperature, humidity, light, dust, gas_resistance, comfort_score FROM sensor_data ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()

        if row:
            data = {
                'temperature': row[0],
                'humidity': row[1],
                'light': row[2],
                'dust': row[3],
                'gas': row[4],
                'comfort_score': row[5]
            }
        else:
            data = {
                'temperature': 0,
                'humidity': 0,
                'light': 0,
                'dust': 0,
                'gas': 0,
                'comfort_score': 0
            }

        cursor.close()
        conn.close()

        return render_template("dashboard.html", data=data)

    except Exception as e:
        print("🔥 Eroare în dashboard:", e)
        return "Eroare la afișarea dashboardului", 500

#ruta detalii senzor
@app.route('/details/<sensor>')
def sensor_details(sensor):
    
    return render_template("details.html", sensor=sensor)

# ✅ Ruta care returnează ultimele valori (folosită de JavaScript din dashboard.html)
@app.route('/api/latest')
def get_latest():
    try:
        conn = MySQLdb.connect(
            host="localhost",
            user="root",
            passwd="student",
            db="smartroom"
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT temperature, humidity, light, dust, dust_avg,
                   gas_resistance, gas_res_avg, comfort_score, timestamp 
            FROM sensor_data 
            ORDER BY timestamp DESC LIMIT 10
        """)
        rows = cursor.fetchall()
        conn.close()

        data = []
        for row in rows:
            data.append({
                'temperature': row[0],
                'humidity': row[1],
                'light': row[2],
                'dust': row[3],
                'dust_avg': row[4],
                'gas': row[5],
                'gas_avg': row[6],
                'comfort_score': row[7],
                'timestamp': row[8].strftime("%Y-%m-%d %H:%M:%S")
            })
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)})
    
@app.route('/api/details/<sensor>')
def api_sensor_data(sensor):
    try:
        conn = MySQLdb.connect(
            host="localhost",
            user="root",
            passwd="student",
            db="smartroom"
        )
        cursor = conn.cursor()

        # Dicționar cu numele coloanelor din baza de date
        sensor_map = {
            'dust': ('dust', 'dust_avg'),
            'gas': ('gas_resistance', 'gas_res_avg'),
            'temperature': ('temperature', None),
            'humidity': ('humidity', None)
        }

        if sensor not in sensor_map:
            return jsonify({'error': 'Senzor invalid'})

        col1, col2 = sensor_map[sensor]

        # Query diferit dacă există și coloană de medie
        if col2:
            query = f"""
                SELECT {col1}, {col2}, timestamp
                FROM sensor_data
                ORDER BY timestamp DESC LIMIT 50
            """
        else:
            query = f"""
                SELECT {col1}, timestamp
                FROM sensor_data
                ORDER BY timestamp DESC LIMIT 50
            """

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        data = []
        for row in rows[::-1]:
            entry = {}

            if col2:
                entry['brut'] = row[0]
                entry['medie'] = row[1]
                entry['timestamp'] = row[2].strftime("%H:%M")
            else:
                entry['valoare'] = row[0]
                entry['timestamp'] = row[1].strftime("%H:%M")
            data.append(entry)

        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)})

# ✅ Pornirea serverului Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
