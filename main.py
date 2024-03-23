from typing import List, Optional, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import math

app = FastAPI()

# SQLite connection
conn = sqlite3.connect('addresses.db')
c = conn.cursor()

# Create table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS addresses
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              address TEXT NOT NULL,
              latitude REAL NOT NULL,
              longitude REAL NOT NULL)''')
conn.commit()


class Address(BaseModel):
    address: str
    latitude: float
    longitude: float


def validate_address_coordinates(latitude: float, longitude: float) -> bool:
    if -90 <= latitude <= 90 and -180 <= longitude <= 180:
        return True
    return False


@app.post("/addresses/", response_model=Address)
def create_address(address: Address):
    if not validate_address_coordinates(address.latitude, address.longitude):
        raise HTTPException(status_code=400, detail="Invalid coordinates")

    with conn:
        c.execute("INSERT INTO addresses (address, latitude, longitude) VALUES (?, ?, ?)",
                  (address.address, address.latitude, address.longitude))
        address_id = c.lastrowid

    return {**address.dict(), "id": address_id}


@app.put("/addresses/{address_id}", response_model=Address)
def update_address(address_id: int, address: Address):
    if not validate_address_coordinates(address.latitude, address.longitude):
        raise HTTPException(status_code=400, detail="Invalid coordinates")

    with conn:
        c.execute("UPDATE addresses SET address=?, latitude=?, longitude=? WHERE id=?",
                  (address.address, address.latitude, address.longitude, address_id))

    return {**address.dict(), "id": address_id}


@app.delete("/addresses/{address_id}")
def delete_address(address_id: int):
    with conn:
        c.execute("DELETE FROM addresses WHERE id=?", (address_id,))


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371  
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance


@app.get("/addresses/")
def get_addresses_within_distance(latitude: float, longitude: float, distance: float = 10.0) -> List[Address]:
    addresses = []
    with conn:
        c.execute("SELECT * FROM addresses")
        rows = c.fetchall()
        for row in rows:
            address_id, address_str, lat, lon = row
            if calculate_distance(latitude, longitude, lat, lon) <= distance:
                addresses.append({"id": address_id, "address": address_str, "latitude": lat, "longitude": lon})
    return addresses
