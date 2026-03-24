import streamlit as st
import json
import base64
import requests
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# ============================================================
# \ud83d\udd38 GitHub-basierte Datenpersistenz
# ============================================================
# Lege in Streamlit Cloud unter Settings > Secrets folgendes an:
#
# [github]
# token = "ghp_deinPersonalAccessToken"
# repo  = "deinUsername/deinRepo"
# path  = "data/historie.json"
# ============================================================

GITHUB_API = "https://api.github.com"
ADMIN_PASSWORD = "Nikolajistcoll"

DEFAULT_ARBEITEN = [
    "Teamlead", "S3", "Bahnhof", "Bahnhof Stapler", "Bahnhof Tugger",
    "Wareneingang", "Frunks", "Door\u00b4s Stapler", "Door\u00b4s Tugger", "Sonstiges"
]

DEFAULT_MIN = {
    "Teamlead": 1, "S3": 1, "Bahnhof": 2, "Bahnhof Stapler": 3,
    "Bahnhof Tugger": 5, "Wareneingang": 3, "Frunks": 1,
    "Door\u00b4s Stapler": 1, "Door\u00b4s Tugger": 1, "Sonstiges": 0
}

DEFAULT_MAX = {
    "Teamlead": 2, "S3": 2, "Bahnhof": 4, "Bahnhof Stapler": 3,
    "Bahnhof Tugger": 5, "Wareneingang": 4, "Frunks": 1,
    "Door\u00b4s Stapler": 1, "Door\u00b4s Tugger": 1, "Sonstiges": 999
}

FIXE_MITARBEITER = [
    "Martin", "Nikolaj", "Eric", "Abdullah", "Monthe", "Fabian", "Patrick",
    "Peter", "Marcin K.", "Daniel", "Damian", "Rene", "Marcin C.", "Kevin",
    "Jaroslaw", "Adrian", "Kamil", "Tomasz", "Maciej", "Krzystof", "Jakub",
    "Radoslaw", "Vazir", "Ebrahim", "Lukasz", "Anna", "Klaudia", "Ryzard", "Muhamad"
]

ARBEITSPLATZ_REIHENFOLGE = [
    "Bahnhof", "Bahnhof Stapler", "Bahnhof Tugger", "Wareneingang",
    "Frunks", "Door\u00b4s Stapler", "Door\u00b4s Tugger", "Sonstiges", "Teamlead", "S3"
]

# ============================================================
# \ud83d\udd39 GitHub Datenverwaltung
# ============================================================

def _headers():
    token = st.secrets["github"]["token"]
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def _repo():
    return st.secrets["github"]["repo"]

def _path():
    return st.secrets["github"]["path"]

def _empty_data():
    return {
        "mitarbeiter": [],
        "arbeiten": [],
        "eintraege": [],
        "feste_positionen": {},
        "mindest_besetzung": {},
        "max_besetzung": {}
    }

def load_data() -> dict:
    url = f"{GITHUB_API}/repos/{_repo()}/contents/{_path()}"
    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        if r.status_code == 404:
            return _empty_data()
        r.raise_for_status()
        content = r.json()["content"]
        decoded = base64.b64decode(content).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        st.error(f"\u274c Fehler beim Laden der Daten: {e}")
        return _empty_data()

