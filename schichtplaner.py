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
        "eintraege": []  # {"date": "...", "plan": [(arbeit, person), ...]}
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

def remove_mitarbeiter(name):
    if name in data["mitarbeiter"]:
        data["mitarbeiter"].remove(name)
        save_data(data)

def add_arbeit(arbeit):
    if arbeit and arbeit not in data["arbeiten"]:
        data["arbeiten"].append(arbeit)
        save_data(data)

def remove_arbeit(arbeit):
    if arbeit in data["arbeiten"]:
        data["arbeiten"].remove(arbeit)
        save_data(data)

def generiere_plan():
    """Erstellt einen fairen Schichtplan aus aktueller Historie"""
    mitarbeiter = data["mitarbeiter"]
    arbeiten = data["arbeiten"]
    if not mitarbeiter or not arbeiten:
        st.warning("Bitte zuerst Mitarbeiter und Arbeiten hinzufügen!")
        return None

    # Zähldaten aus Historie
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

def get_recent_entries(weeks=8):
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

def berechne_statistik_zeitraum(weeks=8):
    """Zählt Einsätze im angegebenen Zeitraum"""
    zeitraum = get_recent_entries(weeks=weeks)
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

tab1, tab2, tab3 = st.tabs(["📋 Schichtplan", "👥 Verwaltung", "📊 Statistik (8 Wochen)"])

# ============================================================
#  📋 TAB 1 – Planerstellung (übersichtlicher)
# ============================================================

with tab1:
    st.header("📋 Schichtplan-Erstellung")

    if st.button("🔄 Neuen Plan generieren"):
        plan = generiere_plan()
        if plan:
            st.session_state["plan"] = plan
            st.success("✅ Plan wurde erstellt!")

    plan = st.session_state.get("plan", None)
    if plan:
        st.subheader(f"📅 Aktueller Plan ({datetime.now().strftime('%d.%m.%Y')})")

        # Darstellung als Tabelle
        df_plan = pd.DataFrame(plan, columns=["Arbeit", "Mitarbeiter"])
        st.dataframe(df_plan, use_container_width=True, hide_index=True)

        st.markdown("---")
        if st.button("💾 Plan speichern"):
            plan_speichern(plan)
            st.success("📦 Plan gespeichert und in Historie übernommen!")    
    else:
        st.info("Noch kein Plan erstellt. Klicke oben auf „Neuen Plan generieren“.")


# ============================================================
#  👥 TAB 2 – Verwaltung
# ============================================================

with tab2:
    st.header("👥 Mitarbeiter & Arbeiten verwalten")
    col1, col2 = st.columns(2)

    # --- Mitarbeiter hinzufügen/entfernen ---
    with col1:
        st.subheader("👤 Mitarbeiter")
        name = st.text_input("Neuer Mitarbeiter:")
        if st.button("➕ Hinzufügen", key="add_person"):
            add_mitarbeiter(name)
            st.rerun()

        if data["mitarbeiter"]:
            selected = st.selectbox("Mitarbeiter löschen:", ["– auswählen –"] + data["mitarbeiter"])
            if selected != "– auswählen –" and st.button("❌ Entfernen", key="remove_person"):
                remove_mitarbeiter(selected)
                st.success(f"{selected} entfernt")
                st.rerun()
        else:
            st.info("Noch keine Mitarbeiter.")

        st.markdown("**Aktuell:** " + ", ".join(data["mitarbeiter"]) if data["mitarbeiter"] else "_leer_")

    # --- Arbeiten hinzufügen/entfernen ---
    with col2:
        st.subheader("🧰 Arbeiten / Schichten")
        arbeit = st.text_input("Neue Arbeit / Schicht:")
        if st.button("➕ Hinzufügen", key="add_work"):
            add_arbeit(arbeit)
            st.rerun()

        if data["arbeiten"]:
            selected_work = st.selectbox("Arbeit entfernen:", ["– auswählen –"] + data["arbeiten"])
            if selected_work != "– auswählen –" and st.button("❌ Entfernen", key="remove_work"):
                remove_arbeit(selected_work)
                st.success(f"{selected_work} entfernt")
                st.rerun()
        else:
            st.info("Noch keine Arbeiten.")

        st.markdown("**Aktuell:** " + ", ".join(data["arbeiten"]) if data["arbeiten"] else "_leer_")


# ============================================================
#  📈 TAB 3 – 8-Wochen-Historie
# ============================================================

with tab3:
    st.header("📊 Statistik der letzten 8 Wochen")

    statistik = berechne_statistik_zeitraum(weeks=8)
    if not statistik:
        st.info("Noch keine gespeicherten Pläne in den letzten 8 Wochen.")
    else:
        for person, daten in statistik.items():
            st.markdown(f"### 👤 {person}")
            df = pd.DataFrame(list(daten.items()), columns=["Arbeit", "Häufigkeit"])
            df = df.sort_values(by="Häufigkeit", ascending=False)
            st.bar_chart(df.set_index("Arbeit"))
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("📅 Zeitraum: letzte **8 Wochen** werden berücksichtigt.")
