def calculate_area(radius):
    """Calculates the area of a circle safely."""
    if radius < 0:
        raise ValueError("Radius cannot be negative")
    
    pi = 3.14159
    return pi * (radius ** 2)

if __name__ == "__main__":
    print(f"Area: {calculate_area(5)}")