def save_data(data: dict) -> bool:
    url = f"{GITHUB_API}/repos/{_repo()}/contents/{_path()}"
    sha = None
    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        if r.status_code == 200:
            sha = r.json()["sha"]
    except Exception:
        pass

    content = base64.b64encode(
        json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")

    payload = {"message": "Schichtplan Update", "content": content}
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(url, headers=_headers(), json=payload, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"\u274c Fehler beim Speichern: {e}")
        return False

# ============================================================
# \ud83d\udd39 Daten laden & initialisieren
# ============================================================

data = load_data()

# Reihenfolge der Mitarbeiter sicherstellen
extras = [m for m in data["mitarbeiter"] if m not in FIXE_MITARBEITER]
data["mitarbeiter"] = FIXE_MITARBEITER + extras

# Fehlende Keys auff\u00fcllen
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
# \u2699\ufe0f Hilfsfunktionen
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
# \ud83e\udde0 Plan-Logik
# ============================================================

def generiere_plan(zeitraum_label):
    mitarbeiter = data["mitarbeiter"]
    arbeiten = data["arbeiten"]
    abwesende = st.session_state.get("abwesend", set())
    verfuegbar = [m for m in mitarbeiter if m not in abwesende]

    if not verfuegbar or not arbeiten:
        st.warning("Bitte zuerst Mitarbeiter und Arbeiten hinzuf\u00fcgen!")
        return None

    plan = []

    # Feste Positionen zuerst
    for person, arbeit in data.get("feste_positionen", {}).items():
        if person in verfuegbar and arbeit in arbeiten:
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    # Historien-Z\u00e4hler
    count = defaultdict(lambda: defaultdict(int))
    gesamt = defaultdict(int)
    for e in data["eintraege"]:
        for arbeit, person in e["plan"]:
            count[person][arbeit] += 1
            gesamt[person] += 1

    def fairer_kandidat(verfuegbar_liste, arbeit):
        return sorted(
            verfuegbar_liste,
            key=lambda p: (count[p][arbeit], gesamt[p])
        )[0]

    # Alle Arbeiten au\u00dfer Bahnhof/Sonstiges fair verteilen
    for arbeit in arbeiten:
        if arbeit in ["Bahnhof", "Sonstiges"]:
            continue
        min_soll = data["mindest_besetzung"].get(arbeit, 1)
        max_soll = data["max_besetzung"].get(arbeit, min_soll)

        while len([p for a, p in plan if a == arbeit]) < min_soll and verfuegbar:
            person = fairer_kandidat(verfuegbar, arbeit)
            plan.append((arbeit, person))
            verfuegbar.remove(person)

        while len([p for a, p in plan if a == arbeit]) < max_soll and verfuegbar:
            person = fairer_kandidat(verfuegbar, arbeit)
            plan.append((arbeit, person))
            verfuegbar.remove(person)

    # Bahnhof & Sonstiges f\u00fcr \u00dcbrige
    bahnhof_max = data["max_besetzung"].get("Bahnhof", 4)
    bahnhof_aktuell = len([p for a, p in plan if a == "Bahnhof"])
    bahnhof_frei = max(0, bahnhof_max - bahnhof_aktuell)

    restliche = list(verfuegbar)
    restliche_bahnhof = sorted(restliche, key=lambda p: (count[p]["Bahnhof"], gesamt[p]))
    zugeteilt = set()

    for person in restliche_bahnhof:
        if bahnhof_frei > 0:
            plan.append(("Bahnhof", person))
            bahnhof_frei -= 1
            zugeteilt.add(person)

    restliche_sonstiges = sorted(
        [p for p in restliche if p not in zugeteilt],
        key=lambda p: (count[p]["Sonstiges"], gesamt[p])
    )
    for person in restliche_sonstiges:
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
            d = datetime.strptime(e["date"], "%Y-%m-%d")
            if d >= cutoff:
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

# ============================================================
# \ud83e\udded Streamlit UI
# ============================================================

st.set_page_config(page_title="Schichtplaner", page_icon="\ud83d\uddd3", layout="centered")
st.title("\ud83d\uddd3 Schichtplan-Manager")

tab1, tab2, tab3 = st.tabs(["\ud83d\udccb Planung", "\ud83d\udd12 Verwaltung", "\ud83d\udcca Statistik (8 Wochen)"])

# ------------------- PLANUNG -------------------
with tab1:
    st.header("\ud83d\uddd3 Planung")
    st.subheader("\ud83d\udeab Abwesenheiten (Urlaub / Krank)")

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
            st.warning("\u274e Abwesend: " + ", ".join(tmp))
        else:
            st.success("\u2705 Alle verf\u00fcgbar")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("\ud83d\udcc5 Plan Mo/Di erstellen"):
            plan = generiere_plan("MoDi")
            if plan:
                st.session_state["plan