import streamlit as st
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd

# ============================================================
#  🔸 Datenverwaltung
# ============================================================

DATA_FILE = Path("data/historie.json")
DATA_FILE.parent.mkdir(exist_ok=True)

def load_data():
    """Lade lokale JSON-Datei oder erzeuge Grundstruktur"""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "mitarbeiter": [],
        "arbeiten": [],
        "eintraege": []  # Liste von {"date": "YYYY-MM-DD", "plan": [(arbeit, person), ...]}
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()


# ============================================================
#  🔹 Hilfsfunktionen
# ============================================================

def add_mitarbeiter(name):
    if name and name not in data["mitarbeiter"]:
        data["mitarbeiter"].append(name)
        save_data(data)

def add_arbeit(arbeit):
    if arbeit and arbeit not in data["arbeiten"]:
        data["arbeiten"].append(arbeit)
        save_data(data)

def generiere_plan():
    mitarbeiter = data["mitarbeiter"]
    arbeiten = data["arbeiten"]
    if not mitarbeiter or not arbeiten:
        st.warning("Bitte zuerst Mitarbeiter und Arbeiten hinzufügen!")
        return None

    # Häufigkeiten aus der Historie berechnen (für faire Zuordnung)
    count = defaultdict(lambda: defaultdict(int))
    for eintrag in data["eintraege"]:
        for arbeit, person in eintrag["plan"]:
            count[person][arbeit] += 1

    verfuegbar = mitarbeiter.copy()
    random.shuffle(verfuegbar)
    plan = []

    for arbeit in arbeiten:
        if not verfuegbar:
            verfuegbar = mitarbeiter.copy()

        kandidaten = sorted(verfuegbar, key=lambda p: count[p][arbeit])
        min_count = count[kandidaten[0]][arbeit]
        beste = [k for k in kandidaten if count[k][arbeit] == min_count]
        person = random.choice(beste)
        plan.append((arbeit, person))
        verfuegbar.remove(person)

    return plan

def plan_speichern(plan):
    if not plan:
        return
    data["eintraege"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "plan": plan
    })
    save_data(data)

def get_recent_entries(weeks=4):
    """Liefert nur Einträge der letzten n Wochen"""
    cutoff = datetime.now() - timedelta(weeks=weeks)
    ergebnis = []
    for eintrag in data["eintraege"]:
        try:
            d = datetime.strptime(eintrag["date"], "%Y-%m-%d")
            if d >= cutoff:
                ergebnis.append(eintrag)
        except ValueError:
            continue
    return ergebnis

def berechne_4wochen_statistik():
    """Zählt alle Einsätze der letzten 4 Wochen pro Person & Tätigkeit"""
    zeitraum = get_recent_entries(weeks=4)
    statistik = defaultdict(lambda: Counter())
    for eintrag in zeitraum:
        for arbeit, person in eintrag["plan"]:
            statistik[person][arbeit] += 1
    return statistik


# ============================================================
#  🎨 Streamlit UI
# ============================================================

st.set_page_config(page_title="Schichtplaner", page_icon="🗓", layout="centered")
st.title("🗓 Schichtplan-Manager")

tab1, tab2, tab3 = st.tabs(["📋 Schichtplan", "👥 Verwaltung", "📈 Statistik (4 Wochen)"])


# ============================================================
#  🧩 TAB 1 – Planerstellung
# ============================================================

with tab1:
    st.header("📋 Plan erstellen")

    if st.button("🔄 Neuen Plan generieren"):
        plan = generiere_plan()
        if plan:
            st.session_state["plan"] = plan
            st.success("Plan erstellt!")

    plan = st.session_state.get("plan", None)
    if plan:
        st.subheader(f"Aktueller Plan ({datetime.now().strftime('%d.%m.%Y')})")
        for arbeit, person in plan:
            st.write(f"**{arbeit}** → {person}")

        if st.button("💾 Plan speichern"):
            plan_speichern(plan)
            st.success("Plan gespeichert ✅")


# ============================================================
#  👥 TAB 2 – Verwaltung
# ============================================================

with tab2:
    st.header("👥 Mitarbeiter & Arbeiten")
    col1, col2 = st.columns(2)

    # --- Mitarbeiter hinzufügen ---
    with col1:
        name = st.text_input("Mitarbeiter hinzufügen")
        if st.button("➕ Mitarbeiter hinzufügen"):
            add_mitarbeiter(name)
            st.rerun()  # <— fix für neuen Streamlit-Standard
        st.markdown("### 👩‍💼 Aktuell:")
        st.write(", ".join(data["mitarbeiter"]) if data["mitarbeiter"] else "_Keine_")

    # --- Arbeiten hinzufügen ---
    with col2:
        arbeit = st.text_input("Arbeit/Schicht hinzufügen")
        if st.button("➕ Arbeit hinzufügen"):
            add_arbeit(arbeit)
            st.rerun()
        st.markdown("### 🧰 Aktuell:")
        st.write(", ".join(data["arbeiten"]) if data["arbeiten"] else "_Keine_")


# ============================================================
#  📈 TAB 3 – 4-Wochen-Historie
# ============================================================

with tab3:
    st.header("📈 Statistik der letzten 4 Wochen")

    statistik = berechne_4wochen_statistik()
    if not statistik:
        st.info("Noch keine Einträge in den letzten 4 Wochen.")
    else:
        for person, daten in statistik.items():
            df = pd.DataFrame(list(daten.items()), columns=["Arbeit", "Anzahl"])
            st.subheader(f"👤 {person}")
            st.dataframe(df, use_container_width=True)

    st.markdown("📅 Betrachteter Zeitraum: letzte 4 Wochen")
