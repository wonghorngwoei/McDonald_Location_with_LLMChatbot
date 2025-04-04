import json
import requests
import sqlite3
import csv

# Database setup
DB_NAME = "mcdonalds_stores.db"
CSV_FILE = "mcdonalds_stores.csv"

def create_database():
    """Creates the stores table if it doesn't exist with additional columns."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            address TEXT,
            lat TEXT,
            lng TEXT,
            operating_hours TEXT,
            waze_link TEXT,
            telephone TEXT,
            email TEXT,
            has_birthday_party INTEGER DEFAULT 0,
            has_breakfast INTEGER DEFAULT 0,
            has_cashless INTEGER DEFAULT 0,
            has_dessert_center INTEGER DEFAULT 0,
            has_digital_kiosk INTEGER DEFAULT 0,
            has_mccafe INTEGER DEFAULT 0,
            has_wifi INTEGER DEFAULT 0,
            has_mcdelivery INTEGER DEFAULT 0,
            UNIQUE(name, address)  -- Prevents duplicate stores
        )
    ''')
    conn.commit()
    conn.close()

def store_data(name, address, lat, lng, operating_hours, waze_link, telephone, email,
               has_birthday_party, has_breakfast, has_cashless, 
               has_dessert_center, has_digital_kiosk, has_mccafe, 
               has_wifi, has_mcdelivery):
    """Inserts store data into the database, avoiding duplicates."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO stores (
                name, address, lat, lng, operating_hours, waze_link,
                telephone, email, has_birthday_party, has_breakfast,
                has_cashless, has_dessert_center, has_digital_kiosk,
                has_mccafe, has_wifi, has_mcdelivery
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name, address, lat, lng, operating_hours, waze_link,
            telephone, email, has_birthday_party, has_breakfast,
            has_cashless, has_dessert_center, has_digital_kiosk,
            has_mccafe, has_wifi, has_mcdelivery
        ))
        conn.commit()
        print(f"Store -> {name}, {address}")
    except sqlite3.IntegrityError:
        print(f"Skipped (Duplicate) -> {name}, {address}")

    conn.close()

# API Endpoint & Headers
url = "https://www.mcdonalds.com.my/storefinder/index.php"
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://www.mcdonalds.com.my/locate-us",
    "Origin": "https://www.mcdonalds.com.my",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Payload Parameters
payload = {
    "ajax": "1",
    "action": "get_nearby_stores",
    "distance": "10000",
    "lat": "",
    "lng": "",
    "state": "Kuala Lumpur",
    "products": "",
    "address": "Kuala Lumpur, Malaysia",
    "issuggestion": "0",
    "islocateus": "0"
}

# Create the database before fetching data
create_database()

response = requests.post(url, headers=headers, data=payload)

if response.status_code == 200:
    json_data = response.text.lstrip("\ufeff")  # Remove BOM if present
    stores_data = json.loads(json_data)  # Convert text to JSON

    stores_list = stores_data.get("stores", [])  # Get list of stores

    if not stores_list:
        print("No stores found.")
    else:
        print(f"Total Stores Fetched: {len(stores_list)}")

        for store in stores_list:
            name = store.get("name", "N/A")
            address = store.get("address", "N/A")
            lat = store.get("lat", "N/A")
            lng = store.get("lng", "N/A")
            telephone = store.get("telephone", "N/A")
            email = store.get("email", "N/A")

            # Initialize operating hours and all features
            operating_hours = "N/A"
            has_birthday_party = 0
            has_breakfast = 0
            has_cashless = 0
            has_dessert_center = 0
            has_digital_kiosk = 0
            has_mccafe = 0
            has_wifi = 0
            has_mcdelivery = 0

            # Check categories
            categories = store.get("cat", [])
            for cat in categories:
                cat_name = cat.get("cat_name", "")
                if cat_name == "24 Hours":
                    operating_hours = "24 Hours"
                elif cat_name == "Birthday Party":
                    has_birthday_party = 1
                elif cat_name == "Breakfast":
                    has_breakfast = 1
                elif cat_name == "Cashless Facility":
                    has_cashless = 1
                elif cat_name == "Dessert Center":
                    has_dessert_center = 1
                elif cat_name == "Digital Order Kiosk":
                    has_digital_kiosk = 1
                elif cat_name == "McCafe":
                    has_mccafe = 1
                elif cat_name == "WiFi":
                    has_wifi = 1
                elif cat_name == "McDelivery":
                    has_mcdelivery = 1

            # Generate Waze link
            waze_link = f"https://waze.com/ul?ll={lat},{lng}" if lat != "N/A" and lng != "N/A" else "Location not available"

            # Store data into the database
            store_data(
                name, address, lat, lng, operating_hours, waze_link,
                telephone, email, has_birthday_party, has_breakfast,
                has_cashless, has_dessert_center, has_digital_kiosk,
                has_mccafe, has_wifi, has_mcdelivery
            )

            # Print store details
            print(f"Stored in DB -> Store Name: {name}, Address: {address}")

else:
    print(f"Error fetching stores: {response.status_code}")

def export_to_csv():
    """Exports store data from the SQLite database to a CSV file with all new columns."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Fetch all data from the stores table
    cursor.execute("SELECT * FROM stores")
    stores = cursor.fetchall()

    # Define CSV headers with all new columns
    headers = [
        "ID", "Name", "Address", "Latitude", "Longitude", "Operating Hours", "Waze Link",
        "Telephone", "Email", "Birthday Party", "Breakfast", "Cashless Facility",
        "Dessert Center", "Digital Kiosk", "McCafe", "WiFi", "McDelivery"
    ]

    # Write data to CSV
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)  # Write headers
        writer.writerows(stores)  # Write store data

    conn.close()
    print(f"Data successfully exported to {CSV_FILE}")

# Run the export function
export_to_csv()