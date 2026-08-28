# Commodity prices per unit (PDS rates) - Phase-8 Updated Prices
COMMODITY_PRICES = {
    "rice": 2.5,           # ₹ per kg
    "wheat": 2,            # ₹ per kg
    "sugar": 7,            # ₹ per kg
    "kerosene": 15,        # ₹ per liter
    "masoor": 20,          # ₹ per kg (mapped from previous urad dal)
    "moong": 30,           # ₹ per kg (mapped from previous toor dal)
    "chana": 25,           # ₹ per kg (mapped from previous chana dal)
    "salt": 3.5,           # ₹ per kg
    "palmoil": 45,         # ₹ per liter (mapped from previous mustard oil)
    "soyabeanoil": 40      # ₹ per liter (mapped from previous sunflower oil)
}

COMMODITY_INFO = {
    "rice": ("Rice", "kg"),
    "wheat": ("Wheat", "kg"),
    "sugar": ("Sugar", "kg"),
    "kerosene": ("Kerosene", "L"),
    "salt": ("Salt", "kg"),
    "soyabeanoil": ("SoyabeanOil", "L"),
    "palmoil": ("PalmOil", "L"),
    "masoor": ("Masoor", "kg"),
    "moong": ("Moong", "kg"),
    "chana": ("Chana", "kg"),
}

# Monthly entitlement limits per household
COMMODITY_LIMITS = {
    "rice": 10,            # kg
    "wheat": 10,           # kg
    "sugar": 5,            # kg
    "kerosene": 3,         # liters
    "masoor": 2,           # kg
    "moong": 2,            # kg
    "chana": 2,            # kg
    "salt": 1,             # kg
    "palmoil": 1,          # liters
    "soyabeanoil": 1       # liters
}

def calculate_bill(**commodities):
    """
    Calculate bill total for commodities.
    Accepts: rice, wheat, sugar, kerosene, masoor, moong, chana, salt, palmoil, soyabeanoil
    """
    total = 0
    for commodity, quantity in commodities.items():
        if commodity in COMMODITY_PRICES and quantity > 0:
            total += quantity * COMMODITY_PRICES[commodity]
    return total
