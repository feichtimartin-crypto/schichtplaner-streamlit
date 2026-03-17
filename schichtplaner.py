import streamlit as st
import json
import random
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter


# ============================================================
# 🔸 Einstellungen & Datenpfade
# ============================================================

DATA_FILE = Path("data/historie.json")
DATA_FILE.parent.mkdir(exist_ok=True)
ADMIN_PASSWORD = "Nikolajistcoll"  # Passwort für Verwaltung


# ============================================================
# 🔹 Datenverwaltung
# ============================================================

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "mitarbeiter": [],
        "arbeiten": [],
        "eintraege": [],
        "feste_positionen": {},   # Neu: {"Anna": "Kasse"}
        "mindest_besetzung": {}   # Neu: {"Lager": 2}
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()


# ============================================================
# ⚙️ Basis‑Funktionen
# ============================================================

def add_mitarbeiter(name):
    if name and name not in data["mitarbeiter"]:
        data["mitarbeiter"].append(name)
        save_data(data)

def remove_mitarbeiter(name):
    if name in data["mitarbeiter"]:
        data["mitarbeiter"].remove(name)
        # Auch aus festen Positionen entfernen
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
        save_data(data)


# ============================================================
# 🧠 Plan‑Logik
# ============================================================

def generiere_plan():
    mitarbeiter = data["mitarbeiter"]
    arbeiten = data["arbeiten"]

    if not mitarbeiter or not arbeiten:
        st.warning("Bitte zuerst Mitarbeiter und Arbeiten hinzufügen!")
        return None

    plan = []
    verfuegbar = mitarbeiter.copy()

    # --- 1️⃣ Feste Positionen zuerst setzen
    for person, arbeit in data.get("feste_positionen", {}).items():
        if person in verfuegbar and arbeit in arbeiten:
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    # --- 2️⃣ Zähldaten aus Historie
    count = defaultdict(lambda: defaultdict(int))
    for eintrag in data["eintraege"]:
        for arbeit, person in eintrag["plan"]:
            count[person][arbeit] += 1

    # --- 3️⃣ Plan generieren für restliche Arbeiten
    for arbeit in arbeiten:
        # Wenn Arbeit schon besetzt (durch feste Position oder mehrfachbedarf), prüfen:
        aktuelle_personen = [p for (a, p) in plan if a == arbeit]
        soll = data.get("mindest_besetzung", {}).get(arbeit, 1)
        benoetigt = max(0, soll - len(aktuelle_personen))

        for _ in range(benoetigt):
            if not verfuegbar:
                verfuegbar = mitarbeiter.copy()
                for _, p in plan:
                    if p in verfuegbar:
                        verfuegbar.remove(p)
            # Kandidaten sortiert nach Häufigkeit
            kandidaten = sorted(
                verfuegbar, key=lambda p: count[p][arbeit]
            )
            if not kandidaten:
                continue
            min_count = count[kandidaten[0]][arbeit]
            beste = [k for k in kandidaten if count[k][arbeit] == min_count]
            person = random.choice(beste)
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    return plan

def plan_speichern(plan):
    data["eintraege"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "plan": plan
    })
    save_data(data)

def get_recent_entries(weeks=8):
    cutoff = datetime.now() - timedelta(weeks=weeks)
    return [
        e for e in data["eintraege"]
        if datetime.strptime(e["date"], "%Y-%m-%d") >= cutoff
    ]

def statistik_wochen(weeks=8):
    zeitraum = get_recent_entries(weeks)
    statistik = defaultdict(lambda: Counter())
    for eintrag in zeitraum:
        for arbeit, person in eintrag["plan"]:
            statistik[person][arbeit] += 1
    return statistik


# ============================================================
# 🎨 Streamlit‑App
# ============================================================

st.set_page_config(page_title="Schichtplaner", page_icon="🗓", layout="centered")
st.title("🗓 Schichtplan‑Manager")

tab1, tab2, tab3 = st.tabs(["📋 Plan", "🔒 Verwaltung", "📊 Statistik (8 Wochen)"])


# ============================================================
# 1️⃣ TAB – PLAN
# ============================================================

with tab1:
    st.header("📋 Schichtplan erstellen")

    if st.button("🔄 Neuen Plan generieren"):
        plan = generiere_plan()
        if plan:
            st.session_state["plan"] = plan
            st.success("✅ Plan erstellt!")

    plan = st.session_state.get("plan", None)
    if plan:
        st.subheader(f"Aktueller Plan ({datetime.now().strftime('%d.%m.%Y')})")
        df_plan = pd.DataFrame(plan, columns=["Arbeit", "Mitarbeiter"])
        df_plan = df_plan.sort_values("Arbeit")
        st.dataframe(df_plan, use_container_width=True, hide_index=True)

        if st.button("💾 Plan speichern"):
            plan_speichern(plan)
            st.success("Gespeichert ✅")
    else:
        st.info("Noch kein Plan vorhanden.")


# ============================================================
# 2️⃣ TAB – VERWALTUNG (Passwortgeschützt)
# ============================================================

