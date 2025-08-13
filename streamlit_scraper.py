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
    (156, "Auberge la Grande Ourse"),
    (162, "Gîte le Pontet"),
    (164, "Chalet Les Méandres (ex Tupilak)"),
    (191, "Hotel du Col de Fenêtre"),
    (22, "Gîte Mermoud"),
    (23, "Refuge de Nant Borrant"),
    (25, "Relais d'Arpette"),
    (26, "Rifugio G. Bertone"),
    (28, "Refuge du Fioux"),
    (283, "Maya-Joie"),
    (31, "Rifugio Monte Bianco - Cai Uget"),
    (322, "Gîte La Léchère"),
    (329, "Refuge Le Peuty"),
    (36, "Hôtel Lavachey"),
    (37, "Hôtel Funivia"),
    (39, "Rifugio Maison Vieille"),
    (406, "Gîte de la Fouly"),
    (41, "Gite le Randonneur du Mont Blanc"),
    (413, "Les Chambres du Soleil"),
    (416, "Refuge des Prés"),
    (428, "Gîte Les Mélèzes"),
    (445, "La Ferme à Piron"),
    (47, "Refuge des Mottets"),
    (476, "Rifugio Chapy Mont-Blanc"),
    (49, "Refuge de la Balme"),
    (50, "Auberge du Truc"),
    (52, "Auberge Mont-Blanc"),
    (54, "Auberge la Boërne"),
    (56, "Auberge Gîte Bon Abri"),
    (57, "Chalet 'Le Dolent'"),
    (58, "Gîte Alpage de La Peule"),
    (60, "Hôtel du Col de la Forclaz"),
    (62, "Hôtel Edelweiss"),
    (64, "Chalet Alpin du Tour"),
    (67, "Gîte Le Moulin"),
    (69, "Gîte Michel Fagot"),
    (71, "Hôtel Chalet Val Ferret"),
    (72, "Pension en Plein Air"),
    (76, "Auberge-Refuge de la Nova"),
    (93, "Gîte d'Alpage Les Ecuries de Charamillon"),
    (96, "Auberge des Glaciers"),
]

# -------------------------
# Region lists
# -------------------------
region_french = [
    "Gîte le Pontet","Chalet Les Méandres (ex Tupilak)","Gîte Mermoud","Refuge de Nant Borrant",
    "Refuge du Fioux","Les Chambres du Soleil","Refuge des Prés","Gîte Les Mélèzes",
    "La Ferme à Piron","Refuge des Mottets","Refuge de la Balme","Auberge du Truc",
    "Auberge la Boërne","Chalet Alpin du Tour","Gîte Le Moulin","Gîte Michel Fagot",
    "Auberge-Refuge de la Nova","Gîte d'Alpage Les Ecuries de Charamillon"
]

region_italian = [
    "Rifugio G. Bertone","Rifugio Monte Bianco - Cai Uget","Hôtel Lavachey",
    "Hôtel Funivia","Rifugio Maison Vieille","Gite le Randonneur du Mont Blanc",
    "Rifugio Chapy Mont-Blanc","Hôtel Chalet Val Ferret"
]

region_swiss = [
    "Auberge la Grande Ourse","Hotel du Col de Fenêtre","Relais d'Arpette",
    "Maya-Joie","Gîte La Léchère","Refuge Le Peuty","Gîte de la Fouly",
    "Auberge Mont-Blanc","Auberge Gîte Bon Abri","Chalet 'Le Dolent'",
    "Gîte Alpage de La Peule","Hôtel du Col de la Forclaz","Hôtel Edelweiss",
    "Pension en Plein Air","Auberge des Glaciers","Chalet La Grange"
]

name_to_id = {name: str(rid) for rid, name in refuge_list}

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
        "id": refuge_id,
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

        post_data = {
            "NumEtape": "2",
            "OSRecherche_caldatedeb4189": date_input,
            "Globales/JourDebut": day,
            "Globales/MoisDebut": month,
            "Globales/AnDebut": year,
            "Globales/ListeIdFournisseur": ",".join(name_to_id.values()),
            "Param/ListeIdService": "1,2",
            "Param/NbPers": "1",
            "Param/DateRech": date_input
        }

        success = False
        for attempt in range(3):
            try:
                response = session.post(POST_URL, data=post_data, headers=HEADERS, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                for colphoto_div in soup.select('div.colphoto'):
                    parent_div = colphoto_div.parent.parent
                    if parent_div:
                        refuge_info = parse_refuge_block(parent_div)
                        if refuge_info["name"] in selected_names:
                            refuge_info['query_date'] = date_input
                            all_results.append(refuge_info)
                success = True
                break
            except Exception as e:
                st.warning(f"Error on {date_input} attempt {attempt+1}: {e}")

        if not success:
            st.error(f"Failed to get data for {date_input} after 3 attempts.")

    if all_results:
        df = pd.DataFrame(all_results)
        df.insert(0, "S.No", range(1, len(df)+1))
        st.success("Filtered results ready!")

        # Download Excel
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
st.title("Mont Blanc Refuge Availability")

# Display logo at the top
st.image("BTA_LOGO_square.webp", width=150)

# Three columns with logos
col1, col2, col3 = st.columns(3)
with col1:
    st.image("logo_french.webp", width=80)
    selected_french = st.multiselect("French Refuges", sorted(region_french), key="french", height=200)
with col2:
    st.image("logo_italian.webp", width=80)
    selected_italian = st.multiselect("Italian Refuges", sorted(region_italian), key="italian", height=200)
with col3:
    st.image("logo_swiss.webp", width=80)
    selected_swiss = st.multiselect("Swiss Refuges", sorted(region_swiss), key="swiss", height=200)

selected_refuges = selected_french + selected_italian + selected_swiss

# Date input and generation
start_date_str = st.text_input("Enter Main Start Date (dd/mm/yyyy):", "")
selected_dates = []
if start_date_str:
    date_options = generate_date_range(start_date_str)
    selected_dates = st.multiselect(
        "Select Dates to Check:",
        options=date_options,
        default=date_options
    )

# Run scraper button
if st.button("Run Scraper"):
    if not selected_refuges:
        st.warning("Please select at least one refuge.")
    elif not selected_dates:
        st.warning("Please select at least one date.")
    else:
        run_scraper(selected_refuges, selected_dates)
