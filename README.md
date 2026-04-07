# 🔁 Backfill Demo — Historical Weather Data

A minimal Python demo showing how a backfill job works in data engineering — detect gaps in a table, fetch missing data from a public API, and fill them back in.

## What it does

1. **Seeds** 30 days of NYC weather into a local SQLite DB — intentionally skipping 5 dates to simulate pipeline failures
2. **Detects** missing dates by diffing the DB against the expected date range
3. **Fetches** the missing data from the [Open-Meteo](https://open-meteo.com/) historical weather API
4. **Backfills** the gaps, tagging rows as `source='backfill'` for auditability

## Quickstart

```bash
pip install requests
python main.py
```

No API key required.

## API Used

**Open-Meteo Archive API** — free, public, no auth.

```
GET https://archive-api.open-meteo.com/v1/archive
    ?latitude=40.7128&longitude=-74.0060
    &start_date=2026-03-01&end_date=2026-03-07
    &daily=temperature_2m_max,temperature_2m_min,precipitation_sum
    &timezone=America/New_York
```

## Schema

```sql
CREATE TABLE daily_weather (
    city        TEXT,
    date        TEXT,
    temp_max_c  REAL,
    temp_min_c  REAL,
    rainfall_mm REAL,
    source      TEXT,   -- 'pipeline' or 'backfill'
    PRIMARY KEY (city, date)
)
```


