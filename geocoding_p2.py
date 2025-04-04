import requests
import time
import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google API Key from environment variable
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Function to get coordinates from Google Maps API
def get_coordinates(address):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_API_KEY}
    response = requests.get(base_url, params=params)
    data = response.json()
    
    if data["status"] == "OK":
        location = data["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]
    return "N/A", "N/A"

# Connect to the database
conn = sqlite3.connect("mcdonalds_stores.db")
cursor = conn.cursor()

# Fetch all stored addresses
cursor.execute("SELECT Name, Address FROM stores")
stores = cursor.fetchall()

# Process each store
for store in stores:
    name, address = store
    lat, lng = get_coordinates(address)
    
    # Print store info
    print(f"Store: {name}")
    print(f"Address: {address}")
    print(f"Lat: {lat}, Lng: {lng}")
    print("-" * 50)
    
    time.sleep(1)  # Avoid hitting API rate limits

# Close the database connection
conn.close()