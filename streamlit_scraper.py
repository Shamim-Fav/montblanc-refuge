# streamlit_scraper.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
from datetime import datetime, timedelta

# ------------------------
# App Configuration
# ------------------------
st.set_page_config(
    page_title="Mont Blanc Refuge Availability",
    page_icon="⛰️",
    layout="centered"
)

# ------------------------
# Logo and Title
# ------------------------
st.image("BTA_LOGO_square.webp", width=150)
st.title("Mont Blanc Refuge Availability")

# ------------------------
# Helper Functions
# ------------------------
def get_dates_list(main_date_str, days_before_after=5):
    """Generate a list of dates from -days_before to +days_after around main_date."""
    main_date = datetime.strptime(main_date_str, "%d/%m/%Y")
    return [(main_date + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(-days_before_after, days_before_after + 1)]

def scrape_availability(refuge_ids, dates):
    """Scrape availability data for given refuges and dates."""
    results = []
    for date_str in dates:
        st.write(f"Checking availability for {date_str}...")
        for refuge_id in refuge_ids:
            # Example scraping URL (replace with real one)
            url = f"https://example.com/refuge/{refuge_id}?date={date_str}"
            try:
                r = requests.get(url, timeout=10)
                soup = BeautifulSoup(r.text, "html.parser")
                name = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Unknown"
                available = "Available" if "available" in r.text.lower() else "Not Available"
                results.append({
                    "Name": name,
                    "Date": date_str,
                    "Availability": available,
                    "URL": url
                })
            except Exception as e:
                results.append({
                    "Name": "Error",
                    "Date": date_str,
                    "Availability": str(e),
                    "URL": url
                })
    return results

# ------------------------
# Sidebar Inputs
# ------------------------
st.sidebar.header("Settings")
main_start_date = st.sidebar.text_input("Enter Main Start Date (dd/mm/yyyy):", "")
days_range = st.sidebar.slider("Days Before/After Main Date", min_value=0, max_value=10, value=5)

refuge_ids_input = st.sidebar.text_area("Enter Refuge IDs (comma-separated):", "123,456")
refuge_ids = [rid.strip() for rid in refuge_ids_input.split(",") if rid.strip()]

if main_start_date:
    all_dates = get_dates_list(main_start_date, days_range)
    selected_dates = st.sidebar.multiselect("Select Dates to Check:", all_dates, default=all_dates)
else:
    selected_dates = []

# ------------------------
# Run Scraper Button
# ------------------------
if st.button("Run Availability Check"):
    if not selected_dates:
        st.error("Please select at least one date.")
    else:
        data = scrape_availability(refuge_ids, selected_dates)
        df = pd.DataFrame(data)

        # Encode CSV as UTF-8 with BOM for proper display of accents
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        csv_data = csv_buffer.getvalue()

        st.success("Filtered results ready!")
        st.dataframe(df)

        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="filtered_availability_results.csv",
            mime="text/csv"
        )
