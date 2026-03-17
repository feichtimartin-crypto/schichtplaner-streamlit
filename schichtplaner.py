import streamlit as st
import json
import random
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter


# ============================================================
# 🔸 Einstellungen
# ============================================================

DATA_FILE = Path("data/historie.json")
DATA_FILE.parent.mkdir(exist_ok=True)
ADMIN_PASSWORD = "Nikolajistcoll"  # 🔐 Passwort für Verwaltung


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
        "mindest_besetzung": {}
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ✨ Sicherheits-Upgrade für alte Dateien
if "feste_positionen" not in data:
    data["feste_positionen"] = {}
if "mindest_besetzung" not in data:
    data["mindest_besetzung"] = {}
save_data(data)


# ============================================================
# ⚙️ Funktionen
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
        save_data(data)

# ============================================================
# 🧠 Plan-Logik
# ============================================================

def generiere_plan():
    mitarbeiter = data["mitarbeiter"]
    arbeiten = data["arbeiten"]

    if not mitarbeiter or not arbeiten:
        st.warning("Bitte zuerst Mitarbeiter und Arbeiten hinzufügen!")
        return None

    # Abwesenheiten aus Session-State berücksichtigen
    abwesende = st.session_state.get("abwesend", set())
    verfuegbar = [m for m in mitarbeiter if m not in abwesende]

    plan = []

    # --- 1️⃣ Feste Positionen zuerst setzen
    for person, arbeit in data.get("feste_positionen", {}).items():
        if person in verfuegbar and arbeit in arbeiten:
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    # --- 2️⃣ Zähldaten aus Historie (faire Verteilung)
    count = defaultdict(lambda: defaultdict(int))
    for eintrag in data["eintraege"]:
        for arbeit, person in eintrag["plan"]:
            count[person][arbeit] += 1

    # --- 3️⃣ Restliche Arbeiten auffüllen (inkl. Mindest-Besetzung)
    for arbeit in arbeiten:
        aktuelle = [p for a, p in plan if a == arbeit]
        soll = data.get("mindest_besetzung", {}).get(arbeit, 1)
        benoetigt = max(0, soll - len(aktuelle))

        for _ in range(benoetigt):
            if not verfuegbar:
                break
            kandidaten = sorted(verfuegbar, key=lambda p: count[p][arbeit])
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
    return [e for e in data["eintraege"]
            if datetime.strptime(e["date"], "%Y-%m-%d") >= cutoff]

def statistik_wochen(weeks=8):
    zeitraum = get_recent_entries(weeks)
    statistik = defaultdict(lambda: Counter())
    for eintrag in zeitraum:
        for arbeit, person in eintrag["plan"]:
            statistik[person][arbeit] += 1
    return statistik


# ============================================================
# 🎨 Streamlit UI
# ============================================================

st.set_page_config(page_title="Schichtplaner", page_icon="🗓", layout="centered")
st.title("🗓 Schichtplan-Manager")

tab1, tab2, tab3 = st.tabs(["📋 Planung", "🔒 Verwaltung", "📊 Statistik (8 Wochen)"])


# ============================================================
# 1️⃣ TAB – PLANUNG (inkl. Abwesenheiten)
# ============================================================

with tab1:
    st.header("📋 Schichtplan")

    # Abwesenheit auswählen
    st.subheader("🚫 Abwesenheiten (Urlaub / Krank)")
    if "abwesend" not in st.session_state:
        st.session_state["abwesend"] = set()

    if not data["mitarbeiter"]:
        st.info("Keine Mitarbeiter vorhanden")
    else:
        abwahlen = []
        for name in data["mitarbeiter"]:
            cb = st.checkbox(name, value=(name in st.session_state["abwesend"]))
            if cb:
                abwahlen.append(name)
        st.session_state["abwesend"] = set(abwahlen)

        if st.session_state["abwesend"]:
            st.error("❎ Abwesend: " + ", ".join(st.session_state["abwesend"]))
        else:
            st.success("✅ Alle verfügbar")

    st.markdown("---")

    if st.button("🔄 Neuen Plan generieren"):
        plan = generiere_plan()
        if plan:
            st.session_state["plan"] = plan
            st.success("✅ Plan erstellt!")

    plan = st.session_state.get("plan", None)
    if plan:
        st.subheader(f"Aktueller Plan ({datetime.now().strftime('%d.%m.%Y')})")
        df_plan = pd.DataFrame(plan, columns=["Arbeit", "Mitarbeiter"])
        df_plan = df_plan.sort_values("Arbeit")
        st.dataframe(df_plan, use_container_width=True, hide_index=True)

        if st.button("💾 Plan speichern"):
            plan_speichern(plan)
            st.success("Plan gespeichert ✅")
    else:
        st.info("Noch kein Plan vorhanden")


