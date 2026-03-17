import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from pypdf import PdfReader

st.set_page_config(page_title="PDF Parser", layout="wide")
st.title("PDF Parser")
st.write("Učitaj PDF dokument i aplikacija će pokušati izvući stavke i podstavke, prikazati ih kao JSON i u tabličnom formatu.")


# --------------------------------------------------
# PARSER LOGIC
# --------------------------------------------------

def normalize_line(line: str) -> str:
    return line.replace("\xa0", " ").strip()


def canonical(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^a-z0-9čćžšđ]", "", text)
    return text


def is_code_token(token: str) -> bool:
    return bool(re.match(r"^[A-Z0-9()/.:-]+$", token))


def split_head(head: str):
    tokens = head.split()

    pos_tokens = []
    i = 0

    while i < len(tokens) and is_code_token(tokens[i]):
        pos_tokens.append(tokens[i])
        i += 1

    if not pos_tokens:
        return None, head.strip()

    pozicija = " ".join(pos_tokens).strip()
    naziv = " ".join(tokens[i:]).strip()

    return pozicija, naziv


MAIN_LINE_RE = re.compile(
    r"^(?P<head>.+?)\s+"
    r"(?P<kolicina>\d+,\d+)\s+"
    r"(?P<jed_mj>\w+)\s+"
    r"(?P<cijena>\d+,\d+)\s+"
    r"(?P<vrijednost>\d+,\d+)\s+"
    r"(?:(?P<rabat>\d+,\d+)\s+)?"
    r"(?P<stopa_pdv>#\d+)\s+"
    r"(?P<porezna_osnovica>\d+,\d+)$"
)

SUB_LINE_RE = re.compile(
    r"^(?P<head>.+?)\s+"
    r"(?P<kolicina>\d+,\d+)\s+"
    r"(?P<jed_mj>\w+)$"
)


def read_pdf_lines_from_upload(uploaded_file) -> list[str]:
    reader = PdfReader(uploaded_file)
    lines = []

    for page in reader.pages:
        text = page.extract_text() or ""

        for raw in text.splitlines():
            line = normalize_line(raw)
            if line:
                lines.append(line)

    return lines


def validate_pdf_structure(lines: list[str]) -> None:
    joined = "\n".join(lines)
    c = canonical(joined)

    if "pozicija" not in c or "naziv" not in c:
        raise ValueError(
            "PDF nema očekivanu tablicu stavki. Nisu pronađeni osnovni stupci 'Pozicija' i 'Naziv'."
        )


def extract_table_lines_from_upload(uploaded_file) -> list[str]:
    all_lines = read_pdf_lines_from_upload(uploaded_file)
    validate_pdf_structure(all_lines)

    lines = []
    in_table = False

    for line in all_lines:
        c = canonical(line)

        if "pozicija" in c and "naziv" in c:
            in_table = True
            continue

        if not in_table:
            continue

        if "rekapitulacijaporeza" in c or "ukupnoeur" in c:
            break

        if c in {
            "jedmj",
            "cijenavrijednostkolxcij",
            "rabatstopa",
            "pdva",
            "porezna",
            "osnovica",
            "kolicinajedmjcijenavrijednostrabatstopapdvaporeznaosnovica",
        }:
            continue

        lines.append(line)

    if not lines:
        raise ValueError("Tablica je pronađena, ali nijedan red nije izdvojen.")

    return lines


def parse_line(line: str):
    m = MAIN_LINE_RE.match(line)

    if m:
        pozicija, naziv = split_head(m.group("head"))

        return {
            "type": "stavka",
            "pozicija": pozicija,
            "naziv": naziv,
            "kolicina": m.group("kolicina"),
            "jed_mj": m.group("jed_mj"),
            "cijena": m.group("cijena"),
            "vrijednost": m.group("vrijednost"),
            "rabat": m.group("rabat"),
            "stopa_pdv": m.group("stopa_pdv"),
            "porezna_osnovica": m.group("porezna_osnovica"),
        }

    m = SUB_LINE_RE.match(line)

    if m:
        pozicija, naziv = split_head(m.group("head"))

        return {
            "type": "podstavka",
            "pozicija": pozicija,
            "naziv": naziv,
            "kolicina": m.group("kolicina"),
            "jed_mj": m.group("jed_mj"),
            "cijena": None,
            "vrijednost": None,
            "rabat": None,
            "stopa_pdv": None,
            "porezna_osnovica": None,
        }

    return None


