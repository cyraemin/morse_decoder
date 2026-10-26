# MorseLab — Digital Communication Simulator

A web application that encodes, decodes and visualises International Morse Code. It is a **software simulation** of a digital decoder and does not control any physical hardware.

**Live app:** <https://morsedecoder-vacmxkhqiuahoqxa9s7sok.streamlit.app>

## Features

- **Decoder:** converts Morse to text (spaces between letters, `/` between words). Supports A–Z, 0–9 and common punctuation, and explains any invalid code.
- **Decode from an image:** upload a PNG or JPG (max 5 MB), press **Extract Morse**, then review and edit the result before decoding. Text you typed yourself is never overwritten without confirmation.
- **Interactive input:** Dot, Dash, Letter gap, Word gap, Undo and Clear buttons.
- **Encoder:** converts text to Morse code, with a copy button.
- **Signal visualiser:** HIGH/LOW waveform of any sequence.
- **Logic diagram and learning panel:** decoding pipeline, reference tables and examples.

## How it works

| Element | Signal | Duration |
|---|---|---|
| Dot / Dash | HIGH | 1 / 3 units |
| Gap within a letter | LOW | 1 unit |
| Gap between letters | LOW | 3 units |
| Gap between words | LOW | 7 units |

The decoder splits the input into words at `/` and letters at spaces, validates each code and looks it up in a single table (`CHAR_TO_MORSE`). The encoder uses the same table in reverse.

**Image reading** (`morse_image.py`) is a lightweight shape detector, not general OCR. It uses only Pillow and NumPy, runs offline, and:

1. separates the marks from the background;
2. classifies each mark as a dot, a dash or a `/` separator;
3. turns the gaps between marks into letter and word spacing;
4. validates the result with the same decoder.

## Digital electronics concepts

| Concept | In MorseLab |
|---|---|
| Digital signals | Two-level HIGH/LOW waveform |
| Counters / timing | Dot vs. dash and gap lengths |
| Shift register | Letters built one bit at a time (dot = 0, dash = 1) |
| ROM look-up table | Pattern → character mapping |

## Limitations

- Timing is ideal; input comes from typed or clicked symbols, not a real key.
- Image reading needs clear, printed or neatly drawn Morse code on a plain background. Always review the extracted sequence.