# ============================================================
# 2️⃣ TAB – VERWALTUNG (Passwort geschützt)
# ============================================================

with tab2:
    st.header("🔒 Verwaltung")

    password = st.text_input("Passwort:", type="password")
    if password != ADMIN_PASSWORD:
        st.warning("Zugriff verweigert! Falsches Passwort.")
        st.stop()

    st.success("Zugang erlaubt ✅")

    col1, col2 = st.columns(2)

    # Mitarbeiter-Bereich
    with col1:
        st.subheader("👤 Mitarbeiter")
        name = st.text_input("Mitarbeiter hinzufügen:")
        if st.button("➕ Hinzufügen"):
            add_mitarbeiter(name)
            st.rerun()

        if data["mitarbeiter"]:
            sel = st.selectbox("Mitarbeiter entfernen:", ["–"] + data["mitarbeiter"])
            if sel != "–" and st.button("❌ Entfernen"):
                remove_mitarbeiter(sel)
                st.rerun()
        st.write("**Liste:**", ", ".join(data["mitarbeiter"]) if data["mitarbeiter"] else "_leer_")

    # Arbeiten-Bereich
    with col2:
        st.subheader("🧰 Arbeiten")
        arbeit = st.text_input("Neue Arbeit:")
        if st.button("➕ Arbeit hinzufügen"):
            add_arbeit(arbeit)
            st.rerun()

        if data["arbeiten"]:
            selw = st.selectbox("Arbeit löschen:", ["–"] + data["arbeiten"])
            if selw != "–" and st.button("❌ Arbeit löschen"):
                remove_arbeit(selw)
                st.rerun()
        st.write("**Liste:**", ", ".join(data["arbeiten"]) if data["arbeiten"] else "_leer_")

    st.markdown("---")

    # Feste Zuweisungen
    st.subheader("📌 Feste Zuweisungen")
    if data["mitarbeiter"] and data["arbeiten"]:
        pfix = st.selectbox("Mitarbeiter:", ["–"] + data["mitarbeiter"])
        afix = st.selectbox("Feste Arbeit:", ["–"] + data["arbeiten"])
        if pfix != "–" and afix != "–" and st.button("📍 Fixierung setzen"):
            data["feste_positionen"][pfix] = afix
            save_data(data)
            st.success(f"{pfix} dauerhaft für '{afix}' gesetzt")
            st.rerun()

    if data["feste_positionen"]:
        dffix = pd.DataFrame(
            list(data["feste_positionen"].items()),
            columns=["Mitarbeiter", "Feste Arbeit"]
        )
        st.dataframe(dffix, use_container_width=True, hide_index=True)
        if st.button("🗑️ Alle Fixierungen löschen"):
            data["feste_positionen"].clear()
            save_data(data)
            st.rerun()
    else:
        st.info("Keine festen Zuweisungen definiert")

    st.markdown("---")

    # Mindest-Besetzung
    st.subheader("👥 Mindest-Besetzung")
    if data["arbeiten"]:
        a_sel = st.selectbox("Arbeit wählen:", ["–"] + data["arbeiten"])
        anzahl = st.number_input("Benötigte Anzahl:", min_value=1, max_value=10, step=1)
        if a_sel != "–" and st.button("💾 Mindest-Besetzung speichern"):
            data["mindest_besetzung"][a_sel] = anzahl
            save_data(data)
            st.success(f"Mindest-Besetzung für {a_sel}: {anzahl}")
            st.rerun()

    if data["mindest_besetzung"]:
        dfmin = pd.DataFrame(
            list(data["mindest_besetzung"].items()),
            columns=["Arbeit", "Mindestens"]
        )
        st.dataframe(dfmin, use_container_width=True, hide_index=True)
        if st.button("🗑️ Alle Besetzungsregeln löschen"):
            data["mindest_besetzung"].clear()
            save_data(data)
            st.rerun()
    else:
        st.info("Keine Mindest-Besetzungen vorhanden")


# ============================================================
# 3️⃣ TAB – STATISTIK
# ============================================================

with tab3:
    st.header("📊 Statistik der letzten 8 Wochen")
    statistik = statistik_wochen(8)
    if not statistik:
        st.info("Noch keine Daten.")
    else:
        for person, daten in statistik.items():
            st.subheader(f"👤 {person}")
            df_stat = pd.DataFrame(list(daten.items()), columns=["Arbeit", "Anzahl"])
            st.bar_chart(df_stat.set_index("Arbeit"))
            st.dataframe(df_stat, use_container_width=True, hide_index=True)
    st.markdown("📅 Zeitraum: letzte **8 Wochen**")
