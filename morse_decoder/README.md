# Morse Code Decoder — Project Report

Hardware design report for the CSE-207 Morse code decoder project. It describes a synchronous decoder built from 74HC-series counters, shift registers and an EEPROM look-up table driving a 14-segment display.

## Files

| File | Description |
|---|---|
| `Morse_Code_Decoder_Report.docx` | Project report (Times New Roman, 12 pt, 8 pages) |
| `morse_model.py` | Clock-accurate simulation of the circuit. It verifies the design and generates the ROM contents and the report figures. |
| `rom_lo.hex`, `rom_hi.hex` | Contents of the two AT28C16 EEPROMs (segments 0–7 and 8–15), as addresses 00h–FFh |
| `rom_table.csv` | Morse code, symbol count and ROM address for each of the 36 characters |

## Regenerating the data

```bash
python -m pip install matplotlib
python morse_model.py
```

The script runs the simulation tests, prints the results and rewrites the ROM files and figures in this folder.

The interactive software version of this project is in [`../morselab`](../morselab).
