import streamlit as st
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# ======== Constants ========
REFUGE_IDS = "32383,32365,123462,127958,32357,32358,32356,32369,32372,39948,32361,39796,39797,32362,116702,32379,32378,36470,67403,32789,32368,116701,32367,32366,32405,39703,32406,32404,32398,32395,114712,32394,46179,32399,32397,32396,32403,32400,32401,32393,32391,32385,32390,32388,32389,32386,36471,32377,133634"

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

id_to_name = {str(rid): name for rid, name in refuge_list}
name_to_id = {name: str(rid) for rid, name in refuge_list}

POST_URL = "https://reservation.montourdumontblanc.com/z7243_uk-.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www.montourdumontblanc.com",
    "Referer": "https://www.montourdumontblanc.com/",
}

# ======== Functions ========
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

def run_scraper(selected_ids, selected_dates):
    session = requests.Session()
    all_results = []

    for date_input in selected_dates:
        try:
            current_date = datetime.strptime(date_input, "%d/%m/%Y")
        except ValueError:
            st.error(f"Invalid date format: {date_input}")
            return

        day = current_date.strftime("%d")
        month = current_date.strftime("%m")
        year = current_date.strftime("%Y")

        st.text(f"Checking availability for {date_input}...")

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
                        if refuge_info["id"]:
                            refuge_info['query_date'] = date_input
                            all_results.append(refuge_info)
                success = True
                break
            except Exception as e:
                st.warning(f"Error on {date_input} attempt {attempt+1}: {e}")
                time.sleep(2)

        if not success:
            st.error(f"Failed to get data for {date_input} after 3 attempts.")

        time.sleep(1)

    filtered_results = [r for r in all_results if r["id"] in selected_ids]

    if filtered_results:
        df = pd.DataFrame(filtered_results)
        st.success("Filtered results ready!")

        # ✅ Correct way to make download button
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="filtered_availability_results.csv",
            mime="text/csv"
        )

    else:
        st.info("No results found for the selected refuges and dates.")

def generate_date_range(center_date_str):
    try:
        center_date = datetime.strptime(center_date_str, "%d/%m/%Y")
    except ValueError:
        st.error("Invalid start date format. Use dd/mm/yyyy.")
        return []

    date_list = []
    for offset in range(-5, 6):  # ±5 days
        dt = center_date + timedelta(days=offset)
        date_list.append(dt.strftime("%d/%m/%Y"))
    return date_list

# ======== Streamlit UI ========
st.title("Mont Blanc Refuge Availability Scraper")

selected_refuges = st.multiselect(
    "Select Refuge(s):",
    [name for _, name in refuge_list]
)

start_date = st.text_input("Enter Main Start Date (dd/mm/yyyy):")

if st.button("Generate Dates ±5 Days"):
    dates = generate_date_range(start_date)
    selected_dates = st.multiselect("Select Dates to Check:", dates, default=dates)
else:
    selected_dates = []

if st.button("Run Scraper"):
    if not selected_refuges:
        st.warning("Please select at least one refuge.")
    elif not selected_dates:
        st.warning("Please select at least one date.")
    else:
        selected_ids = [name_to_id[name] for name in selected_refuges]
        run_scraper(selected_ids, selected_dates)
