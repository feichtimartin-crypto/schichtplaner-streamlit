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

PRIORITAET = ["Teamlead", "S3"]

# ============================================================
# 🔹 Datenverwaltung
# ============================================================

def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
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

# Sicherheits-Upgrade
for key in ["feste_positionen", "mindest_besetzung", "max_besetzung"]:
    if key not in data:
        data[key] = {}

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
# 📊 Neue Tabellenansicht
# ============================================================

def plan_als_tabelle(plan):
    arbeit_dict = {}

    for arbeit, person in plan["plan"]:
        arbeit_dict.setdefault(arbeit, []).append(person)

    if not arbeit_dict:
        return pd.DataFrame()

    sortierte_arbeiten = sorted(
        arbeit_dict.keys(),
        key=lambda x: (PRIORITAET.index(x) if x in PRIORITAET else 999, x)
    )

    max_len = max(len(v) for v in arbeit_dict.values())

    for arbeit in arbeit_dict:
        arbeit_dict[arbeit] += [""] * (max_len - len(arbeit_dict[arbeit]))

    return pd.DataFrame({a: arbeit_dict[a] for a in sortierte_arbeiten})

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

    # Historie
    count = defaultdict(lambda: defaultdict(int))
    for e in data["eintraege"]:
        for arbeit, person in e["plan"]:
            count[person][arbeit] += 1

    # Verteilung
    for arbeit in arbeiten:
        aktuelle = [p for a, p in plan if a == arbeit]

        min_soll = data.get("mindest_besetzung", {}).get(arbeit, 1)
        max_soll = data.get("max_besetzung", {}).get(arbeit, min_soll)

        # Mindestbesetzung
        benoetigt = max(0, min_soll - len(aktuelle))

        for _ in range(benoetigt):
            if not verfuegbar:
                break
            kandidaten = sorted(verfuegbar, key=lambda p: count[p][arbeit])
            min_count = count[kandidaten[0]][arbeit]
            beste = [k for k in kandidaten if count[k][arbeit] == min_count]
            person = random.choice(beste)
            plan.append((arbeit, person))
            verfuegbar.remove(person)

        # Bis max auffüllen
        aktuelle = [p for a, p in plan if a == arbeit]
        extra_slots = max(0, max_soll - len(aktuelle))

        for _ in range(extra_slots):
            if not verfuegbar:
                break
            person = random.choice(verfuegbar)
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
# 🧭 UI
# ============================================================

st.set_page_config(page_title="Schichtplaner", page_icon="🗓", layout="centered")
st.title("🗓 Schichtplan-Manager")

tab1, tab2, tab3 = st.tabs(["📋 Planung", "🔒 Verwaltung", "📊 Statistik (8 Wochen)"])

# ============================================================
# PLANUNG
# ============================================================

with tab1:
    st.header("🗓 Planung")

    if "abwesend" not in st.session_state:
        st.session_state["abwesend"] = set()

    tmp = set()
    for name in data["mitarbeiter"]:
        if st.checkbox(name, value=name in st.session_state["abwesend"]):
            tmp.add(name)

    st.session_state["abwesend"] = tmp

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📅 Plan Mo/Di erstellen"):
            plan = generiere_plan("MoDi")
            if plan:
                st.session_state["plan_modi"] = plan

    with col2:
        if st.button("📅 Plan Mi–Fr erstellen"):
            plan = generiere_plan("MiFr")
            if plan:
                st.session_state["plan_mifr"] = plan

    for key, label in [("plan_modi", "Mo/Di"), ("plan_mifr", "Mi–Fr")]:
        plan = st.session_state.get(key)
        if plan:
            st.subheader(f"📋 Plan {label}")
            df = plan_als_tabelle(plan)
            st.dataframe(df, use_container_width=True, hide_index=True)

            if st.button(f"💾 {label} speichern", key=f"save_{key}"):
                plan_speichern(plan)
                st.success("Gespeichert")

# ============================================================
# VERWALTUNG
# ============================================================

with tab2:
    password = st.text_input("Passwort:", type="password")
    if password != ADMIN_PASSWORD:
        st.stop()

    st.subheader("👤 Mitarbeitende")
    new = st.text_input("Name")
    if st.button("Hinzufügen"):
        add_mitarbeiter(new)

    st.write(data["mitarbeiter"])

    st.subheader("🧰 Arbeiten")
    newa = st.text_input("Arbeit")
    if st.button("Add Arbeit"):
        add_arbeit(newa)

    st.write(data["arbeiten"])

    st.subheader("👥 Mindest")
    job = st.selectbox("Job", ["–"] + data["arbeiten"])
    val = st.number_input("Min", 1, 10)

    if st.button("Min speichern"):
        data["mindest_besetzung"][job] = val
        save_data(data)

    st.subheader("📊 Max")
    job2 = st.selectbox("Job max", ["–"] + data["arbeiten"])
    val2 = st.number_input("Max", 1, 20)

    if st.button("Max speichern"):
        data["max_besetzung"][job2] = val2
        save_data(data)

# ============================================================
# STATISTIK
# ============================================================

with tab3:
    stats = statistik_wochen()

    for person, daten in stats.items():
        st.subheader(person)
        df = pd.DataFrame(list(daten.items()), columns=["Arbeit", "Anzahl"])
        st.bar_chart(df.set_index("Arbeit"))