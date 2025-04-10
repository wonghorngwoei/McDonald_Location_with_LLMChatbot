from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import requests
import os
from dotenv import load_dotenv
from chatbot_p5 import router as chatbot_router  # Import chatbot

# Load environment variables
load_dotenv()

# Initialize FastAPI App
app = FastAPI()

# Allow CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change to specific origin in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return None, None

# Database connection dependency
def get_db_connection():
    conn = sqlite3.connect("mcdonalds_stores.db")
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn

# Function to fetch stores from the database
def get_stores():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            name, 
            address, 
            lat, 
            lng, 
            operating_hours, 
            waze_link,
            telephone,
            email,
            has_birthday_party,
            has_breakfast,
            has_cashless,
            has_dessert_center,
            has_digital_kiosk,
            has_mccafe,
            has_wifi,
            has_mcdelivery
        FROM stores
    ''')
    stores = cursor.fetchall()
    conn.close()
    
    store_list = []
    for store in stores:
        store_dict = {
            "name": store["name"],
            "address": store["address"],
            "latitude": store["lat"],
            "longitude": store["lng"],
            "operating_hours": store["operating_hours"],
            "waze_link": store["waze_link"],
            "contact": {
                "telephone": store["telephone"],
                "email": store["email"]
            },
            "features": {
                "birthday_party": bool(store["has_birthday_party"]),
                "breakfast": bool(store["has_breakfast"]),
                "cashless": bool(store["has_cashless"]),
                "dessert_center": bool(store["has_dessert_center"]),
                "digital_kiosk": bool(store["has_digital_kiosk"]),
                "mccafe": bool(store["has_mccafe"]),
                "wifi": bool(store["has_wifi"]),
                "mcdelivery": bool(store["has_mcdelivery"])
            }
        }

        # If lat/lng is missing, fetch from Google Maps API
        if store_dict["latitude"] is None or store_dict["longitude"] is None:
            lat, lng = get_coordinates(store_dict["address"])
            store_dict["latitude"] = lat
            store_dict["longitude"] = lng
    
        store_list.append(store_dict)
    
    return store_list

# API Endpoint to Get All Outlets
@app.get("/stores")
def read_stores():
    return {"stores": get_stores()}

# Include chatbot endpoints
app.include_router(chatbot_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to McDonald's Outlet Map API"}

# Run this first to activate virtual environment: .venv/Scripts/activate
# Run server: uvicorn fastapi_p3:app --reload
