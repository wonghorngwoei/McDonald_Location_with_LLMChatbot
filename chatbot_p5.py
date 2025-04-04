import os
import sqlite3
import together
from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict

# Load environment variables
from dotenv import load_dotenv

load_dotenv()
together.api_key = os.getenv("TOGETHER_API_KEY")
if not together.api_key:
    raise HTTPException(status_code=500, detail="Together.AI API key not configured")

MODEL_NAME = "meta-llama/Llama-2-70b-hf"

# Initialize FastAPI Router
router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

# ========== DATABASE FUNCTIONS ==========
def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect("mcdonalds_stores.db")
    conn.row_factory = sqlite3.Row
    return conn

def execute_sql_query(sql_query: str) -> List[Dict]:
    """Execute an SQL query and return results as a list of dictionaries"""
    if not sql_query.lower().startswith("select"):
        return [{"error": "Invalid query"}]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(sql_query)
        results = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        results = [{"error": str(e)}]

    conn.close()
    return results

# ========== LLM-GENERATED SQL QUERY ==========
def generate_sql_query(user_query: str) -> str:
    """Use Llama-2 to generate an SQL query based on user input"""
    # Preprocess the query to handle common abbreviations
    preprocessed_query = user_query.lower().strip()
    
    # Replace "KL" with "Kuala Lumpur" in the query for better matching
    import re
    preprocessed_query = re.sub(r'\bkl\b', 'kuala lumpur', preprocessed_query)
    
    # Special case handling for specific 24-hour query
    if ("which outlets" in preprocessed_query and 
        "operate 24 hours" in preprocessed_query and 
        ("kl" in preprocessed_query or "kuala lumpur" in preprocessed_query)):
        return """SELECT * FROM stores 
               WHERE operating_hours LIKE '%24%' 
               AND (address LIKE '%kuala lumpur%' OR address LIKE '%kl%')
               AND name NOT LIKE '%klia%'"""
    
    # Special case handling for birthday party query
    if ("which outlet" in preprocessed_query and 
        "allows birthday parties" in preprocessed_query):
        return """SELECT * FROM stores 
               WHERE has_birthday_party = 1
               AND (address LIKE '%kuala lumpur%' OR address LIKE '%kl%')
               AND name NOT LIKE '%klia%'"""
    
    # For debugging
    if preprocessed_query != user_query.lower():
        print(f"Preprocessed query: '{preprocessed_query}' (original: '{user_query}')")

    prompt = f"""You are an expert SQL assistant. Generate an SQL query based on the user's question.

Database Table: `stores`
Columns: 
- id, name, address, lat, lng, operating_hours, waze_link (basic info)
- telephone, email (contact info)
- has_birthday_party, has_breakfast, has_cashless, has_dessert_center (features)
- has_digital_kiosk, has_mccafe, has_wifi, has_mcdelivery (more features)

Rules:
1. Only generate `SELECT` queries.
2. Filter using `WHERE` clauses.
3. Ensure the SQL query is compatible with SQLite.
4. Do NOT use `DROP`, `DELETE`, `INSERT`, or `UPDATE`.
5. Return ONLY the SQL query. No explanations.
6. For location queries, be inclusive with LIKE operators.
7. For feature queries, use the has_* columns (1 = yes, 0 = no).
8. When searching for "kuala lumpur", also include "kl" in the search.

Examples:
User: "Which outlets in KL operate 24 hours?"
SQL: SELECT * FROM stores WHERE operating_hours LIKE '%24%' AND (address LIKE '%kuala lumpur%' OR address LIKE '%kl%');

User: "List outlets that allow birthday parties"
SQL: SELECT * FROM stores WHERE has_birthday_party = 1;

User: "Find 24-hour McDonald's with WiFi in KL"
SQL: SELECT * FROM stores WHERE operating_hours LIKE '%24%' AND has_wifi = 1 AND (address LIKE '%kuala lumpur%' OR address LIKE '%kl%');

User: "Show McDonald's with McCafe and breakfast"
SQL: SELECT * FROM stores WHERE has_mccafe = 1 AND has_breakfast = 1;

User Query: "{user_query}"
SQL:"""

    try:
        response = together.Complete.create(
            prompt=prompt,
            model="meta-llama/Llama-2-70b-hf",
            max_tokens=150,
            temperature=0.2,
            stop=["\n"]
        )

        if "choices" in response and response["choices"]:
            sql_query = response["choices"][0]["text"].strip()
            if sql_query:
                return sql_query
            return "Error: Empty response from LLM"
        return "Error: Invalid LLM response format"

    except Exception as e:
        return f"Error: {str(e)}"

