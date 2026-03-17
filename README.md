# PDF Parser za stavke i podstavke

Ovaj projekt omogućuje parsiranje PDF računa u strukturirani JSON format te prikaz podataka u tabličnom obliku putem jednostavnog web sučelja.

Parser je prilagođen za realne PDF dokumente (s mogućim nepravilnostima u formatu) i podržava stavke i podstavke.

---

## 🔧 Funkcionalnosti

- Parsiranje PDF računa u JSON
- Podrška za:
  - stavke i podstavke
  - nedostajuće pozicije (npr. "Sitan materijal")
- Prikaz podataka u:
  - JSON formatu
  - tabličnom formatu (Streamlit)
- Export:
  - JSON
  - CSV

---

## 📦 Što parser vraća

Za svaku stavku:

- `pozicija`
- `naziv`
- `kolicina`
- `jed_mj`
- `cijena`
- `vrijednost`
- `rabat`
- `stopa_pdv`
- `porezna_osnovica`
- `podstavke` (lista)

Podstavke su ugniježđene unutar svoje glavne stavke.

---

## ⚙️ Instalacija

```bash
pip install -r requirements.txt
```

ili ručno:

```bash
pip install pypdf pandas streamlit
```

---

## 🖥️ CLI korištenje (parser.py)

Pokretanje parsera kroz terminal:

```bash
python parser.py
```

Zatim uneseš naziv PDF datoteke (npr. `ivan.pdf`).

Rezultat:
- generira se `.json` datoteka
- ispisuje se JSON u terminalu

---

## 🌐 Web sučelje (Streamlit)

Pokretanje aplikacije:

```bash
streamlit run parser.py
```

Nakon toga:

1. Otvori se web sučelje  
2. Učitaš PDF dokument  
3. Dobiješ:
   - JSON prikaz  
   - tablični prikaz  
4. Možeš preuzeti JSON ili CSV datoteku  

---

## 📊 Primjer izlaza

```json
{
  "pozicija": null,
  "naziv": "Sitan materijal",
  "kolicina": "1,00",
  "jed_mj": "kom",
  "cijena": "19,21",
  "vrijednost": "19,21",
  "rabat": null,
  "stopa_pdv": "#6",
  "porezna_osnovica": "19,21"
}
```

---

## ⚠️ Napomene

- Parser radi na temelju tekstualnog sadržaja PDF-a  
- Ne podržava skenirane dokumente (slike)  
- Očekuje da PDF sadrži tablicu s osnovnim stupcima (npr. "Pozicija", "Naziv")  

---