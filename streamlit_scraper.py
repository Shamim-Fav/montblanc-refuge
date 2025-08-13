import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

# -------------------------
# Configuration
# -------------------------
REFUGE_IDS = "32383,32365,123462,127958,32357,32358,32356,32369,32372,39948,32361,39796,39797,32362,116702,32379,32378,36470,67403,32789,32368,116701,32367,32366,32405,39703,32406,32404,32398,32395,114712,32394,46179,32399,32397,32396,32403,32400,32401,32393,32391,32385,32390,32388,32389,32386,36471,32377,133634"

# Regions with refuge names
region_french = [
    "Gîte le Pontet", "Chalet Les Méandres (ex Tupilak)", "Gîte Mermoud", 
    "Refuge de Nant Borrant", "Refuge du Fioux", "Les Chambres du Soleil",
    "Refuge des Prés", "Gîte Les Mélèzes", "La Ferme à Piron", "Refuge des Mottets",
    "Refuge de la Balme", "Auberge du Truc", "Auberge la Boërne", "Chalet Alpin du Tour",
    "Gîte Le Moulin", "Gîte Michel Fagot", "Auberge-Refuge de la Nova",
    "Gîte d'Alpage Les Ecuries de Charamillon"
]

region_italian = [
    "Rifugio G. Bertone", "Rifugio Monte Bianco - Cai Uget", "Hôtel Lavachey", 
    "Hôtel Funivia", "Rifugio Maison Vieille", "Gite le Randonneur du Mont Blanc",
    "Rifugio Chapy Mont-Blanc", "Hôtel Chalet Val Ferret"
]

region_swiss = [
    "Auberge la Grande Ourse", "Hotel du Col de Fenêtre", "Relais d'Arpette",
    "Maya-Joie", "Gîte La Léchère", "Refuge Le Peuty", "Gîte de la Fouly",
    "Auberge Mont-Blanc", "Auberge Gîte Bon Abri", "Chalet 'Le Dolent'",
    "Gîte Alpage de La Peule", "Hôtel du Col de la Forclaz", "Hôtel Edelweiss",
    "Pension en Plein Air", "Auberge des Glaciers", "Chalet La Grange"
]

POST_URL = "https://reservation.montourdumontblanc.com/z7243_uk-.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www.montourdumontblanc.com",
    "Referer": "https://www.montourdumontblanc.com/",
}

# -------------------------
# Helper functions
# -------------------------
def parse_refuge_block(div):
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

def generate_date_range(center_date_str):
    try:
        center_date = datetime.strptime(center_date_str, "%d/%m/%Y")
    except ValueError:
        st.error("Invalid start date format. Use dd/mm/yyyy.")
        return []

    return [(center_date + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(-5, 6)]

def run_scraper(selected_names, selected_dates):
    session = requests.Session()
    all_results = []

    for date_input in selected_dates:
        day, month, year = date_input.split("/")

        post_data = {
            "NumEtape": "2",
            "OSRecherche_caldatedeb4189": date_input,
            "Globales/JourDebut": day,
            "Globales/MoisDebut": month,
            "Globales/AnDebut": year,
            "Globales/ListeIdFournisseur": REFUGE_IDS,  # keep all IDs
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
                    info = parse_refuge_block(parent_div)
                    if info["name"] in selected_names:
                        info["query_date"] = date_input
                        all_results.append(info)

        except Exception as e:
            st.warning(f"Error scraping {date_input}: {e}")

    if all_results:
        df = pd.DataFrame(all_results)

        # Add serial starting from 1
        df.insert(0, "S.No", range(1, len(df) + 1))

        st.success(f"Found {len(df)} results!")
        st.dataframe(df[['S.No','name','altitude','location','capacity_total','available_beds','available_date']])

        # Excel download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Availability')
        excel_data = output.getvalue()
        st.download_button(
            label="Download Excel",
            data=excel_data,
            file_name="Mont Blanc Refuge Availability.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No results found for the selected refuges and dates.")

# -------------------------
# Streamlit UI
# -------------------------
# Logo + Title
col_logo, col_title, _ = st.columns([1,5,1])
with col_logo:
    st.image("logo_french.png", width=80)
with col_title:
    st.title("Mont Blanc Refuge Availability")

# Side-by-side multiselects for three regions with logos
col1, col2, col3 = st.columns(3)

with col1:
    st.image("logo_french.png", width=80)
    selected_french = st.multiselect("French Refuges", options=sorted(region_french))
with col2:
    st.image("logo_italian.png", width=80)
    selected_italian = st.multiselect("Italian Refuges", options=sorted(region_italian))
with col3:
    st.image("logo_swiss.png", width=80)
    selected_swiss = st.multiselect("Swiss Refuges", options=sorted(region_swiss))

selected_refuges = selected_french + selected_italian + selected_swiss

# Date input
start_date_str = st.text_input("Enter Main Start Date (dd/mm/yyyy):", "")
selected_dates = []
if start_date_str:
    date_options = generate_date_range(start_date_str)
    selected_dates = st.multiselect(
        "Select Dates to Check:",
        options=date_options,
        default=date_options
    )

# Run scraper
if st.button("Run Scraper"):
    if not selected_refuges:
        st.warning("Please select at least one refuge.")
    elif not selected_dates:
        st.warning("Please select at least one date.")
    else:
        run_scraper(selected_refuges, selected_dates)
