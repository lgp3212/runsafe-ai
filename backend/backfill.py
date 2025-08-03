import requests
import psycopg2


def fetch_year_of_crashes():
    cutoff_date = "2024-12-15"
    url = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"

    params = {
        "$limit": 50000,
        "$order": "crash_date DESC",
        "$where": f"latitude IS NOT NULL AND longitude IS NOT NULL AND crash_date >= '{cutoff_date}'",
    }

    response = requests.get(url, params=params)
    return response.json()


def insert_crashes_to_db(crashes):
    conn = psycopg2.connect(
        host="localhost", database="runsafe_db", user="lpietrewicz", password=""
    )

    cursor = conn.cursor()

    for crash in crashes:
        try:
            cursor.execute(
                """
                INSERT INTO crashes (collision_id, crash_date, latitude, longitude, injuries, fatalities)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (collision_id) DO NOTHING
            """,
                (
                    crash.get("collision_id"),
                    crash.get("crash_date"),
                    float(crash.get("latitude", 0)),
                    float(crash.get("longitude", 0)),
                    int(crash.get("number_of_persons_injured", 0)),
                    int(crash.get("number_of_persons_killed", 0)),
                ),
            )
        except Exception as e:
            print(f"Error inserting crash {crash.get('collision_id')}: {e}")

    conn.commit()
    conn.close()
    print(f"Inserted crashes into database")


crashes = fetch_year_of_crashes()
insert_crashes_to_db(crashes)