with tab2:
    st.header("🔒 Verwaltung")

    password = st.text_input("Bitte Passwort eingeben:", type="password")
    if password != ADMIN_PASSWORD:
        st.warning("Zugriff verweigert – bitte gültiges Passwort eingeben.")
        st.stop()

    st.success("Zugriff gewährt ✅")

    col1, col2 = st.columns(2)

    # --- Mitarbeiter ---
    with col1:
        st.subheader("👤 Mitarbeiter")
        name = st.text_input("Neuen Mitarbeiter hinzufügen:")
        if st.button("➕ Hinzufügen"):
            add_mitarbeiter(name)
            st.rerun()

        if data["mitarbeiter"]:
            selected = st.selectbox("Mitarbeiter löschen:", ["–"] + data["mitarbeiter"])
            if selected != "–" and st.button("❌ Entfernen"):
                remove_mitarbeiter(selected)
                st.rerun()
        st.info("Aktuell: " + ", ".join(data["mitarbeiter"]) if data["mitarbeiter"] else "Keine Mitarbeiter")

    # --- Arbeiten ---
    with col2:
        st.subheader("🧰 Arbeiten")
        arbeit = st.text_input("Neue Arbeit:")
        if st.button("➕ Arbeit hinzufügen"):
            add_arbeit(arbeit)
            st.rerun()

        if data["arbeiten"]:
            selected_work = st.selectbox("Arbeit löschen:", ["–"] + data["arbeiten"])
            if selected_work != "–" and st.button("❌ Arbeit löschen"):
                remove_arbeit(selected_work)
                st.rerun()
        st.info("Aktuell: " + ", ".join(data["arbeiten"]) if data["arbeiten"] else "Keine Arbeiten")

    st.markdown("---")

    # --- Feste Positionen (NEU) ---
    st.subheader("📌 Feste Zuweisungen")
    if data["mitarbeiter"] and data["arbeiten"]:
        person_fix = st.selectbox("Mitarbeiter wählen", ["–"] + data["mitarbeiter"])
        arbeit_fix = st.selectbox("Feste Arbeit für diesen Mitarbeiter", ["–"] + data["arbeiten"])
        if person_fix != "–" and arbeit_fix != "–" and st.button("📍 Fixierung setzen"):
            data["feste_positionen"][person_fix] = arbeit_fix
            save_data(data)
            st.success(f"{person_fix} ist jetzt dauerhaft an '{arbeit_fix}' eingeteilt.")
            st.rerun()

    if data["feste_positionen"]:
        st.write("**Aktuelle Fixierungen:**")
        df_fest = pd.DataFrame(list(data["feste_positionen"].items()), columns=["Mitarbeiter", "Fixierte Arbeit"])
        st.dataframe(df_fest, use_container_width=True, hide_index=True)

        if st.button("🔓 Alle Fixierungen löschen"):
            data["feste_positionen"].clear()
            save_data(data)
            st.rerun()
    else:
        st.info("Noch keine Fixierungen gesetzt.")

    st.markdown("---")

    # --- Mindest‑Besetzung (NEU) ---
    st.subheader("👥 Mindest‑Besetzung pro Arbeit")
    if data["arbeiten"]:
        arbeit_min = st.selectbox("Arbeit wählen zur Mindest‑Besetzung", ["–"] + data["arbeiten"])
        anzahl_min = st.number_input("Benötigte Anzahl", min_value=1, max_value=10, step=1)
        if arbeit_min != "–" and st.button("💾 Mindestwert speichern"):
            data["mindest_besetzung"][arbeit_min] = anzahl_min
            save_data(data)
            st.success(f"Mindest‑Besetzung für '{arbeit_min}' auf {anzahl_min} gesetzt.")
            st.rerun()

    if data["mindest_besetzung"]:
        st.write("**Aktuelle Mindest‑Besetzungen:**")
        df_min = pd.DataFrame(
            list(data["mindest_besetzung"].items()), columns=["Arbeit", "Mindestens"]
        )
        st.dataframe(df_min, use_container_width=True, hide_index=True)

        if st.button("🗑️ Alle Besetzungsregeln löschen"):
            data["mindest_besetzung"].clear()
            save_data(data)
            st.rerun()
    else:
        st.info("Keine Mindest‑Besetzungen definiert.")


# ============================================================
# 3️⃣ TAB – STATISTIK
# ============================================================

with tab3:
    st.header("📊 Statistik (8 Wochen)")
    statistik = statistik_wochen(8)
    if not statistik:
        st.info("Noch keine Schichtdaten vorhanden.")
    else:
        for person, daten in statistik.items():
            st.subheader(f"👤 {person}")
            df_stat = pd.DataFrame(list(daten.items()), columns=["Arbeit", "Anzahl"])
            df_stat = df_stat.sort_values(by="Anzahl", ascending=False)
            st.bar_chart(df_stat.set_index("Arbeit"))
            st.dataframe(df_stat, use_container_width=True, hide_index=True)
    st.markdown("📅 Zeitraum: letzte 8 Wochen")
