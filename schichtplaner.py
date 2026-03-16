import streamlit as st
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd


# ============================================================
#  🔸 KONSTANTEN & INITIALISIERUNG
# ============================================================

DATA_FILE = Path("data/historie.json")
DATA_FILE.parent.mkdir(exist_ok=True)
ADMIN_PASSWORD = "Nikolajistcoll"  # 🔐 Passwortschutz für Verwaltung


# ============================================================
#  🔹 DATENVERWALTUNG
# ============================================================

def load_data():
    """Lädt gespeicherte Daten oder erstellt neue Basisstruktur."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "mitarbeiter": [],
        "arbeiten": [],
        "eintraege": []  # {"date": "YYYY-MM-DD", "plan": [(arbeit, person), ...]}
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()


# ============================================================
#  ⚙️  FUNKTIONEN
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
    """Erstellt einen fairen Schichtplan auf Basis der bisherigen Historie."""
    mitarbeiter = data["mitarbeiter"]
    arbeiten = data["arbeiten"]
    if not mitarbeiter or not arbeiten:
        st.warning("Bitte zuerst Mitarbeiter und Arbeiten hinzufügen!")
        return None

    # Zähldaten (wer wie oft was gemacht hat)
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
    if plan:
        data["eintraege"].append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "plan": plan
        })
        save_data(data)

def get_recent_entries(weeks=8):
    """Liefert Einträge der letzten Wochen."""
    cutoff = datetime.now() - timedelta(weeks=weeks)
    ergebnis = []
    for eintrag in data["eintraege"]:
        try:
            d = datetime.strptime(eintrag["date"], "%Y-%m-%d")
            if d >= cutoff:
                ergebnis.append(eintrag)
        except Exception:
            continue
    return ergebnis

def statistik_wochen(weeks=8):
    """Zählt, wie oft jede Person welche Arbeit im Zeitraum gemacht hat."""
    zeitraum = get_recent_entries(weeks)
    statistik = defaultdict(lambda: Counter())
    for eintrag in zeitraum:
        for arbeit, person in eintrag["plan"]:
            statistik[person][arbeit] += 1
    return statistik


# ============================================================
#  🎨 STREAMLIT-Oberfläche
# ============================================================

st.set_page_config(page_title="Schichtplaner", page_icon="🗓", layout="centered")
st.title("🗓 Schichtplan-Manager")

tab1, tab2, tab3 = st.tabs(["📋 Schichtplan", "🔒 Verwaltung", "📊 Statistik (8 Wochen)"])


# ============================================================
# 1️⃣  TAB – SCHICHTPLAN
# ============================================================

with tab1:
    st.header("📅 Schichtplan erstellen")

    if st.button("🔄 Neuen Plan generieren"):
        plan = generiere_plan()
        if plan:
            st.session_state["plan"] = plan
            st.success("✅ Neuer Plan erfolgreich erstellt!")

    plan = st.session_state.get("plan", None)

    if plan:
        st.subheader(f"Aktueller Plan – {datetime.now().strftime('%d.%m.%Y')}")
        df_plan = pd.DataFrame(plan, columns=["Arbeit", "Mitarbeiter"])
        st.dataframe(df_plan, use_container_width=True, hide_index=True)

        st.markdown("---")
        if st.button("💾 Plan speichern"):
            plan_speichern(plan)
            st.success("📦 Plan gespeichert und in die Historie aufgenommen.")
    else:
        st.info("Noch kein Plan vorhanden. Erstelle zuerst einen neuen.")


# ============================================================
# 2️⃣  TAB – VERWALTUNG (PASSWORTGESCHÜTZT)
# ============================================================

with tab2:
    st.header("🔒 Verwaltung – Geschützter Bereich")

    password = st.text_input("Passwort eingeben:", type="password")
    if password != ADMIN_PASSWORD:
        st.warning("🚫 Zugriff verweigert – falsches Passwort oder kein Passwort eingegeben.")
        st.stop()

    st.success("✅ Zugriff gewährt – willkommen im Verwaltungsbereich!")
    col1, col2 = st.columns(2)

    # --- Mitarbeiter hinzufügen / löschen ---
    with col1:
        st.subheader("👤 Mitarbeiter verwalten")
        name = st.text_input("Neuen Mitarbeiter hinzufügen:")
        if st.button("➕ Mitarbeiter speichern"):
            add_mitarbeiter(name)
            st.rerun()

        if data["mitarbeiter"]:
            selected = st.selectbox("Mitarbeiter entfernen:", ["– auswählen –"] + data["mitarbeiter"])
            if selected != "– auswählen –" and st.button("❌ Mitarbeiter löschen"):
                remove_mitarbeiter(selected)
                st.rerun()
        else:
            st.info("Noch keine Mitarbeiter.")

        st.markdown("**Aktuell:** " + ", ".join(data["mitarbeiter"]) if data["mitarbeiter"] else "_leer_")

    # --- Arbeiten hinzufügen / löschen ---
    with col2:
        st.subheader("🧰 Arbeiten / Schichten verwalten")
        arbeit = st.text_input("Neue Arbeit hinzufügen:")
        if st.button("➕ Arbeit speichern"):
            add_arbeit(arbeit)
            st.rerun()

        if data["arbeiten"]:
            selected_arbeit = st.selectbox("Arbeit löschen:", ["– auswählen –"] + data["arbeiten"])
            if selected_arbeit != "– auswählen –" and st.button("❌ Arbeit löschen"):
                remove_arbeit(selected_arbeit)
                st.rerun()
        else:
            st.info("Noch keine Arbeiten.")

        st.markdown("**Aktuell:** " + ", ".join(data["arbeiten"]) if data["arbeiten"] else "_leer_")


# ============================================================
# 3️⃣  TAB – STATISTIK (8-WOCHEN)
# ============================================================

with tab3:
    st.header("📊 Schicht-Statistik – letzte 8 Wochen")

    statistik = statistik_wochen(8)
    if not statistik:
        st.info("ℹ️ Noch keine Pläne in den letzten 8 Wochen gespeichert.")
    else:
        for person, daten in statistik.items():
            st.subheader(f"👤 {person}")
            df_stat = pd.DataFrame(list(daten.items()), columns=["Arbeit", "Anzahl"])
            df_stat = df_stat.sort_values(by="Anzahl", ascending=False)
            st.bar_chart(df_stat.set_index("Arbeit"))
            st.dataframe(df_stat, use_container_width=True, hide_index=True)

    st.markdown("📅 Betrachteter Zeitraum: **8 Wochen**")
