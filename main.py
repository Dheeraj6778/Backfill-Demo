import sqlite3
import requests
from datetime import date, timedelta
import os

if os.path.exists("weather.db"):
    os.remove("weather.db")  # Start fresh for demo purposes

DB_FILE = "weather.db"
CITY = "New York"
LATITUDE = 40.7128
LONGITUDE = -74.0060

END_DATE = date.today() - timedelta(days=1)
START_DATE = END_DATE - timedelta(days=29)

SIMULATED_GAPS = [
    START_DATE + timedelta(days=5),
    START_DATE + timedelta(days=6),
    START_DATE + timedelta(days=7),
    START_DATE + timedelta(days=15),
    START_DATE + timedelta(days=22),
    START_DATE + timedelta(days=23),
]


def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_weather (
            city        TEXT NOT NULL,
            date        TEXT NOT NULL,
            temp_max_c  REAL,
            temp_min_c  REAL,
            rainfall_mm REAL,
            source      TEXT DEFAULT 'pipeline',
            PRIMARY KEY (city, date)
        )
    """)
    conn.commit()
    print("DB initialized.")


def seed_existing_data(conn: sqlite3.Connection, all_dates: list[date]):
    seeded = 0
    for dt in all_dates:
        if dt in SIMULATED_GAPS:
            continue  # Skip inserting data for simulated gaps
        conn.execute("""
            INSERT OR IGNORE INTO daily_weather (city, date, temp_max_c, temp_min_c, rainfall_mm)
            VALUES (?, ?, ?, ?, ?)
        """, (CITY, dt.isoformat(), 25.0, 15.0, 5.0))
        seeded += 1
    conn.commit()
    print(f"Seeded {seeded} existing records (excluding simulated gaps).")


def find_gaps(conn: sqlite3.Connection, all_dates: list[date]) -> list[date]:
    cursor = conn.execute("""
        SELECT date FROM daily_weather
        WHERE city = ?
    """, (CITY,))
    existing_dates = {date.fromisoformat(row[0]) for row in cursor.fetchall()}
    gaps = [dt for dt in all_dates if dt not in existing_dates]
    print(f"Identified {len(gaps)} gaps.")
    for g in gaps:
        print(f"   ❌ {g.isoformat()}")
    return gaps


def fetch_weather_data(dt: date) -> dict:
    # Simulate API response with dummy data
    print(f"Fetching weather data for {dt.isoformat()}...")
    return {
        "temp_max_c": 25.0,
        "temp_min_c": 15.0,
        "rainfall_mm": 5.0
    }


def fetch_weather(gap_dates: list[date]) -> dict:

    start = min(gap_dates).isoformat()
    end = max(gap_dates).isoformat()
    print(f"Fetching weather data for gaps from {start} to {end}...")
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start,
        "end_date": end,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "timezone": "America/New_York"
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()["daily"]
    print("API response received.")
    result = {}
    for i, dt in enumerate(data["time"]):
        result[dt] = {
            "temp_max_c": data["temperature_2m_max"][i],
            "temp_min_c": data["temperature_2m_min"][i],
            "rainfall_mm": data["precipitation_sum"][i]
        }
    print(f"Fetched weather data for {len(result)} days.")
    return result


def backfill_data(conn: sqlite3.Connection, gaps: list[date], api_data: dict):
    filled = 0 
    skipped = 0
    for dt in gaps:
        key = dt.isoformat()
        if key not in api_data:
            print(f"   ⚠️ No API data for {key}. Skipping.")
            skipped += 1
            continue
        row = api_data[key]
        try:
            conn.execute("""
                INSERT INTO daily_weather (city, date, temp_max_c, temp_min_c, rainfall_mm, source)
                VALUES (?, ?, ?, ?, ?, 'backfill')
            """, (CITY, key, row["temp_max_c"], row["temp_min_c"], row["rainfall_mm"]))
            filled += 1
        except sqlite3.IntegrityError:
            print(f"   ⚠️ Record for {key} already exists. Skipping.")
            skipped += 1
        else:
            filled += 1
    conn.commit()
    print(f"Backfill complete: {filled} filled, {skipped} skipped.")


def print_summary(conn: sqlite3.Connection, all_dates: list[date], gap_dates: list[date]):
    print("\n── Data Missing Before Backfill ─────────────────────────────────")
    print(f"Missing {len(gap_dates)} rows before backfill for city {CITY}.")
    if gap_dates:
        for g in gap_dates:
            print(f"   ❌ {g.isoformat()}")
    else:
        print("   ✅ No missing dates before backfill.")

    print("\n── Backfilled Records for Gap Dates ─────────────────────────────")
    if gap_dates:
        placeholders = ",".join("?" for _ in gap_dates)
        rows = conn.execute(
            f"SELECT date, temp_max_c, temp_min_c, rainfall_mm, source FROM daily_weather WHERE city = ? AND date IN ({placeholders}) ORDER BY date DESC",
            (CITY, *[d.isoformat() for d in gap_dates]),
        ).fetchall()
        print(f"{'Date':<14} {'Max °C':>8} {'Min °C':>8} {'Rain mm':>9} {'Source':<10}")
        print("-" * 55)
        for r in rows:
            print(f"{r[0]:<14} {str(r[1]):>8} {str(r[2]):>8} {str(r[3]):>9} {r[4]:<10}")
        after_count = len(rows)
        print(f"\nAfter backfill, {after_count} of {len(gap_dates)} gap dates now have rows.")
    else:
        print("No gap dates were backfilled.")

    print("\n── Final Table ──────────────────────────────")
    print(f"{'Date':<14} {'Max °C':>8} {'Min °C':>8} {'Rain mm':>9} {'Source':<10}")
    print("-" * 55)
    rows = conn.execute(
        "SELECT date, temp_max_c, temp_min_c, rainfall_mm, source FROM daily_weather WHERE city = ? ORDER BY date",
        (CITY,),
    ).fetchall()
    for r in rows:
        print(f"{r[0]:<14} {str(r[1]):>8} {str(r[2]):>8} {str(r[3]):>9} {r[4]:<10}")
 
    total = conn.execute("SELECT COUNT(*) FROM daily_weather WHERE city=?", (CITY,)).fetchone()[0]
    backfilled = conn.execute("SELECT COUNT(*) FROM daily_weather WHERE city=? AND source='backfill'", (CITY,)).fetchone()[0]
    print(f"\n📊 Total rows: {total}  |  Backfilled: {backfilled}  |  Expected: {len(all_dates)}")


def main():
    print("=" * 60)
    print("  Backfill Demo — Open-Meteo Historical Weather API")
    print(f"  City: {CITY}  |  Range: {START_DATE} → {END_DATE}")
    print("=" * 60)
    all_dates = [START_DATE + timedelta(days=i) for i in range((END_DATE - START_DATE).days + 1)]
    with sqlite3.connect(DB_FILE) as conn:
        init_db(conn)
        seed_existing_data(conn, all_dates)
        gap_dates = find_gaps(conn, all_dates)
        if not gap_dates:
            print("No gaps to backfill. Exiting.")
            return
        weather_data = fetch_weather(gap_dates)
        backfill_data(conn, gap_dates, weather_data)
        print_summary(conn, all_dates, gap_dates)
        print("Fetched weather data for gaps:")
        for dt in gap_dates:
            print(f"   ✅ {dt.isoformat()}: {weather_data.get(dt.isoformat(), 'No data')}")

if __name__ == "__main__":
    main()
