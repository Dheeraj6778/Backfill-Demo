import sqlite3

DB_FILE = "weather.db"

def initial_data():


    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row

        # Total count
        total = conn.execute("SELECT COUNT(*) FROM daily_weather").fetchone()[0]
        print(f"Total rows: {total}")

        # All rows
        print(f"\n{'Date':<14} {'Max°C':>6} {'Min°C':>6} {'Rain':>6} {'Source'}")
        print("-" * 48)
        rows = conn.execute("SELECT date, temp_max_c, temp_min_c, rainfall_mm, source FROM daily_weather ORDER BY date").fetchall()
        for r in rows:
            print(f"{r[0]:<14} {r[1]:>6} {r[2]:>6} {r[3]:>6} {r[4]}")