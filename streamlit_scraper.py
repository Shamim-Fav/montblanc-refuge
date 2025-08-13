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
refuge_list = [
    # Swiss
    (156, "Auberge la Grande Ourse", "Swiss"),
    (191, "Hotel du Col de Fenêtre", "Swiss"),
    (25, "Relais d'Arpette", "Swiss"),
    (283, "Maya-Joie", "Swiss"),
    (322, "Gîte La Léchère", "Swiss"),
    (329, "Refuge Le Peuty", "Swiss"),
    (406, "Gîte de la Fouly", "Swiss"),
    (52, "Auberge Mont-Blanc", "Swiss"),
    (56, "Auberge Gîte Bon Abri", "Swiss"),
    (57, "Chalet 'Le Dolent'", "Swiss"),
    (58, "Gîte Alpage de La Peule", "Swiss"),
    (60, "Hôtel du Col de la Forclaz", "Swiss"),
    (62, "Hôtel Edelweiss", "Swiss"),
    (72, "Pension en Plein Air", "Swiss"),
    (96, "Auberge des Glaciers", "Swiss"),
    # French
    (162, "Gîte le Pontet", "French"),
    (164, "Chalet Les Méandres (ex Tupilak)", "French"),
    (22, "Gîte Mermoud", "French"),
    (23, "Refuge de Nant Borrant", "French"),
    (28, "Refuge du Fioux", "French"),
    (413, "Les Chambres du Soleil", "French"),
    (416, "Refuge des Prés", "French"),
    (428, "Gîte Les Mélèzes", "French"),
    (445, "La Ferme à Piron", "French"),
    (47, "Refuge des Mottets", "French"),
    (49, "Refuge de la Balme", "French"),
    (50, "Auberge du Truc", "French"),
    (54, "Auberge la Boërne", "French"),
    (64, "Chalet Alpin du Tour", "French"),
    (67, "Gîte Le Moulin", "French"),
    (69, "Gîte Michel Fagot", "French"),
    (76, "Auberge-Refuge de la Nova", "French"),
    (93, "Gîte d'Alpage Les Ecuries de Charamillon", "French"),
    # Italian
    (26, "Rifugio G. Bertone", "Italian"),
    (31, "Rifugio Monte Bianco - Cai Uget", "Italian"),
    (36, "Hôtel Lavachey", "Italian"),
    (37, "Hôtel Funivia", "Italian"),
    (39, "Rifugio Maison Vieille", "Italian"),
    (41, "Gite le Randonneur du Mont Blanc", "Italian"),
    (476, "Rifugio Chapy Mont-Blanc", "Italian"),
    (71, "Hôtel Chalet Val Ferret", "Italian"),
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
    refuge_id = None
    map_btn = div.select_one('a.bouton.carte')
    if map_btn and 'onclick' in map_btn.attrs:
        m = re.search(r'openPopupRefuge\("(\d+)"\)', map_btn['onclick'])
        if m:
            refuge_id = m.group(1)

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

    date_list = []
    for offset in range(-5, 6):
        dt = center_date + timedelta(days=offset)
        date_list.append(dt.strftime("%d/%m/%Y"))
    return date_list

def run_scraper(selected_names, selected_dates):
    session = requests.Session()
    all_results = []

    for date_input in selected_dates:
        try:
            current_date = datetime.strptime(date_input, "%d/%m/%Y")
        except ValueError:
            st.error(f"Invalid date format: {date_input}")
            continue

        day = current_date.strftime("%d")
        month = current_date.strftime("%m")
        year = current_date.strftime("%Y")

        # We still post all REFUGE_IDS for server, but filter later by name
        REFUGE_IDS_ALL = ",".join([str(rid) for rid, _, _ in refuge_list])

        post_data = {
            "NumEtape": "2",
            "OSRecherche_caldatedeb4189": date_input,
            "Globales/JourDebut": day,
            "Globales/MoisDebut": month,
            "Globales/AnDebut": year,
            "Globales/ListeIdFournisseur": REFUGE_IDS_ALL,
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
                    refuge_info['query_date'] = date_input
                    all_results.append(refuge_info)
        except Exception as e:
            st.warning(f"Error on {date_input}: {e}")

    # Filter by selected names
    filtered_results = [r for r in all_results if r["name"] in selected_names]

    if filtered_results:
        df = pd.DataFrame(filtered_results)
        df.insert(0, "S.No", range(1, len(df) + 1))

        st.success("Filtered results ready!")

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Availability")
        st.download_button(
            label="Download Excel",
            data=output.getvalue(),
            file_name="Mont Blanc Refuge Availability.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.dataframe(df)
    else:
        st.info("No results found for the selected refuges and dates.")

# -------------------------
# Streamlit UI
# -------------------------
st.image("BTA_LOGO_square.webp", width=120)
st.title("Mont Blanc Refuge Availability")

# Region logos
col1, col2, col3 = st.columns(3)
with col1:
    st.image("logo_french.png", width=80)
with col2:
    st.image("logo_italian.png", width=80)
with col3:
    st.image("logo_swiss.png", width=80)

# Prepare regions
selected_french = st.multiselect("French Refuges", sorted(region_french), key="french", height=200)
selected_italian = st.multiselect("Italian Refuges", sorted(region_italian), key="italian", height=200)
selected_swiss = st.multiselect("Swiss Refuges", sorted(region_swiss), key="swiss", height=200)

# Refuge selection
selected_french = st.multiselect("French Refuges", sorted(region_french), key="french", height=200)
selected_italian = st.multiselect("Italian Refuges", sorted(region_italian), key="italian", height=200)
selected_swiss = st.multiselect("Swiss Refuges", sorted(region_swiss), key="swiss", height=200)

# Combine selected names
selected_refuges = selected_french + selected_italian + selected_swiss

# Date input
start_date_str = st.text_input("Enter Main Start Date (dd/mm/yyyy):", "")
selected_dates = []
if start_date_str:
    date_options = generate_date_range(start_date_str)
    selected_dates = st.multiselect("Select Dates to Check", options=date_options, default=date_options)

# Run scraper
if st.button("Run Scraper"):
    if not selected_refuges:
        st.warning("Please select at least one refuge.")
    elif not selected_dates:
        st.warning("Please select at least one date.")
    else:
        run_scraper(selected_refuges, selected_dates)

