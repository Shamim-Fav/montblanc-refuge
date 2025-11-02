# app.py
import streamlit as st
import pandas as pd
import requests
from datetime import timedelta
from io import BytesIO
import time

# ----------------------
# Streamlit UI: Logo + Title
# ----------------------
col_logo, col_title, _ = st.columns([1, 5, 1])
with col_logo:
    st.image("logo.png", width=100)  # Make sure logo.png is in the same folder as app.py
with col_title:
    st.title("Hong Kong – Mandarin Oriental Availability Checker")

st.info("This app checks room availability for **Hong Kong – Mandarin Oriental**")

# ----------------------
# Date inputs
# ----------------------
start_date = st.date_input("Select start date for checking availability")
num_days = st.number_input("How many days to check?", min_value=1, max_value=365, value=60)

# ----------------------
# API setup
# ----------------------
API_URL = "https://www.mandarinoriental.com/api/v1/booking/check-room-availability"

HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "Cookie": "YOUR_CURRENT_COOKIE_HERE",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

def fetch_availability(hotel_id, check_date):
    payload = {
        "hotelCode": str(hotel_id),
        "roomCodes": None,
        "roomName": None,
        "bedType": None,
        "rateCode": None,
        "adultGuestCount": "2",
        "childGuestCount": "0",
        "stayDateStart": check_date.strftime("%Y-%m-%d"),
        "stayDateEnd": (check_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        "primaryLanguageId": "en"
    }
    response = requests.post(API_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"HTTP {response.status_code} for hotel {hotel_id} on {check_date}")
        return None

def parse_response(hotel_id, check_date, data):
    if not data or not data.get("roomStays"):
        return []
    rows = []
    for room in data["roomStays"]:
        for rate in room.get("rates", []):
            rows.append({
                "Hotel Name": "Mandarin Oriental",
                "HotelID": hotel_id,
                "Date": check_date.strftime("%Y-%m-%d"),
                "RoomType": room.get("title"),
                "Total": rate.get("total"),
                "Taxes": rate.get("taxes"),
                "Fees": rate.get("fees"),
                "MaxGuests": room.get("maxGuests"),
                "ShortDescription": rate.get("shortDescription"),
                "LongDescription": rate.get("longDescription"),
                "Image": rate.get("image")
            })
    return rows

# ----------------------
# Main logic
# ----------------------
if st.button("Start Checking"):
    hotel_id = 514
    all_rows = []

    progress_bar = st.progress(0)
    status_text = st.empty()
    start_time = time.time()

    for day_offset in range(num_days):
        check_date = pd.to_datetime(start_date) + timedelta(days=day_offset)
        data = fetch_availability(hotel_id, check_date)
        parsed_rows = parse_response(hotel_id, check_date, data)
        if parsed_rows:
            all_rows.extend(parsed_rows)

        # Update progress bar and estimated time remaining
        progress = (day_offset + 1) / num_days
        progress_bar.progress(progress)
        elapsed_time = time.time() - start_time
        estimated_total_time = elapsed_time / progress
        remaining_time = estimated_total_time - elapsed_time
        status_text.text(f"{int(progress*100)}% completed – Estimated time remaining: {int(remaining_time)}s")

    status_text.text("Checking complete!")

    if all_rows:
        result_df = pd.DataFrame(all_rows)
        buffer = BytesIO()
        result_df.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            label="Download Results Excel",
            data=buffer,
            file_name="hongkong_mandarin_oriental_availability.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No availability found.")
