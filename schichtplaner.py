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

# 🔹 Feste Mitarbeiter automatisch hinzufügen
FIXE_MITARBEITER = ["Martin", "Nikolaj", "Eric", "Abdullah"]
for name in FIXE_MITARBEITER:
    if name not in data["mitarbeiter"]:
        data["mitarbeiter"].append(name)

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

# ------------------- STATISTIK -------------------
with tab3:
    st.header("📊 Statistik der letzten 8 Wochen")

    if st.button("🗑️ Alle Statistikdaten löschen"):
        data["eintraege"] = []
        save_data(data)
        st.success("Alle Statistikdaten gelöscht!")
        st.experimental_rerun()