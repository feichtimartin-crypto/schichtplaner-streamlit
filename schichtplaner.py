import streamlit as st
import json
import base64
import requests
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# ============================================================
# GitHub-basierte Datenpersistenz
# ============================================================
# Streamlit Cloud -> Settings -> Secrets:
#
# [github]
# token = "ghp_DeinPersonalAccessToken"
# repo  = "deinUsername/deinRepo"
# path  = "data/historie.json"
# ============================================================

ADMIN_PASSWORD = "Nikolajistcool"

DEFAULT_ARBEITEN = [
    "Teamlead", "S3", "Bahnhof", "Bahnhof Stapler", "Bahnhof Tugger",
    "WE", "Frunks", "Door's Stapler", "Door's Tugger", "Sonstiges"
]

DEFAULT_MIN = {
    "Teamlead": 1, "S3": 1, "Bahnhof": 2, "Bahnhof Stapler": 3,
    "Bahnhof Tugger": 5, "WE": 3, "Frunks": 1,
    "Door's Stapler": 1, "Door's Tugger": 1, "Sonstiges": 0
}

DEFAULT_MAX = {
    "Teamlead": 2, "S3": 2, "Bahnhof": 4, "Bahnhof Stapler": 3,
    "Bahnhof Tugger": 5, "WE": 4, "Frunks": 1,
    "Door's Stapler": 1, "Door's Tugger": 1, "Sonstiges": 999
}

FIXE_MITARBEITER = [
    "Martin", "Nikolaj", "Eric", "Abdullah", "Monthe", "Fabian", "Patrick",
    "Peter", "Marcin K.", "Daniel", "Damian", "Rene", "Marcin C.", "Kevin",
    "Jaroslaw", "Adrian", "Kamil", "Tomasz", "Maciej", "Krzystof", "Jakub",
    "Radoslaw", "Vazir", "Ebrahim", "Lukasz", "Anna", "Klaudia", "Muhamad"
]

ARBEITSPLATZ_REIHENFOLGE = [
    "Bahnhof", "Bahnhof Stapler", "Bahnhof Tugger", "WE",
    "Frunks", "Door's Stapler", "Door's Tugger", "Sonstiges", "Teamlead", "S3"
]

GITHUB_API = "https://api.github.com"

