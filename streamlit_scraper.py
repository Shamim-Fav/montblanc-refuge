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

# Keep REFUGE_IDS as is
REFUGE_IDS = "32383,32365,123462,127958,32357,32358,32356,32369,32372,39948,32361,39796,39797,32362,116702,32379,32378,36470,67403,32789,32368,116701,32367,32366,32405,39703,32406,32404,32398,32395,114712,32394,46179,32399,32397,32396,32403,32400,32401,32393,32391,32385,32390,32388,32389,32386,36471,32377,133634"

# Refuge list with region
refuge_list = [
    (156, "Auberge la Grande Ourse", "Swiss"),
    (162, "Gîte le Pontet", "French"),
    (164, "Chalet Les Méandres (ex Tupilak)", "French"),
    (191, "Hotel du Col de Fenêtre", "Swiss"),
    (22, "Gîte Mermoud", "French"),
    (23, "Refuge de Nant Borrant", "French"),
    (25, "Relais d'Arpette", "Swiss"),
    (26, "Rifugio G. Bertone", "Italian"),
    (28, "Refuge du Fioux", "French"),
    (283, "Maya-Joie", "Swiss"),
    (31, "Rifugio Monte Bianco - Cai Uget", "Italian"),
    (322, "Gîte La Léchère", "Swiss"),
    (329, "Refuge Le Peuty", "Swiss"),
    (36, "Hôtel Lavachey", "Italian"),
    (37, "Hôtel Funivia", "Italian"),
    (39, "Rifugio Maison Vieille", "Italian"),
    (406, "Gîte de la Fouly", "Swiss"),
    (41, "Gite le Randonneur du Mont Blanc", "Italian"),
    (413, "Les Chambres du Soleil", "French"),
    (416, "Refuge des Prés", "French"),
    (428, "Gîte Les Mélèzes", "French"),
    (445, "La Ferme à Piron", "French"),
    (47, "Refuge des Mottets", "French"),
    (476, "Rifugio Chapy Mont-Blanc", "Italian"),
    (49, "Refuge de la Balme", "French"),
    (50, "Auberge du Truc", "French"),
    (52, "Auberge Mont-Blanc", "Swiss"),
    (54, "Auberge la Boërne", "French"),
    (56, "Auberge Gîte Bon Abri", "Swiss"),
    (57, "Chalet 'Le Dolent'", "Swiss"),
    (58, "Gîte Alpage de La Peule", "Swiss"),
    (60, "Hôtel du Col de la Forclaz", "Swiss"),
    (62, "Hôtel Edelweiss", "Swiss"),
    (64, "Chalet Alpin du Tour", "French"),
    (67, "Gîte Le Moulin", "French"),
    (69, "Gîte Michel Fagot", "French"),
    (71, "Hôtel Chalet Val Ferret", "Italian"),
    (72, "Pension en Plein Air", "Swiss"),
    (76, "Auberge-Refuge de la Nova", "French"),
    (93, "Gîte d'Alpage Les Ecuries de Charamillon", "French"),
    (96, "Auberge des Glaciers", "Swiss"),
]

# Mapping names to IDs
name_to_id = {name: str(rid) for rid, name, _ in refuge_list}

# URLs & headers
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
    return [(center_date + timedelta(days=offset)).strftime("%d/%m/%Y") for offset in range(-5,6)]

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
            "Globales/ListeIdFournisseur": REFUGE_IDS,
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
                        refuge_info['query_date'] = date_input
                        all_results.append(refuge_info)

                success = True
                break
            except Exception as e:
                st.warning(f"Error on {date_input} attempt {attempt+1}: {e}")

        if not success:
            st.error(f"Failed to get data for {date_input} after 3 attempts.")

    # Filter by names
    filtered_results = [r for r in all_results if r["name"] in selected_names]

    if filtered_results:
        df = pd.DataFrame(filtered_results)
        df.insert(0, "S.No", range(1, len(df)+1))
        st.success("Filtered results ready!")

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Availability')
            writer.save()
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

# Display top logo
st.image("BTA_LOGO_square.webp", width=120)

# Columns for regions
col1, col2, col3 = st.columns(3)

with col1:
    st.image("logo_french.png", width=80)
    region_french = [str(name) for _, name, region in refuge_list if region=="French" and name]
    region_french = list(filter(None, region_french))
    selected_french = st.multiselect("French Refuges", sorted(region_french), key="french", height=200)

with col2:
    st.image("logo_italian.png", width=80)
    region_italian = [str(name) for _, name, region in refuge_list if region=="Italian" and name]
    region_italian = list(filter(None, region_italian))
    selected_italian = st.multiselect("Italian Refuges", sorted(region_italian), key="italian", height=200)

with col3:
    st.image("logo_swiss.png", width=80)
    region_swiss = [str(name) for _, name, region in refuge_list if region=="Swiss" and name]
    region_swiss = list(filter(None, region_swiss))
    selected_swiss = st.multiselect("Swiss Refuges", sorted(region_swiss), key="swiss", height=200)

# Date input
start_date_str = st.text_input("Enter Main Start Date (dd/mm/yyyy):", "")
selected_dates = []
if start_date_str:
    date_options = generate_date_range(start_date_str)
    selected_dates = st.multiselect("Select Dates to Check:", options=date_options, default=date_options)

# Combine selected refuges
selected_refuges = selected_french + selected_italian + selected_swiss

if st.button("Run Scraper"):
    if not selected_refuges:
        st.warning("Please select at least one refuge.")
    elif not selected_dates:
        st.warning("Please select at least one date.")
    else:
        run_scraper(selected_refuges, selected_dates)
