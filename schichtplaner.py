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

# Reihenfolge der Arbeiten im Plan (Spalten von links nach rechts)
ARBEITSPLATZ_REIHENFOLGE = [
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

FIXE_MITARBEITER = [
    "Martin", "Nikolaj", "Eric", "Abdullah", "Monthe", "Fabian",
    "Patrick", "Peter", "Marcin K.", "Daniel", "Damian", "Rene",
    "Marcin C.", "Kevin", "Jaroslaw", "Adrian", "Kamil", "Tomasz",
    "Maciej", "Krzystof", "Jakub", "Radoslaw", "Vazir", "Ebrahim",
    "Lukasz", "Anna", "Klaudia", "Ryzard", "Muhamad"
]

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

# Sicherheits-Upgrade für ältere Daten
for k in ["feste_positionen", "mindest_besetzung", "max_besetzung"]:
    if k not in data:
        data[k] = {}

# Feste Mitarbeiterliste einmalig befüllen
for name in FIXE_MITARBEITER:
    if name not in data["mitarbeiter"]:
        data["mitarbeiter"].append(name)

# Standard-Arbeiten setzen falls noch leer
if not data["arbeiten"]:
    data["arbeiten"] = ARBEITSPLATZ_REIHENFOLGE.copy()

# Standard Min/Max einmalig setzen
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
    """Erstellt einen fairen Schichtplan mit Mindest‑ und Maximal‑Besetzung."""
    mitarbeiter = data["mitarbeiter"]
    arbeiten = data["arbeiten"]

    abwesende = st.session_state.get("abwesend", set())
    verfuegbar = [m for m in mitarbeiter if m not in abwesende]

    if not verfuegbar or not arbeiten:
        st.warning("Bitte zuerst Mitarbeiter und Arbeiten hinzufügen!")
        return None

    plan = []

    # 1️⃣ Feste Positionen zuerst
    for person, arbeit in data.get("feste_positionen", {}).items():
        if person in verfuegbar and arbeit in arbeiten:
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    # 2️⃣ Zähldaten für faire Verteilung
    count = defaultdict(lambda: defaultdict(int))
    for e in data["eintraege"]:
        for arbeit, person in e["plan"]:
            count[person][arbeit] += 1

    # 3️⃣ Alle Arbeiten in definierter Reihenfolge befüllen (außer Sonstiges)
    for arbeit in ARBEITSPLATZ_REIHENFOLGE:
        if arbeit == "Sonstiges" or arbeit not in arbeiten:
            continue

        min_soll = data["mindest_besetzung"].get(arbeit, 1)
        max_soll = data["max_besetzung"].get(arbeit, min_soll)

        # Mindest-Besetzung sicherstellen
        while len([p for a, p in plan if a == arbeit]) < min_soll and verfuegbar:
            kandidaten = sorted(verfuegbar, key=lambda p: count[p][arbeit])
            min_count = count[kandidaten[0]][arbeit]
            beste = [k for k in kandidaten if count[k][arbeit] == min_count]
            person = random.choice(beste)
            plan.append((arbeit, person))
            verfuegbar.remove(person)

        # Bis Maximum auffüllen wenn noch Leute verfügbar
        while len([p for a, p in plan if a == arbeit]) < max_soll and verfuegbar:
            kandidaten = sorted(verfuegbar, key=lambda p: count[p][arbeit])
            min_count = count[kandidaten[0]][arbeit]
            beste = [k for k in kandidaten if count[k][arbeit] == min_count]
            person = random.choice(beste)
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    # 4️⃣ Restliche Mitarbeiter → Sonstiges
    for person in verfuegbar:
        plan.append(("Sonstiges", person))

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
            if datetime.strptime(e["date"], "%Y-%m-%d") >= cutoff:
                result.append(e)
        except Exception:
            pass
    return result

def statistik_wochen(weeks=8):
    zeitraum = get_recent_entries(weeks)
    statistik = defaultdict(lambda: Counter())
    for eintrag in zeitraum:
        for arbeit, person in eintrag["plan"]:
            statistik[person][arbeit] += 1
    return statistik

def plan_als_tabelle(plan_eintrag):
    """Wandelt einen Plan in eine horizontale Tabelle um (Arbeiten als Spalten)."""
    df = pd.DataFrame(plan_eintrag["plan"], columns=["Arbeit", "Mitarbeiter"])
    df_grouped = (
        df.groupby("Arbeit")["Mitarbeiter"]
        .apply(list)
        .reindex(ARBEITSPLATZ_REIHENFOLGE)
        .apply(lambda x: x if isinstance(x, list) else [])
    )
    max_len = df_grouped.apply(len).max() or 1
    df_expanded = pd.DataFrame({
        a: df_grouped[a] + [""] * (max_len - len(df_grouped[a]))
        for a in df_grouped.index
    })
    return df_expanded

# ============================================================
# 🎨 Streamlit Oberfläche
# ============================================================

st.set_page_config(
    page_title="Schichtplaner",
    page_icon="🗓",
    layout="wide"   # wide: mehr Platz für die horizontale Tabelle
)
st.title("🗓 Schichtplan-Manager")

tab1, tab2, tab3 = st.tabs(["📋 Planung", "🔒 Verwaltung", "📊 Statistik (8 Wochen)"])

# ============================================================
# 1️⃣ PLANUNG
# ============================================================

with tab1:
    st.header("📅 Schichtplanung")

    # Abwesenheiten
    st.subheader("🚫 Abwesenheiten (Urlaub / Krank)")
    if "abwesend" not in st.session_state:
        st.session_state["abwesend"] = set()

    if not data["mitarbeiter"]:
        st.info("Noch keine Mitarbeitenden angelegt.")
    else:
        n = 5  # 5 Personen pro Zeile
        rows = [data["mitarbeiter"][i:i+n] for i in range(0, len(data["mitarbeiter"]), n)]
        tmp = set()
        for row in rows:
            cols = st.columns(len(row))
            for col, name in zip(cols, row):
                if col.checkbox(name, value=(name in st.session_state["abwesend"])):
                    tmp.add(name)
        st.session_state["abwesend"] = tmp

        if tmp:
            st.warning("❎ Abwesend: " + ", ".join(sorted(tmp)))
        else:
            st.success("✅ Alle Mitarbeitenden verfügbar")

    st.divider()

    # Plan erstellen
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📅 Plan Mo / Di erstellen", use_container_width=True):
            plan = generiere_plan("MoDi")
            if plan:
                st.session_state["plan_modi"] = plan
                st.success("✅ Plan Mo/Di erstellt!")
    with c2:
        if st.button("📅 Plan Mi – Fr erstellen", use_container_width=True):
            plan = generiere_plan("MiFr")
            if plan:
                st.session_state["plan_mifr"] = plan
                st.success("✅ Plan Mi–Fr erstellt!")

    st.divider()

    # Pläne anzeigen
    for key, label in [("plan_modi", "Mo / Di"), ("plan_mifr", "Mi – Fr")]:
        plan = st.session_state.get(key)
        if plan:
            st.subheader(f"📋 Plan {label}  —  {plan['date']}")
            st.dataframe(
                plan_als_tabelle(plan),
                use_container_width=True,
                hide_index=True
            )
            if st.button(f"💾 Plan {label} speichern", key=f"save_{key}"):
                plan_speichern(plan)
                st.success(f"Plan {label} gespeichert ✅")
        else:
            st.info(f"Noch kein Plan für {label} erstellt.")

# ============================================================
# 2️⃣ VERWALTUNG
# ============================================================

with tab2:
    st.header("🔒 Verwaltung – Passwortgeschützt")
    password = st.text_input("Passwort eingeben:", type="password")
    if password != ADMIN_PASSWORD:
        st.warning("🚫 Zugriff verweigert – falsches oder fehlendes Passwort.")
        st.stop()

    st.success("✅ Zugriff erlaubt – Willkommen!")
    st.divider()

    # Mitarbeiter & Arbeiten
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("👤 Mitarbeitende")
        new = st.text_input("Neue/r Mitarbeiter*in:")
        if st.button("➕ Hinzufügen"):
            add_mitarbeiter(new)
            st.rerun()
        if data["mitarbeiter"]:
            sel = st.selectbox("Mitarbeiter entfernen:", ["–"] + data["mitarbeiter"])
            if sel != "–" and st.button("❌ Entfernen"):
                remove_mitarbeiter(sel)
                st.rerun()
        st.caption("Aktuell: " + (", ".join(data["mitarbeiter"]) or "–"))

    with col2:
        st.subheader("🧰 Arbeiten / Positionen")
        newa = st.text_input("Neue Arbeit / Position:")
        if st.button("➕ Arbeit hinzufügen"):
            add_arbeit(newa)
            st.rerun()
        if data["arbeiten"]:
            sela = st.selectbox("Arbeit löschen:", ["–"] + data["arbeiten"])
            if sela != "–" and st.button("❌ Arbeit löschen"):
                remove_arbeit(sela)
                st.rerun()
        st.caption("Aktuell: " + (", ".join(data["arbeiten"]) or "–"))

    st.divider()

    # Feste Positionen
    st.subheader("📌 Feste Positionen")
    if data["mitarbeiter"] and data["arbeiten"]:
        c1, c2 = st.columns(2)
        with c1:
            pers = st.selectbox("Mitarbeiter:", ["–"] + data["mitarbeiter"])
        with c2:
            job = st.selectbox("Feste Arbeit:", ["–"] + data["arbeiten"])
        if pers != "–" and job != "–" and st.button("📍 Fixierung setzen"):
            data["feste_positionen"][pers] = job
            save_data(data)
            st.success(f"✅ {pers} dauerhaft auf „{job}" gesetzt")
            st.rerun()

    if data["feste_positionen"]:
        df_fix = pd.DataFrame(
            data["feste_positionen"].items(),
            columns=["Mitarbeiter", "Feste Arbeit"]
        )
        st.dataframe(df_fix, use_container_width=True, hide_index=True)
        if st.button("🗑️ Alle Fixierungen löschen"):
            data["feste_positionen"].clear()
            save_data(data)
            st.rerun()
    else:
        st.info("Keine festen Positionen definiert.")

    st.divider()

    # Mindest‑ und Max‑Besetzung
    st.subheader("👥 Mindest‑ & Maximal‑Besetzung")
    if data["arbeiten"]:
        c1, c2, c3 = st.columns(3)
        with c1:
            job_bset = st.selectbox("Position wählen:", ["–"] + data["arbeiten"])
        with c2:
            min_val = st.number_input(
                "Mindestens:",
                min_value=0, max_value=20, step=1,
                value=int(data["mindest_besetzung"].get(job_bset, 1)) if job_bset != "–" else 1
            )
        with c3:
            max_val = st.number_input(
                "Maximal:",
                min_value=0, max_value=50, step=1,
                value=int(data["max_besetzung"].get(job_bset, 1)) if job_bset != "–" else 1
            )
        if job_bset != "–" and st.button("💾 Besetzung speichern"):
            data["mindest_besetzung"][job_bset] = min_val
            data["max_besetzung"][job_bset] = max_val
            save_data(data)
            st.success(f"✅ {job_bset}: Min={min_val} / Max={max_val}")
            st.rerun()

    # Tabelle Mindest/Max zusammen anzeigen
    if data["mindest_besetzung"] or data["max_besetzung"]:
        alle_arbeiten = list(set(
            list(data["mindest_besetzung"].keys()) +
            list(data["max_besetzung"].keys())
        ))
        df_bset = pd.DataFrame({
            "Arbeit": alle_arbeiten,
            "Min. Personen": [data["mindest_besetzung"].get(a, "–") for a in alle_arbeiten],
            "Max. Personen": [data["max_besetzung"].get(a, "–") for a in alle_arbeiten]
        })
        st.dataframe(df_bset, use_container_width=True, hide_index=True)

        if st.button("🗑️ Alle Besetzungsregeln löschen"):
            data["mindest_besetzung"].clear()
            data["max_besetzung"].clear()
            save_data(data)
            st.rerun()

# ============================================================
# 3️⃣ STATISTIK
# ============================================================

with tab3:
    st.header("📊 Statistik der letzten 8 Wochen")

    if st.button("🗑️ Alle Statistikdaten löschen"):
        data["eintraege"] = []
        save_data(data)
        st.success("Alle Statistikdaten gelöscht!")
        st.rerun()

    stats = statistik_wochen(8)
    if not stats:
        st.info("Noch keine gespeicherten Pläne vorhanden.")
    else:
        for person, daten in sorted(stats.items()):
            st.subheader(f"👤 {person}")
            df_stat = pd.DataFrame(list(daten.items()), columns=["Arbeit", "Anzahl"])
            df_stat = df_stat.sort_values("Anzahl", ascending=False)
            st.bar_chart(df_stat.set_index("Arbeit"))
            st.dataframe(df_stat, use_container_width=True, hide_index=True)

    st.markdown("📅 Betrachtungszeitraum: **8 Wochen**")
