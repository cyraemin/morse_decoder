# MorseLab — Digital Communication Simulator

MorseLab is an interactive web application that encodes, decodes and visualises International Morse Code. It is a **software simulation** of a digital Morse code decoder, developed as the course project for **Digital Electronics and Computer Organisation (CSE-207)**.

**Live app:** <https://morsedecoder-vacmxkhqiuahoqxa9s7sok.streamlit.app>

The application reproduces the stages of a hardware decoder in software: signal timing, symbol separation, pattern storage and look-up-table decoding. It does not involve or control any physical hardware.

---

## Contents

1. [Features](#features)
2. [Quick start](#quick-start)
3. [Deployment](#deployment)
4. [How it works](#how-it-works)
5. [Digital electronics concepts demonstrated](#digital-electronics-concepts-demonstrated)
6. [Project structure](#project-structure)
7. [Testing](#testing)
8. [Limitations](#limitations)
9. [Future scope](#future-scope)

---

## Features

| Module | Description |
|---|---|
| **Morse decoder** | Converts Morse code to text. Letters are separated by spaces and words by `/`. Supports A–Z, 0–9 and common punctuation. Invalid codes are shown as `?` with a specific error message. |
| **Decode from an image** | Optional section in the decoder card. Upload a PNG or JPG (max 5 MB) of printed or neatly drawn Morse code, preview it and press **Extract Morse**. The extracted sequence is placed in the decoder box for review and editing before you press Decode. Text you typed yourself is never overwritten without confirmation. |
| **Interactive input** | Dot, Dash, Letter gap, Word gap, Undo and Clear buttons build a sequence that is decoded as you type. |
| **Text encoder** | Converts text of any case to Morse code and keeps word boundaries. Characters with no Morse code are reported. |
| **Signal visualiser** | Plots the HIGH/LOW waveform of the decoder input, the keypad sequence or the encoder output, with each character labelled. |
| **Logic diagram** | Shows the decoding pipeline: Input → Signal/Timing Interpretation → Morse Decoder Logic → Character Mapping → Output Display. |
| **Learning panel** | Reference tables, one-click example messages and an explanation of the decoding algorithm. |
| **Status indicator** | Shows *Ready* when all inputs are valid and *Error* when an invalid sequence is entered. |

Results can be copied with the copy icon that appears when you hover over an output box.

## Quick start

**Requirements:** Python 3.13 or 3.14 (both tested) and a modern web browser.

Run these commands from the repository root (the folder that contains `morselab/`):

```bash
python -m pip install -r requirements.txt
python -m streamlit run morselab/app.py
```

The application opens at <http://localhost:8501>. Running from the repository root applies the colour theme in `.streamlit/config.toml`. After installation, no internet connection is required.

## Deployment

The application is ready for [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Sign in at <https://share.streamlit.io> with the GitHub account that owns the repository.
2. Select **Create app**, then choose the repository, branch `main` and main file path `morselab/app.py`.
3. Under **Advanced settings**, select Python **3.13**.
4. Deploy. The dependencies are installed from `requirements.txt` in the repository root, which pins the versions that were tested.

The app needs no API keys, secrets, database or external services.

## How it works

### Timing rules

All durations are multiples of one *unit*, the length of a dot.

| Element | Signal level | Duration |
|---|---|---|
| Dot | HIGH | 1 unit |
| Dash | HIGH | 3 units |
| Gap between symbols of a letter | LOW | 1 unit |
| Gap between letters | LOW | 3 units |
| Gap between words | LOW | 7 units |

### Decoding algorithm

1. **Normalise:** remove surplus whitespace and accept look-alike symbols (`•`, `–`, `_`).
2. **Segment:** split the sequence into words at `/`, and each word into letter codes at spaces.
3. **Validate:** check that every code contains only `.` and `-`.
4. **Map:** look up each code in the Morse table. Unknown codes produce `?` and an error message.
5. **Output:** join the characters into words and the words into the final text.

### Reading Morse from an image

`morse_image.py` is a small shape detector, not general OCR. It uses only Pillow and NumPy, which are installed with Streamlit, and runs entirely offline:

1. Convert the image to greyscale and separate the marks from the background with an automatic (Otsu) threshold. Both dark-on-light and light-on-dark images work.
2. Find each connected mark and measure its width, height, fill and slope.
3. Classify each mark as a dot (round or square), a dash (wide) or a word separator (`/` or `|`).
4. Read the marks left to right and turn the gaps into symbol, letter or word spacing using the 1 / 3 / 7 unit rule.
5. Check the result with the same decoder used everywhere else in the app.

Blank, low-contrast, damaged or unsupported files, and images of ordinary text, produce a clear message instead of a guess.

### Single mapping table

Encoding and decoding use a single mapping table (`CHAR_TO_MORSE`), and the reverse table is derived from it automatically, so the two directions are always consistent. All results, including the examples, are computed at run time; none are hard-coded.

## Digital electronics concepts demonstrated

| Concept | How it appears in MorseLab |
|---|---|
| Digital signals | Each sequence is represented as a two-level (HIGH/LOW) waveform over time. |
| Timing and counters | Dots and dashes differ only in duration. Gap lengths distinguish symbols, letters and words, as a counter would in hardware. |
| Shift registers | A letter is built one binary symbol at a time (dot = 0, dash = 1). |
| ROM look-up tables | Character mapping works like memory: the dot/dash pattern is the address and the character is the stored data. |
| Error detection | Patterns that do not exist in the table are detected and reported, like unused ROM addresses. |
| Sequential control | The keypad moves between the states *within a letter*, *letter complete* and *word complete*. |

## Project structure

```
(repository root)
├── requirements.txt         Pinned dependencies (Streamlit, Plotly)
├── .streamlit/config.toml   Colour theme and upload size limit
└── morselab/
    ├── app.py               Streamlit user interface
    ├── morse_logic.py       Morse table, encoder, decoder, waveform timing, keypad logic
    ├── morse_image.py       Reads dots, dashes and separators from an uploaded image
    ├── test_morselab.py     Automated test suite
    └── README.md
```

## Testing

```bash
cd morselab
python -m unittest test_morselab -v
```

The suite contains 35 tests covering decoding, encoding, input validation, waveform timing, keypad behaviour and image extraction (drawn, printed, inverted and JPEG images, plus blank, blurred and damaged files). It also uses Streamlit's AppTest framework to click every button, submit both forms and compare the plotted waveform against the timing rules.

## Limitations

- MorseLab is a software simulation, not a physical circuit. Signal timing is ideal rather than measured from a real key.
- Input is entered as typed or clicked symbols, not by holding down a key for a measured duration.
- Prosigns (for example SK and AR) and non-Latin Morse alphabets are not supported.
- Image reading is designed for clear, printed or neatly drawn Morse code on a plain background. Handwriting with uneven spacing, tilted photos or cluttered images may be misread, so always review the extracted sequence before decoding.

## Future scope

- Measure real key-press durations and classify dots and dashes automatically, with adaptive speed.
- Add audio playback of Morse sequences and decoding from a microphone.
- Implement the same pipeline in hardware, on an FPGA or with 74-series logic ICs.