# ============================================================
# GitHub Datenverwaltung
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
        st.error(f"Fehler beim Laden der Daten: {e}")
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
        json.dumps(data, ensure_ascii=True, indent=2).encode("utf-8")
    ).decode("utf-8")

    payload = {"message": "Schichtplan Update", "content": content}
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(url, headers=_headers(), json=payload, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")
        return False

# ============================================================
# Daten laden & initialisieren
# ============================================================

data = load_data()

extras = [m for m in data["mitarbeiter"] if m not in FIXE_MITARBEITER]
data["mitarbeiter"] = FIXE_MITARBEITER + extras

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
# Hilfsfunktionen
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
# Plan-Logik
# ============================================================

def generiere_plan(zeitraum_label):
    mitarbeiter = data["mitarbeiter"]
    arbeiten = data["arbeiten"]
    abwesende = st.session_state.get("abwesend", set())
    verfuegbar = [m for m in mitarbeiter if m not in abwesende]

    if not verfuegbar or not arbeiten:
        st.warning("Bitte zuerst Mitarbeiter und Arbeiten hinzufuegen!")
        return None

    plan = []

    for person, arbeit in data.get("feste_positionen", {}).items():
        if person in verfuegbar and arbeit in arbeiten:
            plan.append((arbeit, person))
            verfuegbar.remove(person)

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
# Streamlit UI
# ============================================================

st.set_page_config(page_title="Schichtplaner", page_icon=":calendar:", layout="centered")
st.title("Schichtplan-Manager")

tab1, tab2, tab3 = st.tabs(["Planung", "Verwaltung", "Statistik (8 Wochen)"])

# ------------------- PLANUNG -------------------
with tab1:
    st.header("Planung")
    st.subheader("Abwesenheiten (Urlaub / Krank)")

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
            st.warning("Abwesend: " + ", ".join(tmp))
        else:
            st.success("Alle verfuegbar")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Plan Mo/Di erstellen"):
            plan = generiere_plan("MoDi")
            if plan:
                st.session_state["plan_modi"] = plan
                st.success("Plan Mo/Di erstellt!")
    with c2:
        if st.button("Plan Mi-Fr erstellen"):
            plan = generiere_plan("MiFr")
            if plan:
                st.session_state["plan_mifr"] = plan
                st.success("Plan Mi-Fr erstellt!")

    st.divider()
    for key, zeitraum_label in [("plan_modi", "Mo/Di"), ("plan_mifr", "Mi-Fr")]:
        plan = st.session_state.get(key, None)
        if plan:
            st.subheader(f"Plan {zeitraum_label}")
            df = pd.DataFrame(plan["plan"], columns=["Arbeit", "Mitarbeiter"])
            df_grouped = df.groupby("Arbeit")["Mitarbeiter"].apply(list).reindex(ARBEITSPLATZ_REIHENFOLGE)
            df_grouped = df_grouped.apply(lambda x: x if isinstance(x, list) else [])
            max_len = df_grouped.apply(len).max()
            df_expanded = pd.DataFrame({
                a: df_grouped[a] + [""] * (max_len - len(df_grouped[a]))
                for a in df_grouped.index
            })
            st.dataframe(df_expanded, use_container_width=True, hide_index=True)
            if st.button(f"Speichern {zeitraum_label}"):
                plan_speichern(plan)
                st.success(f"Plan fuer {zeitraum_label} gespeichert!")
        else:
            st.info(f"Kein Plan fuer {zeitraum_label} generiert.")

# ------------------- VERWALTUNG -------------------
with tab2:
    st.header("Verwaltung")
    password = st.text_input("Passwort:", type="password")
    if password != ADMIN_PASSWORD:
        st.warning("Zugriff verweigert - falsches Passwort.")
        st.stop()
    st.success("Zugriff erlaubt")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Mitarbeitende")
        new = st.text_input("Neue/r Mitarbeiter*in:")
        if st.button("Hinzufuegen"):
            add_mitarbeiter(new)
            st.rerun()
        if data["mitarbeiter"]:
            sel = st.selectbox("Entfernen:", ["-"] + data["mitarbeiter"])
            if sel != "-" and st.button("Entfernen"):
                remove_mitarbeiter(sel)
                st.rerun()
        st.write("**Aktuell:**", ", ".join(data["mitarbeiter"]) if data["mitarbeiter"] else "_leer_")

    with col2:
        st.subheader("Arbeiten")
        newa = st.text_input("Neue Arbeit:")
        if st.button("Arbeit hinzufuegen"):
            add_arbeit(newa)
            st.rerun()
        if data["arbeiten"]:
            sela = st.selectbox("Arbeit loeschen:", ["-"] + data["arbeiten"])
            if sela != "-" and st.button("Arbeit loeschen"):
                remove_arbeit(sela)
                st.rerun()
        st.write("**Aktuell:**", ", ".join(data["arbeiten"]) if data["arbeiten"] else "_leer_")

    st.divider()
    st.subheader("Feste Positionen")
    if data["mitarbeiter"] and data["arbeiten"]:
        pers = st.selectbox("Mitarbeiter:", ["-"] + data["mitarbeiter"])
        job = st.selectbox("Feste Arbeit:", ["-"] + data["arbeiten"])
        if pers != "-" and job != "-" and st.button("Fixierung setzen"):
            data["feste_positionen"][pers] = job
            save_data(data)
            st.success(f"{pers} dauerhaft auf {job} gesetzt")
            st.rerun()

    if data["feste_positionen"]:
        df_fix = pd.DataFrame(data["feste_positionen"].items(), columns=["Mitarbeiter", "Arbeit"])
        st.dataframe(df_fix, use_container_width=True, hide_index=True)
        if st.button("Alle Fixierungen loeschen"):
            data["feste_positionen"].clear()
            save_data(data)
            st.rerun()
    else:
        st.info("Keine festen Positionen.")

    st.divider()
    st.subheader("Mindest-Besetzung")
    if data["arbeiten"]:
        job_min = st.selectbox("Arbeit waehlen:", ["-"] + data["arbeiten"], key="min_job")
        anzahl_min = st.number_input("Mindestens benoetigte Personen:", min_value=1, max_value=10, step=1)
        if job_min != "-" and st.button("Speichern", key="save_min"):
            data["mindest_besetzung"][job_min] = anzahl_min
            save_data(data)
            st.success(f"Mindest-Besetzung fuer {job_min}: {anzahl_min}")
            st.rerun()

    if data["mindest_besetzung"]:
        df_min = pd.DataFrame(data["mindest_besetzung"].items(), columns=["Arbeit", "Min. Personen"])
        st.dataframe(df_min, use_container_width=True, hide_index=True)
        if st.button("Alle loeschen", key="del_min"):
            data["mindest_besetzung"].clear()
            save_data(data)
            st.rerun()
    else:
        st.info("Keine Mindestregelungen gesetzt.")

    st.divider()
    st.subheader("Maximal-Besetzung")
    if data["arbeiten"]:
        job_max = st.selectbox("Arbeit waehlen:", ["-"] + data["arbeiten"], key="max_job")
        anzahl_max = st.number_input("Maximal erlaubte Personen:", min_value=1, max_value=999, step=1, key="max_anzahl")
        if job_max != "-" and st.button("Speichern", key="save_max"):
            data["max_besetzung"][job_max] = anzahl_max
            save_data(data)
            st.success(f"Maximal-Besetzung fuer {job_max}: {anzahl_max}")
            st.rerun()

    if data["max_besetzung"]:
        df_max = pd.DataFrame(
            [(k, v if v != 999 else "unbegrenzt") for k, v in data["max_besetzung"].items()],
            columns=["Arbeit", "Max. Personen"]
        )
        st.dataframe(df_max, use_container_width=True, hide_index=True)
        if st.button("Alle loeschen", key="del_max"):
            data["max_besetzung"].clear()
            save_data(data)
            st.rerun()
    else:
        st.info("Keine Maximalregelungen gesetzt.")

# ------------------- STATISTIK -------------------
with tab3:
    st.header("Statistik der letzten 8 Wochen")

    if st.button("Alle Statistikdaten loeschen"):
        data["eintraege"] = []
        save_data(data)
        st.success("Alle Statistikdaten geloescht!")
        st.rerun()

    stats = statistik_wochen(8)
    if not stats:
        st.info("Noch keine Daten.")
    else:
        for person, daten in stats.items():
            if person in ["S3", "Teamlead"]:
                continue
            st.subheader(f"{person}")
            df = pd.DataFrame(list(daten.items()), columns=["Arbeit", "Anzahl"])
            st.bar_chart(df.set_index("Arbeit"))
            st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown("Betrachtungszeitraum: **8 Wochen**")
