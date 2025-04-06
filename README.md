# CV Adapter (V1)

Converts a PDF CV to an ATS-friendly PDF using JSON Resume standard with LLM parsing.

---

## Setup (Windows)

1. Clone the repository or create the folder:

```
mkdir cv_adapter
cd cv_adapter
```

2. Install dependencies:

```
pip install -r requirements.txt
```

If `pip` fails, use:

```
py -m pip install -r requirements.txt
```

3. Place your CV as `input_cv.pdf` in the root folder.

4. Run the pipeline:

```
py src/main.py
```

---

## Project Structure

```
cv_adapter/
├── src/
│   ├── cv_extraction.py
│   ├── cv_parser.py
│   ├── ats_generator.py
│   └── main.py
├── tests/
│   ├── test_extraction.py
│   ├── test_parser.py
│   └── test_generator.py
├── input_cv.pdf
├── PLANNING.md
├── TASK.md
├── README.md
└── requirements.txt
```

---

## Description

- **Input:** PDF CV (`input_cv.pdf`)
- **Extraction:** Extracts text using `pdfminer.six`
- **Parsing:** Converts text to JSON Resume format via LLM
- **Output:** Generates ATS-friendly PDF using `reportlab`

---

## Future Versions

- V2: Job description adaptation, Streamlit UI
- V3: Interactive agent-based editing
