from flask import Flask, render_template, request, redirect, url_for
import joblib
import pandas as pd
import mysql.connector

app = Flask(__name__)

# Load model and columns
model = joblib.load("model.pkl")
with open("columns.pkl", "rb") as f:
    model_columns = joblib.load(f)

# DB connection function
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="gaming_pc_db"
    )

# Dropdown options
motherboards = ['ASUS ROG STRIX B550-F', 'MSI MPG Z690 EDGE', 'Gigabyte B660M DS3H',
                'ASRock X570 Phantom', 'ASUS TUF Gaming B660M', 'MSI MAG B550 Tomahawk']
cpus = ['Intel i5-11400F', 'Intel i7-12700K', 'Intel i9-12900K',
        'AMD Ryzen 5 5600X', 'AMD Ryzen 7 5800X', 'AMD Ryzen 9 5950X']
gpus = ['RTX 3060', 'RTX 3070', 'RTX 3080', 'RTX 4090',
        'RX 6700 XT', 'RX 7900 XTX']
rams = [16, 32, 64]
storages = [512, 1024, 2048]
years = [2020, 2021, 2022, 2023, 2024]

@app.route("/", methods=["GET", "POST"])
def index():
    prediction = None

    if request.method == "POST":
        inputs = {
            "Year": int(request.form["year"]),
            "RAM_GB": int(request.form["ram"]),
            "Storage_GB": int(request.form["storage"]),
        }

        for mb in motherboards[1:]:
            inputs[f"Motherboard_Model_{mb}"] = 1 if request.form["motherboard"] == mb else 0
        for cpu in cpus[1:]:
            inputs[f"CPU_{cpu}"] = 1 if request.form["cpu"] == cpu else 0
        for gpu in gpus[1:]:
            inputs[f"GPU_{gpu}"] = 1 if request.form["gpu"] == gpu else 0

        df = pd.DataFrame([inputs])

        # Fill missing columns and match order
        for col in model_columns:
            if col not in df.columns:
                df[col] = 0
        df = df[model_columns]

        # Predict price
        prediction = float(model.predict(df)[0])

        # Store in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions (year, motherboard, cpu, gpu, ram, storage, predicted_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form["year"],
            request.form["motherboard"],
            request.form["cpu"],
            request.form["gpu"],
            request.form["ram"],
            request.form["storage"],
            prediction
        ))
        conn.commit()
        cursor.close()
        conn.close()

    return render_template("index.html",
                           motherboards=motherboards,
                           cpus=cpus,
                           gpus=gpus,
                           rams=rams,
                           storages=storages,
                           years=years,
                           prediction=prediction)

@app.route("/history")
def history():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM predictions ORDER BY timestamp DESC LIMIT 50")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("history.html", predictions=rows)

@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM predictions WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('history'))

if __name__ == "__main__":
    app.run(debug=True)
