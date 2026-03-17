import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from pypdf import PdfReader

st.set_page_config(page_title="PDF Parser", layout="wide")
st.title("PDF Parser")
st.write("Učitaj PDF dokument i aplikacija će pokušati izvući stavke i podstavke.")


# --------------------------------------------------
# BASIC HELPERS
# --------------------------------------------------

def normalize_line(line: str) -> str:
    return line.replace("\xa0", " ").strip()


def is_code_token(token: str) -> bool:
    # fleksibilnije – mora imati broj i biti uppercase-ish
    return any(c.isdigit() for c in token)


def split_head(head: str):
    tokens = head.split()

    pos_tokens = []
    naziv_tokens = []

    i = 0

    # uzmi sve dok ima broj ili izgleda kao kod
    while i < len(tokens):
        t = tokens[i]

        # ako ima broj → dio pozicije
        if any(c.isdigit() for c in t):
            pos_tokens.append(t)

        # ako je 1 slovo (npr. N, G, itd.) → također dio pozicije
        elif len(t) == 1 and t.isalpha():
            pos_tokens.append(t)

        else:
            break

        i += 1

    naziv_tokens = tokens[i:]

    pozicija = " ".join(pos_tokens) if pos_tokens else None
    naziv = " ".join(naziv_tokens)

    return pozicija, naziv


# --------------------------------------------------
# PDF READING
# --------------------------------------------------

def read_pdf_lines(uploaded_file):
    reader = PdfReader(uploaded_file)
    lines = []

    for page in reader.pages:
        text = page.extract_text() or ""

        for raw in text.splitlines():
            line = normalize_line(raw)
            if line:
                lines.append(line)

    return lines


# --------------------------------------------------
# MERGE BROKEN LINES (KEY FIX)
# --------------------------------------------------

def merge_lines(lines):
    merged = []
    buffer = ""

    for line in lines:
        # nova stavka ako počinje s (01) ili kodom
        if re.match(r"^\(?\d{2}\)?", line):
            if buffer:
                merged.append(buffer.strip())
            buffer = line
        else:
            buffer += " " + line

    if buffer:
        merged.append(buffer.strip())

    return merged


# --------------------------------------------------
# PARSING
# --------------------------------------------------

MAIN_RE = re.compile(
    r"^(?P<head>.+?)\s+"
    r"(?P<kolicina>\d+,\d+)\s+"
    r"(?P<jed_mj>\w+)\s+"
    r"(?P<cijena>\d+,\d+)\s+"
    r"(?P<vrijednost>\d+,\d+)"
)

SUB_RE = re.compile(
    r"^(?P<head>.+?)\s+"
    r"(?P<kolicina>\d+,\d+)\s+"
    r"(?P<jed_mj>\w+)$"
)


def parse_line(line):
    m = MAIN_RE.match(line)

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
        }

    m = SUB_RE.match(line)

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
        }

    return None


# --------------------------------------------------
# MAIN PARSER
# --------------------------------------------------

def parse_pdf(uploaded_file):
    lines = read_pdf_lines(uploaded_file)
    lines = merge_lines(lines)

    stavke = []
    current = None
    neparsirani = []

    for line in lines:
        parsed = parse_line(line)

        if not parsed:
            neparsirani.append(line)
            continue

        if parsed["type"] == "stavka":
            parsed.pop("type")
            parsed["podstavke"] = []
            stavke.append(parsed)
            current = parsed

        else:
            parsed.pop("type")

            if current:
                current["podstavke"].append(parsed)

    return {
        "stavke": stavke,
        "neparsirani_redovi": neparsirani
    }


# --------------------------------------------------
# TABLE VIEW
# --------------------------------------------------

def flatten(parsed):
    rows = []

    for s in parsed["stavke"]:
        rows.append({
            "tip": "stavka",
            "pozicija": s["pozicija"],
            "naziv": s["naziv"],
            "kolicina": s["kolicina"],
            "jed_mj": s["jed_mj"],
            "cijena": s["cijena"],
            "vrijednost": s["vrijednost"],
        })

        for p in s["podstavke"]:
            rows.append({
                "tip": "podstavka",
                "pozicija": p["pozicija"],
                "naziv": "↳ " + p["naziv"],
                "kolicina": p["kolicina"],
                "jed_mj": p["jed_mj"],
                "cijena": p["cijena"],
                "vrijednost": p["vrijednost"],
            })

    return rows


# --------------------------------------------------
# UI
# --------------------------------------------------

uploaded_file = st.file_uploader("Učitaj PDF", type=["pdf"])

if uploaded_file:
    try:
        parsed = parse_pdf(uploaded_file)

        st.success("Parsiranje gotovo")

        json_str = json.dumps(parsed, ensure_ascii=False, indent=2)
        df = pd.DataFrame(flatten(parsed))

        st.subheader("JSON")
        st.code(json_str, language="json")

        st.subheader("Tablica")
        st.dataframe(df, use_container_width=True)

        if parsed["neparsirani_redovi"]:
            with st.expander("Neparsirani redovi"):
                for l in parsed["neparsirani_redovi"]:
                    st.write(l)

    except Exception as e:
        st.error(str(e))