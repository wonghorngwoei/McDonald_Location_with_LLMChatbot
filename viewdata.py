import sqlite3

conn = sqlite3.connect("mcdonalds_stores.db")
cursor = conn.cursor()

# Fetch all data from the stores table
cursor.execute("SELECT name FROM stores")
rows = cursor.fetchall()

# Print all data
for row in rows:
    print(row)

conn.close()


# ##show table_info 
# # Connect to the database
# conn = sqlite3.connect("mcdonalds_stores.db")
# cursor = conn.cursor()

# # Get table information (column names and types)
# cursor.execute("PRAGMA table_info(stores)")
# columns = cursor.fetchall()

# # Print column names
# for col in columns:
#     print(col) 

# conn.close()