def format_store_response(store_data: Dict) -> Dict:
    """Format store data for the API response"""
    return {
        "name": store_data.get("name", "N/A"),
        "address": store_data.get("address", "N/A"),
        "coordinates": {
            "latitude": store_data.get("lat"),
            "longitude": store_data.get("lng")
        },
        "operating_hours": store_data.get("operating_hours", "N/A"),
        "waze_link": store_data.get("waze_link", "N/A"),
        "contact": {
            "telephone": store_data.get("telephone", "N/A"),
            "email": store_data.get("email", "N/A")
        },
        "features": {
            "24_hours": "24 Hours" in str(store_data.get("operating_hours", "")),
            "birthday_party": bool(store_data.get("has_birthday_party", 0)),
            "breakfast": bool(store_data.get("has_breakfast", 0)),
            "cashless": bool(store_data.get("has_cashless", 0)),
            "dessert_center": bool(store_data.get("has_dessert_center", 0)),
            "digital_kiosk": bool(store_data.get("has_digital_kiosk", 0)),
            "mccafe": bool(store_data.get("has_mccafe", 0)),
            "wifi": bool(store_data.get("has_wifi", 0)),
            "mcdelivery": bool(store_data.get("has_mcdelivery", 0))
        }
    }

def initialize_database():
    """Create the stores table if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stores (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        lat REAL,
        lng REAL,
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
        has_mcdelivery INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized with 'stores' table")

@router.get("/")
def chatbot_query(query: str = Query(..., min_length=3, example="Find McDonald's with McCafe")):
    """Chatbot that retrieves McDonald's store details based on user queries"""
    query_lower = query.lower().strip()
    
    # First check if this is a specific location/feature query
    is_location_query = any(term in query_lower for term in [
        "outlets", "stores", "locations", "find", "list", "which",
        "24 hour", "24-hour", "birthday", "parties", "mccafe", "wifi"
    ])
    
    # Only handle conversational phrases if this isn't a location/feature query
    if not is_location_query:
        # Handle conversational phrases
        gratitude_phrases = ["thank you", "thanks", "appreciate it", "cheers"]
        if any(phrase in query_lower for phrase in gratitude_phrases):
            return {
                "response": "You're welcome! Happy to help with McDonald's locations and features.",
                "matches": 0,
                "data": []
            }
        
        greeting_phrases = ["hi", "hello", "hey", "greetings"]
        if any(phrase in query_lower for phrase in greeting_phrases):
            return {
                "response": "Hello! I can help you find McDonald's locations and their features (like McCafe, WiFi, etc.). What are you looking for?",
                "matches": 0,
                "data": []
            }
        
        farewell_phrases = ["bye", "goodbye", "see you", "farewell"]
        if any(phrase in query_lower for phrase in farewell_phrases):
            return {
                "response": "Goodbye! Come back if you need more help finding McDonald's locations or their features.",
                "matches": 0,
                "data": []
            }

    # Generate SQL query
    sql_query = generate_sql_query(query)
    
    if sql_query.startswith("Error:"):
        return {
            "response": "I'm sorry, I encountered an issue processing your request. Please try again with a different question.",
            "matches": 0,
            "data": []
        }

    results = execute_sql_query(sql_query)
    
    if not results or "error" in results[0]:
        return {
            "response": "I couldn't find any matching McDonald's locations. Try a different location or ask about specific features.",
            "matches": 0,
            "data": []
        }
    
    # Format the results with all features
    formatted_results = [format_store_response(store) for store in results]
    
    # Generate appropriate response text
    if "24 hour" in query_lower or "24-hour" in query_lower:
        if "kl" in query_lower or "kuala lumpur" in query_lower:
            response_text = f"Found {len(results)} 24-hour McDonald's locations in Kuala Lumpur:"
        else:
            response_text = f"Found {len(results)} 24-hour McDonald's locations:"
    elif "birthday party" in query_lower or "birthday parties" in query_lower:
        response_text = f"Found {len(results)} McDonald's locations that allow birthday parties:"
    else:
        response_text = f"Found {len(results)} McDonald's locations matching your query:"

    return {
        "query": query,
        "response": response_text,
        "sql_query": sql_query,
        "matches": len(results),
        "data": formatted_results
    }