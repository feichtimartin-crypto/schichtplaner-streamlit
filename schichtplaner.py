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

DEFAULT_ARBEITEN = [
    "Teamlead",
    "S3",
    "Bahnhof",
    "Bahnhof Stapler",
    "Bahnhof Tugger",
    "Wareneingang",
    "Frunks",
    "Door´s Stapler",
    "Door´s Tugger",
    "Sonstiges"
]

DEFAULT_MIN = {
    "Teamlead": 1,
    "S3": 1,
    "Bahnhof": 2,
    "Bahnhof Stapler": 3,
    "Bahnhof Tugger": 5,
    "Wareneingang": 3,
    "Frunks": 1,
    "Door´s Stapler": 1,
    "Door´s Tugger": 1,
    "Sonstiges": 0
}

DEFAULT_MAX = {
    "Teamlead": 2,
    "S3": 2,
    "Bahnhof": 4,
    "Bahnhof Stapler": 3,
    "Bahnhof Tugger": 5,
    "Wareneingang": 4,
    "Frunks": 1,
    "Door´s Stapler": 1,
    "Door´s Tugger": 1,
    "Sonstiges": 999
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

for k in ["feste_positionen", "mindest_besetzung", "max_besetzung"]:
    if k not in data:
        data[k] = {}

if not data["arbeiten"]:
    data["arbeiten"] = DEFAULT_ARBEITEN.copy()

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

    # feste Positionen zuerst
    for person, arbeit in data.get("feste_positionen", {}).items():
        if person in verfuegbar and arbeit in arbeiten:
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    count = defaultdict(lambda: defaultdict(int))
    for e in data["eintraege"]:
        for arbeit, person in e["plan"]:
            count[person][arbeit] += 1

    # Zuerst alle Arbeiten außer Bahnhof/Sonstiges
    for arbeit in arbeiten:
        if arbeit in ["Bahnhof", "Sonstiges"]:
            continue
        min_soll = data["mindest_besetzung"].get(arbeit, 1)
        max_soll = data["max_besetzung"].get(arbeit, min_soll)

        while len([p for a, p in plan if a == arbeit]) < min_soll and verfuegbar:
            kandidaten = sorted(verfuegbar, key=lambda p: count[p][arbeit])
            person = random.choice(kandidaten)
            plan.append((arbeit, person))
            verfuegbar.remove(person)

        while len([p for a, p in plan if a == arbeit]) < max_soll and verfuegbar:
            kandidaten = sorted(verfuegbar, key=lambda p: count[p][arbeit])
            person = random.choice(kandidaten)
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    # Bahnhof + Sonstiges: Alle verbleibenden Mitarbeiter
    for person in verfuegbar:
        plan.append(("Bahnhof", person))

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
# 🧭 Streamlit UI
# ============================================================

st.set_page_config(page_title="Schichtplaner", page_icon="🗓", layout="centered")
st.title("🗓 Schichtplan-Manager")

tab1, tab2, tab3 = st.tabs(["📋 Planung", "🔒 Verwaltung", "📊 Statistik (8 Wochen)"])

arbeitsplatz_reihenfolge = [
    "Bahnhof",
    "Bahnhof Stapler",
    "Bahnhof Tugger",
    "Wareneingang",
    "Frunks",
    "Door´s Stapler",
    "Door´s Tugger",
    "Sonstiges",
    "Teamlead",
    "S3"
]

# ------------------- PLANUNG -------------------
with tab1:
    st.header("🗓 Planung")
    st.subheader("🚫 Abwesenheiten (Urlaub / Krank)")

    if "abwesend" not in st.session_state:
        st.session_state["abwesend"] = set()

    if not data["mitarbeiter"]:
        st.info("Noch keine Mitarbeitenden angelegt.")
    else:
        n = 4
        rows = [data["mitarbeiter"][i:i+n] for i in range(0, len(data["mitarbeiter"]), n)]
        abwesende = set(st.session_state["abwesend"])
        tmp = set()
        for row in rows:
            cols = st.columns(len(row))
            for col, name in zip(cols, row):
                checked = col.checkbox(name, value=(name in abwesende))
                if checked:
                    tmp.add(name)
        st.session_state["abwesend"] = tmp
        if tmp:
            st.warning("❎ Abwesend: " + ", ".join(tmp))
        else:
            st.success("✅ Alle verfügbar")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📅 Plan Mo/Di erstellen"):
            plan = generiere_plan("MoDi")
            if plan:
                st.session_state["plan_modi"] = plan
                st.success("Plan Mo/Di erstellt!")
    with c2:
        if st.button("📅 Plan Mi–Fr erstellen"):
            plan = generiere_plan("MiFr")
            if plan:
                st.session_state["plan_mifr"] = plan
                st.success("Plan Mi–Fr erstellt!")

    st.divider()
    for key, zeitraum_label in [("plan_modi", "Mo/Di"), ("plan_mifr", "Mi–Fr")]:
        plan = st.session_state.get(key, None)
        if plan:
            st.subheader(f"📋 Plan {zeitraum_label}")
            df = pd.DataFrame(plan["plan"], columns=["Arbeit", "Mitarbeiter"])
            df_grouped = df.groupby("Arbeit")["Mitarbeiter"].apply(list).reindex(arbeitsplatz_reihenfolge)
            df_grouped = df_grouped.apply(lambda x: x if isinstance(x, list) else [])

            # Max 4 Mitarbeiter für Bahnhof, Rest → Sonstiges
            bahnhof = df_grouped["Bahnhof"] if "Bahnhof" in df_grouped else []
            if len(bahnhof) > 4:
                df_grouped["Bahnhof"] = bahnhof[:4]
                df_grouped["Sonstiges"] = df_grouped.get("Sonstiges", []) + bahnhof[4:]

            # Spaltennamen ändern
            rename_map = {
                "Bahnhof Tugger": "Tugger",
                "Wareneingang": "WE"
            }
            df_grouped = df_grouped.rename(index=rename_map)

            # Alle Spalten auf gleiche Länge bringen
            max_len = df_grouped.apply(len).max()
            df_expanded = pd.DataFrame({
                a: df_grouped[a] + [""] * (max_len - len(df_grouped[a]))
                for a in df_grouped.index
            })
            st.dataframe(df_expanded, use_container_width=True, hide_index=True)

            if st.button(f"💾 {zeitraum_label} speichern"):
                plan_speichern(plan)
                st.success(f"Plan für {zeitraum_label} gespeichert ✅")
        else:
            st.info(f"Kein Plan für {zeitraum_label} generiert.")

# ------------------- VERWALTUNG -------------------
with tab2:
    st.header("🔒 Verwaltung")
    password = st.text_input("Passwort:", type="password")
    if password != ADMIN_PASSWORD:
        st.warning("Zugriff verweigert – falsches Passwort.")
        st.stop()
    st.success("✅ Zugriff erlaubt")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👤 Mitarbeitende")
        new = st.text_input("Neue/r Mitarbeiter*in:")
        if st.button("➕ Hinzufügen"):
            add_mitarbeiter(new)
            st.rerun()
        if data["mitarbeiter"]:
            sel = st.selectbox("Entfernen:", ["–"] + data["mitarbeiter"])
            if sel != "–" and st.button("❌ Entfernen"):
                remove_mitarbeiter(sel)
                st.rerun()
        st.write("**Aktuell:**", ", ".join(data["mitarbeiter"]) if data["mitarbeiter"] else "_leer_")

    with col2:
        st.subheader("🧰 Arbeiten")
        newa = st.text_input("Neue Arbeit:")
        if st.button("➕ Arbeit hinzufügen"):
            add_arbeit(newa)
            st.rerun()
        if data["arbeiten"]:
            sela = st.selectbox("Arbeit löschen:", ["–"] + data["arbeiten"])
            if sela != "–" and st.button("❌ Arbeit löschen"):
                remove_arbeit(sela)
                st.rerun()
        st.write("**Aktuell:**", ", ".join(data["arbeiten"]) if data["arbeiten"] else "_leer_")

    st.divider()
    st.subheader("📌 Feste Positionen")
    if data["mitarbeiter"] and data["arbeiten"]:
        pers = st.selectbox("Mitarbeiter:", ["–"] + data["mitarbeiter"])
        job = st.selectbox("Feste Arbeit:", ["–"] + data["arbeiten"])
        if pers != "–" and job != "–" and st.button("📍 Fixierung setzen"):
            data["feste_positionen"][pers] = job
            save_data(data)
            st.success(f"{pers} dauerhaft auf {job} gesetzt")
            st.rerun()

    if data["feste_positionen"]:
        df_fix = pd.DataFrame(data["feste_positionen"].items(), columns=["Mitarbeiter", "Arbeit"])
        st.dataframe(df_fix, use_container_width=True, hide_index=True)
        if st.button("🗑️ Alle Fixierungen löschen"):
            data["feste_positionen"].clear()
            save_data(data)
            st.rerun()
    else:
        st.info("Keine festen Positionen.")

    st.divider()
    st.subheader("👥 Mindest-Besetzung")
    if data["arbeiten"]:
        job = st.selectbox("Arbeit wählen:", ["–"] + data["arbeiten"])
        anzahl = st.number_input("Mindestens benötigte Personen:", min_value=1, max_value=10, step=1)
        if job != "–" and st.button("💾 Speichern"):
            data["mindest_besetzung"][job] = anzahl
            save_data(data)
            st.success(f"Mindest-Besetzung für {job}: {anzahl}")
            st.rerun()

    if data["mindest_besetzung"]:
        df_min = pd.DataFrame(data["mindest_besetzung"].items(), columns=["Arbeit", "Min. Personen"])
        st.dataframe(df_min, use_container_width=True, hide_index=True)
        if st.button("🗑️ Alle löschen"):
            data["mindest_besetzung"].clear()
            save_data(data)
            st.rerun()
    else:
        st.info("Keine Mindestregelungen gesetzt.")

# ------------------- STATISTIK -------------------
with tab3:
    st.header("📊 Statistik der letzten 8 Wochen")

    if st.button("🗑️ Alle Statistikdaten löschen"):
        data["eintraege"].clear()
        save_data(data)
        st.success("Alle Statistikdaten gelöscht!")
        st.experimental_rerun()

    stats = statistik_wochen(8)
    if not stats:
        st.info("Noch keine Daten.")
    else:
        for person, daten in stats.items():
            if person in ["S3", "Teamlead"]:
                continue
            st.subheader(f"👤 {person}")
            df = pd.DataFrame(list(daten.items()), columns=["Arbeit", "Anzahl"])
            st.bar_chart(df.set_index("Arbeit"))
            st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown("📅 Betrachtungszeitraum: **8 Wochen**")