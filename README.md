# Morse Code Decoder — CSE-207 Project

Course project for **Digital Electronics and Computer Organisation (CSE-207)**. The project designs a digital Morse code decoder and implements it as an interactive software simulation.

| Folder | Contents |
|---|---|
| [`morselab/`](morselab) | **MorseLab**, a web application that encodes, decodes and visualises Morse code (Python, Streamlit, Plotly) |
| [`morse_decoder/`](morse_decoder) | Project report and hardware design data: a 74HC-series decoder with EEPROM look-up table |

## Run MorseLab locally

Run these commands from this folder (the repository root):

```bash
python -m pip install -r requirements.txt
python -m streamlit run morselab/app.py
```

The application opens at <http://localhost:8501>.

## Deploy on Streamlit Community Cloud

1. Sign in at <https://share.streamlit.io> with the GitHub account that owns this repository.
2. Select **Create app**, then **Deploy a public app from GitHub**.
3. Set **Repository** to `cyraemin/morse_decoder`, **Branch** to `main` and **Main file path** to `morselab/app.py`.
4. Under **Advanced settings**, select Python **3.13**, then click **Deploy**.

Dependencies are installed from `requirements.txt`, and the colour theme is read from `.streamlit/config.toml`. No secrets or external services are required.

See [`morselab/README.md`](morselab/README.md) for features, design and testing details.
