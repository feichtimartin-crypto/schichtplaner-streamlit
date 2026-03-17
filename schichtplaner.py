import streamlit as st
import json
import random
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter

# ============================================================
# 🔸 Grundeinstellungen
# ============================================================

DATA_FILE = Path("data/historie.json")
DATA_FILE.parent.mkdir(exist_ok=True)
ADMIN_PASSWORD = "Nikolajistcoll"

# ✅ NEU: Arbeiten inkl. Wareneingang
DEFAULT_ARBEITEN = [
    "Teamlead",
    "S3",
    "Bahnhof",
    "Bahnhof Stapler",
    "Bahnhof Tugger",
    "Wareneingang",
    "Frunks",
    "Door´s Stapler",
    "Door´s Tugger"
]

# ✅ NEU: Min
DEFAULT_MIN = {
    "Teamlead": 1,
    "S3": 1,
    "Bahnhof": 2,
    "Bahnhof Stapler": 3,
    "Bahnhof Tugger": 5,
    "Wareneingang": 3,
    "Frunks": 1,
    "Door´s Stapler": 1,
    "Door´s Tugger": 1
}

# ✅ NEU: Max
DEFAULT_MAX = {
    "Teamlead": 2,
    "S3": 2,
    "Bahnhof": 999,
    "Bahnhof Stapler": 3,
    "Bahnhof Tugger": 5,
    "Wareneingang": 4,
    "Frunks": 1,
    "Door´s Stapler": 1,
    "Door´s Tugger": 1
}

# ============================================================
# 🔹 Datenverwaltung
# ============================================================

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "mitarbeiter": [],
        "arbeiten": [],
        "eintraege": [],
        "feste_positionen": {},
        "mindest_besetzung": {},
        "max_besetzung": {}
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ✅ Defaults nur setzen, wenn leer / nicht vorhanden
if not data["arbeiten"]:
    data["arbeiten"] = DEFAULT_ARBEITEN.copy()

if "feste_positionen" not in data:
    data["feste_positionen"] = {}
if "mindest_besetzung" not in data:
    data["mindest_besetzung"] = {}
if "max_besetzung" not in data:
    data["max_besetzung"] = {}

for a, v in DEFAULT_MIN.items():
    if a not in data["mindest_besetzung"]:
        data["mindest_besetzung"][a] = v

for a, v in DEFAULT_MAX.items():
    if a not in data["max_besetzung"]:
        data["max_besetzung"][a] = v

save_data(data)

# ============================================================
# ⚙️ Hilfsfunktionen
# ============================================================

def add_mitarbeiter(name):
    if name and name not in data["mitarbeiter"]:
        data["mitarbeiter"].append(name)
        save_data(data)

def remove_mitarbeiter(name):
    if name in data["mitarbeiter"]:
        data["mitarbeiter"].remove(name)
        data["feste_positionen"].pop(name, None)
        save_data(data)

def add_arbeit(arbeit):
    if arbeit and arbeit not in data["arbeiten"]:
        data["arbeiten"].append(arbeit)
        save_data(data)

def remove_arbeit(arbeit):
    if arbeit in data["arbeiten"]:
        data["arbeiten"].remove(arbeit)
        data["mindest_besetzung"].pop(arbeit, None)
        data["max_besetzung"].pop(arbeit, None)
        save_data(data)

# ============================================================
# 🧠 Plan-Logik
# ============================================================

def generiere_plan(zeitraum_label):
    mitarbeiter = data["mitarbeiter"]
    arbeiten = data["arbeiten"]

    abwesende = st.session_state.get("abwesend", set())
    verfuegbar = [m for m in mitarbeiter if m not in abwesende]

    if not verfuegbar or not arbeiten:
        st.warning("Bitte zuerst Mitarbeiter und Arbeiten hinzufügen!")
        return None

    plan = []

    # feste Positionen
    for person, arbeit in data.get("feste_positionen", {}).items():
        if person in verfuegbar and arbeit in arbeiten:
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    count = defaultdict(lambda: defaultdict(int))
    for e in data["eintraege"]:
        for arbeit, person in e["plan"]:
            count[person][arbeit] += 1

    for arbeit in arbeiten:
        aktuelle = [p for a, p in plan if a == arbeit]

        min_soll = data["mindest_besetzung"].get(arbeit, 1)
        max_soll = data["max_besetzung"].get(arbeit, min_soll)

        # Mindest erfüllen
        for _ in range(max(0, min_soll - len(aktuelle))):
            if not verfuegbar:
                break
            kandidaten = sorted(verfuegbar, key=lambda p: count[p][arbeit])
            person = random.choice(kandidaten)
            plan.append((arbeit, person))
            verfuegbar.remove(person)

        # Max auffüllen
        while len([p for a, p in plan if a == arbeit]) < max_soll and verfuegbar:
            kandidaten = sorted(verfuegbar, key=lambda p: count[p][arbeit])
            person = random.choice(kandidaten)
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    return {
        "type": zeitraum_label,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "plan": plan
    }

def plan_speichern(plan):
    data["eintraege"].append(plan)
    save_data(data)

def get_recent_entries(weeks=8):
    cutoff = datetime.now() - timedelta(weeks=weeks)
    result = []
    for e in data["eintraege"]:
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d")
            if d >= cutoff:
                result.append(e)
        except:
            pass
    return result

def statistik_wochen(weeks=8):
    zeitraum = get_recent_entries(weeks)
    statistik = defaultdict(lambda: Counter())
    for eintrag in zeitraum:
        for arbeit, person in eintrag["plan"]:
            statistik[person][arbeit] += 1
    return statistik

# ============================================================
# 🧭 DEINE ORIGINALE UI (UNVERÄNDERT)
# ============================================================

st.set_page_config(page_title="Schichtplaner", page_icon="🗓", layout="centered")
st.title("🗓 Schichtplan-Manager")

tab1, tab2, tab3 = st.tabs(["📋 Planung", "🔒 Verwaltung", "📊 Statistik (8 Wochen)"])

with tab1:
    st.header("🗓 Planung")

    if "abwesend" not in st.session_state:
        st.session_state["abwesend"] = set()

    if not data["mitarbeiter"]:
        st.info("Noch keine Mitarbeitenden angelegt.")
    else:
        for name in data["mitarbeiter"]:
            if st.checkbox(name):
                st.session_state["abwesend"].add(name)

    if st.button("Plan erstellen"):
        plan = generiere_plan("Woche")
        if plan:
            df = pd.DataFrame(plan["plan"], columns=["Arbeit", "Mitarbeiter"])
            st.dataframe(df)

with tab2:
    st.header("🔒 Verwaltung")
    password = st.text_input("Passwort:", type="password")
    if password != ADMIN_PASSWORD:
        st.stop()

    new = st.text_input("Mitarbeiter hinzufügen")
    if st.button("Hinzufügen"):
        add_mitarbeiter(new)
        st.rerun()

with tab3:
    st.header("📊 Statistik")
    stats = statistik_wochen()
    for person, daten in stats.items():
        st.write(person, dict(daten))