def parse_uploaded_pdf(uploaded_file) -> dict:
    lines = extract_table_lines_from_upload(uploaded_file)

    stavke = []
    neparsirani_redovi = []
    current_item = None

    for line in lines:
        parsed = parse_line(line)

        if parsed is None:
            neparsirani_redovi.append(line)
            continue

        if parsed["type"] == "stavka":
            parsed.pop("type")
            parsed["podstavke"] = []
            stavke.append(parsed)
            current_item = parsed
        else:
            parsed.pop("type")

            if current_item is None:
                raise ValueError("Podstavka je pronađena prije glavne stavke.")

            current_item["podstavke"].append(parsed)

    if not stavke:
        raise ValueError(
            "Nijedna stavka nije uspješno parsirana. PDF možda nema očekivani raspored stupaca."
        )

    return {
        "stavke": stavke,
        "neparsirani_redovi": neparsirani_redovi
    }


# --------------------------------------------------
# TABLE PREP
# --------------------------------------------------

def flatten_for_table(parsed_json: dict) -> list[dict]:
    rows = []

    for stavka in parsed_json["stavke"]:
        rows.append({
            "tip": "stavka",
            "pozicija": stavka.get("pozicija"),
            "naziv": stavka.get("naziv"),
            "kolicina": stavka.get("kolicina"),
            "jed_mj": stavka.get("jed_mj"),
            "cijena": stavka.get("cijena"),
            "vrijednost": stavka.get("vrijednost"),
            "rabat": stavka.get("rabat"),
            "stopa_pdv": stavka.get("stopa_pdv"),
            "porezna_osnovica": stavka.get("porezna_osnovica"),
        })

        for podstavka in stavka.get("podstavke", []):
            rows.append({
                "tip": "podstavka",
                "pozicija": podstavka.get("pozicija"),
                "naziv": f"↳ {podstavka.get('naziv')}",
                "kolicina": podstavka.get("kolicina"),
                "jed_mj": podstavka.get("jed_mj"),
                "cijena": podstavka.get("cijena"),
                "vrijednost": podstavka.get("vrijednost"),
                "rabat": podstavka.get("rabat"),
                "stopa_pdv": podstavka.get("stopa_pdv"),
                "porezna_osnovica": podstavka.get("porezna_osnovica"),
            })

    return rows


# --------------------------------------------------
# UI
# --------------------------------------------------

uploaded_file = st.file_uploader("Učitaj PDF dokument", type=["pdf"])

if uploaded_file is None:
    st.info("Za početak učitaj PDF dokument.")
else:
    try:
        parsed = parse_uploaded_pdf(uploaded_file)

        st.success("PDF je uspješno obrađen.")

        json_string = json.dumps(parsed, ensure_ascii=False, indent=2)
        rows = flatten_for_table(parsed)
        df = pd.DataFrame(rows)

        st.subheader("JSON prikaz")
        st.code(json_string, language="json")

        st.subheader("Tablični prikaz")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            label="Preuzmi JSON datoteku",
            data=json_string.encode("utf-8"),
            file_name=Path(uploaded_file.name).with_suffix(".json").name,
            mime="application/json",
        )

        if parsed.get("neparsirani_redovi"):
            with st.expander("Neparsirani redovi"):
                for line in parsed["neparsirani_redovi"]:
                    st.write(line)

    except Exception as e:
        st.error(f"Greška: {e}")