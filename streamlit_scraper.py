import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

# -------------------------
# CONFIGURATION
# -------------------------

# Logo and title
LOGO_PATH = "/mnt/data/BTA_LOGO_square.webp"
TITLE = "Mont Blanc Refuge Availability"

# Refuge data by region (name only, no IDs)
REGION1 = [
    "Gîte le Pontet","Chalet Les Méandres (ex Tupilak)","Gîte Mermoud",
    "Refuge de Nant Borrant","Refuge du Fioux","Les Chambres du Soleil",
    "Refuge des Prés","Gîte Les Mélèzes","La Ferme à Piron","Refuge des Mottets",
    "Refuge de la Balme","Auberge du Truc","Auberge la Boërne","Chalet Alpin du Tour",
    "Gîte Le Moulin","Gîte Michel Fagot","Auberge-Refuge de la Nova",
    "Gîte d'Alpage Les Ecuries de Charamillon"
]

REGION2 = [
    "Rifugio G. Bertone","Rifugio Monte Bianco - Cai Uget","Hôtel Lavachey",
    "Hôtel Funivia","Rifugio Maison Vieille","Gite le Randonneur du Mont Blanc",
    "Rifugio Chapy Mont-Blanc","Hôtel Chalet Val Ferret"
]

REGION3 = [
    "Auberge la Grande Ourse","Hotel du Col de Fenêtre","Relais d'Arpette",
    "Maya-Joie","Gîte La Léchère","Refuge Le Peuty","Gîte de la Fouly",
    "Auberge Mont-Blanc","Auberge Gîte Bon Abri","Chalet 'Le Dolent'",
    "Gîte Alpage de La Peule","Hôtel du Col de la Forclaz","Hôtel Edelweiss",
    "Pension en Plein Air","Auberge des Glaciers","Chalet La Grange"
]

POST_URL = "https://reservation.montourdumontblanc.com/z7243_uk-.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www.montourdumontblanc.com",
    "Referer": "https://www.montourdumontblanc.com/",
}

# -------------------------
# HELPER FUNCTIONS
# -------------------------
def parse_refuge_block(div):
    """Parse a refuge HTML block into a dictionary"""
    h2 = div.select_one('.entete h2')
    name = h2.get_text(strip=True) if h2 else ""
    altitude = ""
    if h2:
        span_alt = h2.select_one('span.altitude')
        if span_alt:
            altitude = span_alt.get_text(strip=True)
            name = name.replace(span_alt.get_text(), "").strip()
    location = div.select_one('.Lieu')
    location = location.get_text(strip=True) if location else ""
    capacity_total_span = div.select_one('.capacitetotale span.valeur')
    capacity_total = capacity_total_span.get_text(strip=True) if capacity_total_span else ""
    dispo_div = div.select_one('.capacitedispo')
    available_beds = ""
    available_date = ""
    if dispo_div:
        text = dispo_div.get_text(strip=True)
        date_match = re.search(r'\(([^)]+)\)', text)
        if date_match:
            available_date = date_match.group(1)
        beds_match = re.search(r'(\d+)\s*beds', text, re.I)
        if beds_match:
            available_beds = beds_match.group(1)
    return {
        "name": name,
        "altitude": altitude,
        "location": location,
        "capacity_total": capacity_total,
        "available_beds": available_beds,
        "available_date": available_date
    }

def generate_date_range(center_date, days=5):
    """Generate a list of dates ±days around center_date"""
    return [(center_date + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(-days, days+1)]

def run_scraper(selected_refuges, selected_dates):
    """Scrape the website and filter results by selected names"""
    session = requests.Session()
    all_results = []

    for date_input in selected_dates:
        day, month, year = date_input.split('/')

        post_data = {
            "NumEtape": "2",
            "OSRecherche_caldatedeb4189": date_input,
            "Globales/JourDebut": day,
            "Globales/MoisDebut": month,
            "Globales/AnDebut": year,
            "Globales/ListeIdFournisseur": ",".join([str(i) for i in range(1,500000)]),  # all IDs placeholder
            "Param/ListeIdService": "1,2",
            "Param/NbPers": "1",
            "Param/DateRech": date_input
        }

        try:
            response = session.post(POST_URL, data=post_data, headers=HEADERS, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for colphoto_div in soup.select('div.colphoto'):
                parent_div = colphoto_div.parent.parent
                if parent_div:
                    refuge_info = parse_refuge_block(parent_div)
                    if refuge_info["name"] in selected_refuges:
                        refuge_info["query_date"] = date_input
                        all_results.append(refuge_info)
        except Exception as e:
            st.warning(f"Error scraping {date_input}: {e}")

    if all_results:
        df = pd.DataFrame(all_results)
        st.success(f"Found {len(df)} results!")
        st.dataframe(df[['name','altitude','location','capacity_total','available_beds','available_date']])

        # Excel download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Availability')
            writer.save()
        excel_data = output.getvalue()
        st.download_button(
            label="Download Excel",
            data=excel_data,
            file_name=f"{TITLE}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No results found for the selected refuges and dates.")

# -------------------------
# STREAMLIT UI
# -------------------------
st.image(LOGO_PATH, width=150)
st.title(TITLE)

col1, col2, col3 = st.columns(3)
with col1:
    selected_region1 = st.multiselect("French Refuges", sorted(REGION1))
with col2:
    selected_region2 = st.multiselect("Italian Refuges", sorted(REGION2))
with col3:
    selected_region3 = st.multiselect("Swiss Refuges", sorted(REGION3))

selected_refuges = selected_region1 + selected_region2 + selected_region3

start_date = st.date_input("Select Main Start Date")
selected_dates = generate_date_range(start_date)

st.write("Checking availability for dates:", ", ".join(selected_dates))

if st.button("Run Scraper"):
    if not selected_refuges:
        st.warning("Please select at least one refuge.")
    else:
        run_scraper(selected_refuges, selected_dates)
