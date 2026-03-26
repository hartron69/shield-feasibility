#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 22 01:33:14 2026

@author: haraldtronstad
"""

"""
barentswatch_c5ai_fetcher.py  v2.0
===================================
Henter luserapporter, sykdomshistorikk og lokalitetsdata
fra Barentswatch API og strukturerer til C5AI risk_forecast.json.

Endringer fra v1:
  - Sykdomsdata (ILA, PD, m.fl.) via v3-endepunkt
  - Oppdatert til v2 luse-API (nytt feltformat fra feb 2025)
  - Patogen-prior justeres dynamisk basert på faktiske sykdomstilfeller
  - Sykdomsstatus lagres separat i sykdom_historikk_{no}.json
  - Sammendrag inkluderer sykdomsflagg

Bruk:
    pip install requests pandas
    python barentswatch_c5ai_fetcher.py

Konfigurasjon:
    Sett CLIENT_SECRET nedenfor eller som miljøvariabel BW_CLIENT_SECRET.
"""

import os
import json
import math
import time
import datetime
from pathlib import Path
import requests
import pandas as pd

# ─── KONFIGURASJON ────────────────────────────────────────────────────────────
CLIENT_ID     = os.getenv("BW_CLIENT_ID",     "harald@fender.link:Shield Data Client")
CLIENT_SECRET = os.getenv("BW_CLIENT_SECRET", "")   # Set BW_CLIENT_SECRET env var

BASE_URL  = "https://www.barentswatch.no/bwapi"
TOKEN_URL = "https://id.barentswatch.no/connect/token"

# Output directory — override with BW_OUTPUT_DIR env var, defaults to cwd
OUTPUT_DIR = Path(os.getenv("BW_OUTPUT_DIR", "."))

# Lokaliteter — Kornstad Havbruk AS, Averøy, Møre og Romsdal
# Koordinater bekreftet fra oppdretter mars 2026
LOKALITETER = [
    {"localityNo": 12855, "name": "Kornstad", "lat": 62.960383, "lon": 7.45015},
    {"localityNo": 12870, "name": "Leite",    "lat": 63.03515,  "lon": 7.676817},
    {"localityNo": 12871, "name": "Hogsnes",  "lat": 63.093033, "lon": 7.675883},
]

# Nettverksparameter — C5AI PCC-brukermanual v2
NETWORK_RADIUS_KM = 50    # km-radius for smittespredning
NETWORK_DECAY     = 0.05  # eksponentiell avstand-decay per km

# Lusegrense (Mattilsynet)
LICE_THRESHOLD = 0.5

# Historikk
UKER_HISTORIKK  = 52
SYKDOM_ÅR_BAKOVER = 3   # henter sykdomsdata for siste N år


# ─── AUTENTISERING ────────────────────────────────────────────────────────────

def hent_token() -> str:
    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type":    "client_credentials",
            "scope":         "api",
        },
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise ValueError(f"Ingen token i svar: {resp.text}")
    print("✓ Token hentet")
    return token


# ─── API-HJELPERE ─────────────────────────────────────────────────────────────

def api_get(token: str, path: str, params: dict = None) -> dict | list:
    url = f"{BASE_URL}{path}"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def uke_liste(antall_uker: int) -> list[tuple[int, int]]:
    uker = []
    dato = datetime.date.today()
    for _ in range(antall_uker):
        iso = dato.isocalendar()
        uker.append((iso[0], iso[1]))
        dato -= datetime.timedelta(weeks=1)
    return list(reversed(uker))


# ─── LUSE-DATA (v2 API) ───────────────────────────────────────────────────────

def hent_luserapporter(token: str, locality_no: int, antall_uker: int = 52) -> pd.DataFrame:
    """
    Henter ukentlige luserapporter via v2-endepunkt.
    v2 bruker liceReport.adultFemaleLice.average i stedet for localityWeek.avgAdultFemaleLice.
    Faller tilbake til v1-feltnavn hvis v2-format ikke finnes.
    """
    rader = []
    for year, week in uke_liste(antall_uker):
        try:
            data = api_get(
                token,
                f"/v2/geodata/fishhealth/locality/{locality_no}/{year}/{week}"
            )

            # v2-format
            lr = data.get("liceReport", {})
            avg_female = (lr.get("adultFemaleLice") or {}).get("average")
            avg_mobile = (lr.get("mobileLice") or {}).get("average")
            avg_stat   = (lr.get("stationaryLice") or {}).get("average")
            sea_temp   = lr.get("seaTemperature")

            # Behandlinger v2
            lt = data.get("liceTreatments", {})
            har_behandling = bool(
                lt.get("medicinalTreatments") or
                lt.get("nonMedicinalTreatments") or
                lt.get("mechanicalRemovalTreatment") or
                lt.get("combinationTreatments") or
                lt.get("cleanerFishTreatment")
            )

            # Koordinater fra geometry hvis tilgjengelig
            geom = data.get("geometry", {})
            coords = geom.get("coordinates", [None, None]) if geom else [None, None]

            rader.append({
                "year":               year,
                "week":               week,
                "avgAdultFemaleLice": avg_female,
                "avgMobileLice":      avg_mobile,
                "avgStationaryLice":  avg_stat,
                "seaTemperature":     sea_temp,
                "hasTreatment":       har_behandling,
                "aboveThreshold":     (avg_female or 0) >= LICE_THRESHOLD,
                "lon_api":            coords[0] if len(coords) > 0 else None,
                "lat_api":            coords[1] if len(coords) > 1 else None,
            })

        except requests.HTTPError as e:
            if e.response.status_code in (404, 400):
                pass
            else:
                print(f"  Feil uke {year}w{week}: {e}")
        time.sleep(0.2)

    return pd.DataFrame(rader)


# ─── SYKDOMSDATA (v3 API) ─────────────────────────────────────────────────────

def hent_sykdomshistorikk(token: str, locality_no: int, år_bakover: int = 3) -> dict:
    """
    Henter sykdomstilfeller for lokalitet via v3-endepunkt.
    Dekker ILA, PD og alle listeførte sykdommer fra 2025.

    Returnerer dict med:
        alle_tilfeller  — komplett liste
        aktive          — ingen closureDate
        historiske_ant  — totalt antall registrerte tilfeller
        sykdomsnavn     — unike sykdomsnavn funnet
        patogen_prior   — justert prior til risk_forecast.json
        risiko_flagg    — AKTIV / HISTORISK / INGEN
    """
    nå = datetime.date.today()
    alle = []

    for year in range(nå.year - år_bakover, nå.year + 1):
        try:
            data = api_get(
                token,
                f"/v3/geodata/fishhealth/locality/{locality_no}/disease/{year}"
            )
            if isinstance(data, list):
                alle.extend(data)
            elif isinstance(data, dict) and "diseases" in data:
                alle.extend(data["diseases"])
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                pass   # ingen sykdom dette året
            else:
                print(f"    Sykdom-feil {year}: {e}")
        time.sleep(0.2)

    aktive = [
        s for s in alle
        if not s.get("closureDate") and s.get("status") != "CLOSED"
    ]

    sykdomsnavn = list({s.get("name", "ukjent") for s in alle if s.get("name")})

    # Patogen-prior: 0.10 baseline, +0.15 per aktivt tilfelle, max 0.70
    if aktive:
        prior = min(0.70, 0.10 + len(aktive) * 0.15)
        flagg = "AKTIV"
    elif alle:
        prior = min(0.25, 0.10 + len(alle) * 0.03)
        flagg = "HISTORISK"
    else:
        prior = 0.10
        flagg = "INGEN"

    return {
        "alle_tilfeller":  alle,
        "aktive":          aktive,
        "historiske_ant":  len(alle),
        "sykdomsnavn":     sykdomsnavn,
        "patogen_prior":   round(prior, 3),
        "risiko_flagg":    flagg,
    }


# ─── LOKALITETSOVERSIKT ───────────────────────────────────────────────────────

def hent_alle_lokaliteter(token: str) -> pd.DataFrame:
    data = api_get(token, "/v1/geodata/fishhealth/localities")
    rader = []
    for loc in data:
        rader.append({
            "localityNo": loc.get("localityNo"),
            "name":       loc.get("name"),
            "lat":        loc.get("latitude"),
            "lon":        loc.get("longitude"),
        })
    return pd.DataFrame(rader)


# ─── NETTVERKSMULTIPLIKATOR ───────────────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def beregn_nettverksmultiplikator(
    lokalitet: dict,
    alle_lok: pd.DataFrame,
    luse_status: dict[int, bool],
) -> float:
    """
    C5AI nettverksmultiplikator (PCC-brukermanual v2):
        1 + min(0.50, Σ nabovekter × 0.15)
        nabovekt = exp(-0.05 × avstand_km), kun for naboer OVER lusegrense
    """
    if lokalitet["lat"] is None or lokalitet["lon"] is None:
        return 1.0

    lat, lon = lokalitet["lat"], lokalitet["lon"]
    sum_vekter = 0.0

    for _, nabo in alle_lok.iterrows():
        if nabo["localityNo"] == lokalitet["localityNo"]:
            continue
        if pd.isna(nabo.get("lat")) or pd.isna(nabo.get("lon")):
            continue
        avstand = haversine_km(lat, lon, float(nabo["lat"]), float(nabo["lon"]))
        if avstand > NETWORK_RADIUS_KM:
            continue
        if not luse_status.get(int(nabo["localityNo"]), False):
            continue
        sum_vekter += math.exp(-NETWORK_DECAY * avstand)

    return round(1.0 + min(0.50, sum_vekter * 0.15), 4)


# ─── C5AI OUTPUT ──────────────────────────────────────────────────────────────

def lag_c5ai_input(
    lokalitet: dict,
    luse_df: pd.DataFrame,
    nettverksmultiplikator: float,
    sykdom: dict,
) -> dict:
    """
    Bygger risk_forecast.json kompatibelt med PCC Feasibility Tool v2.0.
    Patogen-domenet bruker nå faktisk sykdomshistorikk i stedet for fast prior.
    """
    # ── Lus ──
    if luse_df.empty:
        overskridelse_rate = 0.30
        snitt_lus = None
        trend = "ukjent"
    else:
        siste_8 = luse_df.tail(8)
        overskridelse_rate = float(siste_8["aboveThreshold"].mean())
        snitt_lus_raw = siste_8["avgAdultFemaleLice"].mean()
        snitt_lus = float(snitt_lus_raw) if pd.notna(snitt_lus_raw) else None

        if len(luse_df) >= 8:
            tidlig = luse_df.tail(8).head(4)["avgAdultFemaleLice"].mean()
            sen    = luse_df.tail(4)["avgAdultFemaleLice"].mean()
            if pd.notna(tidlig) and pd.notna(sen) and tidlig > 0:
                trend = ("stigende" if sen > tidlig * 1.1 else
                         "synkende" if sen < tidlig * 0.9 else "stabil")
            else:
                trend = "utilstrekkelig data"
        else:
            trend = "utilstrekkelig data"

    # ── Temperatur / HAB ──
    siste_temp = None
    if not luse_df.empty and "seaTemperature" in luse_df.columns:
        temps = luse_df["seaTemperature"].dropna()
        if not temps.empty:
            siste_temp = round(float(temps.iloc[-1]), 1)

    hab_temp_faktor = 1.0
    if siste_temp and siste_temp > 12:
        hab_temp_faktor = round(1.0 + (siste_temp - 12) * 0.05, 3)

    # ── Risikokomponenter ──
    lus_risiko     = min(1.0, overskridelse_rate * 1.5)
    hab_risiko     = 0.12 * hab_temp_faktor
    manet_risiko   = 0.08                          # fase 2 placeholder
    patogen_risiko = sykdom["patogen_prior"]        # ← nå faktisk data

    total_bio = (lus_risiko    * 0.40 +
                 hab_risiko    * 0.35 +
                 manet_risiko  * 0.10 +
                 patogen_risiko * 0.15)

    # Datakvalitet basert på antall uker med faktisk lusemåling
    rapporterte = int(luse_df["avgAdultFemaleLice"].notna().sum()) if not luse_df.empty else 0
    quality = ("SUFFICIENT" if rapporterte >= 24 else
               "LIMITED"    if rapporterte >= 12 else
               "POOR"       if rapporterte > 0 else
               "PRIOR_ONLY")

    return {
        "metadata": {
            "generated_at":    datetime.datetime.utcnow().isoformat() + "Z",
            "source":          "Barentswatch Fiskehelse API v2/v3",
            "model_version":   "c5ai-bw-v2.0",
            "locality_no":     lokalitet["localityNo"],
            "locality_name":   lokalitet["name"],
            "data_weeks":      len(luse_df),
            "reported_weeks":  rapporterte,
            "data_quality_flag": quality,
        },
        "lice": {
            "exceedance_rate_8w":  round(overskridelse_rate, 3),
            "avg_adult_female_8w": round(snitt_lus, 3) if snitt_lus else None,
            "trend":               trend,
            "threshold":           LICE_THRESHOLD,
            "network_multiplier":  nettverksmultiplikator,
        },
        "hab": {
            "sea_temperature_last":    siste_temp,
            "temperature_risk_factor": hab_temp_faktor,
            "prior_annual_prob":       0.12,
        },
        "jellyfish": {
            "prior_annual_prob": 0.08,
            "status":            "placeholder_fase2",
        },
        "pathogen": {
            "prior_annual_prob":   patogen_risiko,
            "risiko_flagg":        sykdom["risiko_flagg"],
            "aktive_tilfeller":    len(sykdom["aktive"]),
            "historiske_tilfeller": sykdom["historiske_ant"],
            "sykdomsnavn":         sykdom["sykdomsnavn"],
            "status":              "faktisk_data_v3",
        },
        "operator_aggregate": {
            "loss_breakdown_fractions": {
                "lice":     round(lus_risiko     * 0.40 / max(total_bio, 0.001), 3),
                "hab":      round(hab_risiko      * 0.35 / max(total_bio, 0.001), 3),
                "jellyfish": round(manet_risiko   * 0.10 / max(total_bio, 0.001), 3),
                "pathogen":  round(patogen_risiko * 0.15 / max(total_bio, 0.001), 3),
            },
            "total_bio_risk_index": round(total_bio, 4),
            "c5ai_vs_static_ratio": round(total_bio / 0.15, 4),
            "confidence_score":     0.75 if quality == "SUFFICIENT" else 0.45,
        },
    }


# ─── HOVEDPROGRAM ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Barentswatch → C5AI datafetcher  v2.0")
    print("=" * 60)

    token = hent_token()

    # ── Alle lokaliteter for nettverksanalyse ──
    print("\nHenter alle aktive lokaliteter for nettverksanalyse...")
    try:
        alle_lok_df = hent_alle_lokaliteter(token)
        print(f"✓ {len(alle_lok_df)} lokaliteter lastet")
    except Exception as e:
        print(f"  Advarsel: {e}")
        alle_lok_df = pd.DataFrame()

    for lok in LOKALITETER:
        print(f"  {lok['name']:<12} lat={lok['lat']}  lon={lok['lon']}")

    alle_resultater = []

    for lok in LOKALITETER:
        no   = lok["localityNo"]
        navn = lok["name"]
        print(f"\n{'─'*50}")
        print(f"  Lokalitet: {navn}  (nr. {no})")

        # ── Luserapporter ──
        print(f"  Henter {UKER_HISTORIKK} uker luserapporter (v2)...")
        luse_df = hent_luserapporter(token, no, UKER_HISTORIKK)
        rapporterte = int(luse_df["avgAdultFemaleLice"].notna().sum()) if not luse_df.empty else 0
        print(f"  ✓ {len(luse_df)} uker hentet, {rapporterte} med lusemåling")

        if not luse_df.empty:
            siste = luse_df.iloc[-1]
            lus_v = siste["avgAdultFemaleLice"]
            lus_s = f"{float(lus_v):.2f}" if pd.notna(lus_v) else "ikke rapportert"
            print(f"  Siste uke: {int(siste['year'])}w{int(siste['week'])} | "
                  f"Hunnlus: {lus_s} | "
                  f"Over grense: {'JA ⚠' if siste['aboveThreshold'] else 'nei'}")

        # ── Sykdomshistorikk ──
        print(f"  Henter sykdomshistorikk siste {SYKDOM_ÅR_BAKOVER} år (v3)...")
        sykdom = hent_sykdomshistorikk(token, no, SYKDOM_ÅR_BAKOVER)
        print(f"  ✓ {sykdom['historiske_ant']} tilfeller funnet | "
              f"Aktive: {len(sykdom['aktive'])} | "
              f"Flagg: {sykdom['risiko_flagg']} | "
              f"Prior: {sykdom['patogen_prior']}")
        if sykdom["aktive"]:
            for s in sykdom["aktive"]:
                print(f"    ⚠  {s.get('name','?')} | "
                      f"Status: {s.get('status','?')} | "
                      f"Mistenkt: {s.get('suspicionDate','?')} | "
                      f"Bekreftet: {s.get('diagnosisDate','?')}")

        # ── Nettverksmultiplikator ──
        if not alle_lok_df.empty and not luse_df.empty:
            luse_status = {no: bool(luse_df.iloc[-1]["aboveThreshold"])}
            mult = beregn_nettverksmultiplikator(lok, alle_lok_df, luse_status)
        else:
            mult = 1.0
        print(f"  Nettverksmultiplikator: {mult}")

        # ── Bygg og lagre risk_forecast.json ──
        c5ai = lag_c5ai_input(lok, luse_df, mult, sykdom)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        json_fil = OUTPUT_DIR / f"risk_forecast_{no}.json"
        with open(json_fil, "w", encoding="utf-8") as f:
            json.dump(c5ai, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Lagret: {json_fil}")

        # ── Lagre sykdomsdetaljer separat ──
        sykdom_fil = OUTPUT_DIR / f"sykdom_historikk_{no}.json"
        with open(sykdom_fil, "w", encoding="utf-8") as f:
            json.dump(sykdom, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Lagret: {sykdom_fil}")

        # ── Lagre luse-CSV ──
        if not luse_df.empty:
            csv_fil = OUTPUT_DIR / f"luse_historikk_{no}.csv"
            luse_df.to_csv(csv_fil, index=False)
            print(f"  ✓ Lagret: {csv_fil}")

        alle_resultater.append({
            "no":        no,
            "name":      navn,
            "scale":     c5ai["operator_aggregate"]["c5ai_vs_static_ratio"],
            "network":   mult,
            "quality":   c5ai["metadata"]["data_quality_flag"],
            "sykdom":    sykdom["risiko_flagg"],
            "patogen":   sykdom["patogen_prior"],
        })

    # ── Sammendrag ──
    print(f"\n{'='*60}")
    print("  SAMMENDRAG")
    print(f"{'='*60}")
    print(f"  {'Lokalitet':<14} {'Skala':>6}  {'Nettverk':>9}  "
          f"{'Sykdom':>10}  {'Patogen':>8}  Kvalitet")
    print(f"  {'─'*14} {'─'*6}  {'─'*9}  {'─'*10}  {'─'*8}  {'─'*9}")
    for r in alle_resultater:
        flagg = "⚠" if r["scale"] > 1.2 or r["sykdom"] == "AKTIV" else (
                "✓" if r["scale"] < 0.8 else "~")
        print(f"  {flagg} {r['name']:<12} "
              f"{r['scale']:>6.3f}  "
              f"{r['network']:>9.3f}  "
              f"{r['sykdom']:>10}  "
              f"{r['patogen']:>8.3f}  "
              f"[{r['quality']}]")

    print(f"\nFerdig. JSON-filer klare for PCC-verktøyet:")
    for r in alle_resultater:
        print(f'  c5ai_forecast_path: "risk_forecast_{r["no"]}.json"')


if __name__ == "__main__":
    main()