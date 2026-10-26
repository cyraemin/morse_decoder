# Morse Code Decoder — CSE-207 Project

Course project for **Digital Electronics and Computer Organisation (CSE-207)**: a digital Morse code decoder, designed in hardware and implemented as an interactive software simulation.

**Live app:** <https://morsedecoder-vacmxkhqiuahoqxa9s7sok.streamlit.app>

## Project structure

```
.
├── README.md
├── requirements.txt            Pinned dependencies (Streamlit, Plotly)
├── .streamlit/config.toml      Colour theme and 5 MB upload limit
├── morselab/                   MorseLab web application
│   ├── app.py                  User interface
│   ├── morse_logic.py          Morse table, encoder, decoder, signal timing
│   ├── morse_image.py          Reads Morse symbols from an uploaded image
│   ├── test_morselab.py        Automated tests
│   └── README.md               Features and how it works
└── morse_decoder/              Hardware design and report
    ├── Morse_Code_Decoder_Report.docx
    ├── morse_model.py          Circuit simulation and ROM generator
    ├── rom_lo.hex, rom_hi.hex  EEPROM contents
    ├── rom_table.csv           Character-to-address table
    └── README.md
```

## Run locally

From this folder:

```bash
python -m pip install -r requirements.txt
python -m streamlit run morselab/app.py
```

The app opens at <http://localhost:8501>. To run the tests:

```bash
cd morselab
python -m unittest test_morselab
```

## Deployment

The app is deployed on Streamlit Community Cloud from branch `main`, with main file `morselab/app.py`. Every push to `main` redeploys it automatically. No secrets or external services are required.
