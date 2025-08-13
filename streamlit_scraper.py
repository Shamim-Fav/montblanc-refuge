import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import io

# ----------------------------
# App title & description
# ----------------------------
st.set_page_config(page_title="Mont Blanc Refuge Availability", page_icon="🏔", layout="centered")
st.title("🏔 Mont Blanc Refuge Availability")

st.write("Check hut availability for your selected dates without losing special characters in downloads.")

# ----------------------------
# Helper functions
# ----------------------------
def fetch_availability(refuge_id, date):
    url = f"https://example.com/api/{refuge_id}?date={date}"  # Replace with real URL
    response = requests.get(url)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    # Parse data from soup here...
    return {
        "Name": "Hôtel du Col de la Forclaz",  # Example
        "Date": date,
        "Status": "Available"
    }

def run_scraper(selected_ids, selected_dates):
    results = []
    for d in selected_dates:
        st.write(f"Checking availability for {d}...")
        for r in selected_ids:
            data = fetch_availability(r, d)
            if data:
                results.append(data)

    if not results:
        st.error("❌ No results found for the selected refuges and dates.")
        return

    df = pd.DataFrame(results)
    st.dataframe(df)

    # Export with UTF-8-SIG for Excel
    output_csv = df.to_csv(index=False, encoding="utf-8-sig")
    output_bytes = output_csv.encode("utf-8-sig")

    st.download_button(
        "📥 Download CSV",
        data=output_bytes,
        file_name="filtered_availability_results.csv",
        mime="text/csv"
    )

# ----------------------------
# UI controls
# ----------------------------
refuge_ids = ["refuge1", "refuge2", "refuge3"]  # Replace with real IDs
refuge_names = ["Refuge A", "Refuge B", "Refuge C"]

selected_ids = st.multiselect(
    "Select Refuges",
    options=refuge_ids,
    format_func=lambda x: refuge_names[refuge_ids.index(x)]
)

start_date_str = st.date_input("Main Start Date", datetime.today())
date_range_days = st.slider("Number of days to check", min_value=1, max_value=10, value=5)

if st.button("Run Scraper"):
    selected_dates = [(start_date_str + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(date_range_days)]
    run_scraper(selected_ids, selected_dates)
