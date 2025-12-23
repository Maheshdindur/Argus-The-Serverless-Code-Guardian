import os

def database_connect():
    # SECURITY LEAK: Hardcoded password!
    db_password = "SuperSecretPassword123!" 
    print(f"Connecting to DB with {db_password}")

def calculate_price(quantity):
    # LOGIC BUG: Infinite loop risk if quantity is 0
    while quantity > 0:
        print("Adding item...")
        # Forgot to decrement quantity! This will run forever.
    
    return 100

database_connect()
