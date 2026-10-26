"""Morse code decoder - ROM generator, clock-accurate behavioural model and figures.

Address of the decoder ROM:  A7..A5 = symbol count L,  A4..A0 = pattern
(pattern = Morse code read as binary, dot = 0, dash = 1, first symbol = MSB).
Two 2Kx8 EEPROMs (AT28C16) share the address; ROM_LO drives segments 0-7,
ROM_HI drives segments 8-14 (+DP) of a 14-segment display (active high).
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
}

# 14-segment font, bit order: A B C D E F G1 G2 H J K L M N DP (bit0..bit14)
SEG14 = {
    "0": 0x0C3F, "1": 0x0006, "2": 0x00DB, "3": 0x008F, "4": 0x00E6,
    "5": 0x2069, "6": 0x00FD, "7": 0x0007, "8": 0x00FF, "9": 0x00EF,
    "A": 0x00F7, "B": 0x128F, "C": 0x0039, "D": 0x120F, "E": 0x00F9,
    "F": 0x0071, "G": 0x00BD, "H": 0x00F6, "I": 0x1209, "J": 0x001E,
    "K": 0x2470, "L": 0x0038, "M": 0x0536, "N": 0x2136, "O": 0x003F,
    "P": 0x00F3, "Q": 0x203F, "R": 0x20F3, "S": 0x018D, "T": 0x1201,
    "U": 0x003E, "V": 0x0C30, "W": 0x2836, "X": 0x2D00, "Y": 0x1500,
    "Z": 0x0C09, "?": 0x1083, " ": 0x0000,
}


def address(code):
    pattern = int(code.replace(".", "0").replace("-", "1"), 2)
    return (len(code) << 5) | pattern


def build_rom():
    """Return 256-entry table of characters; unused codes show '?'."""
    rom = ["?"] * 256
    for addr in range(32):          # L = 0 never latched; keep blank
        rom[addr] = " "
    for ch, code in MORSE.items():
        rom[address(code)] = ch
    return rom


def write_hex(rom):
    lo = [SEG14[c] & 0xFF for c in rom]
    hi = [(SEG14[c] >> 8) & 0xFF for c in rom]
    for name, data in (("rom_lo.hex", lo), ("rom_hi.hex", hi)):
        with open(os.path.join(HERE, name), "w") as f:
            for base in range(0, 256, 16):
                f.write(f"{base:03X}: " + " ".join(f"{b:02X}" for b in data[base:base + 16]) + "\n")
    with open(os.path.join(HERE, "rom_table.csv"), "w") as f:
        f.write("char,morse,L,pattern_bin,address_hex,seg14_hex\n")
        for ch, code in MORSE.items():
            a = address(code)
            f.write(f"{ch},{code},{len(code)},{a & 31:05b},{a:02X},{SEG14[ch]:04X}\n")


# ---------------------------------------------------------------- simulation
TICKS_PER_UNIT = 4  # 555 clock = 4 ticks per Morse dot length


def key_waveform(text, jitter=None):
    """Ideal keying waveform (1 = key down), one sample per clock tick."""
    import random
    rnd = random.Random(7)
    def n(units):
        t = units * TICKS_PER_UNIT
        if jitter:
            t = max(1, t + rnd.randint(-jitter, jitter))
        return t
    wave = [0] * 6
    for w, word in enumerate(text.split(" ")):
        if w:
            wave += [0] * n(4)       # 3 already added + 4 = 7 units
        for c, ch in enumerate(word):
            if c:
                wave += [0] * n(2)   # 1 already added + 2 = 3 units
            for s, sym in enumerate(MORSE[ch]):
                wave += [1] * n(1 if sym == "." else 3)
                wave += [0] * n(1)
    return wave + [0] * 20


def simulate(wave, rom):
    """Clock-accurate model of the synchronous circuit (all regs update on clk edge)."""
    k1 = k2 = 0          # 74HC74 synchroniser
    mark = 0             # 74HC163 #1 (stops at 8)
    gap = 0              # 74HC163 #2 (stops at 8)
    gap_d = 0            # 74HC74 edge-detect FF
    end_d = 0            # 74HC74 delayed END -> clear
    shreg = 0            # 2 x 74HC194
    length = 0           # 74HC163 #3
    display = " "        # 2 x 74HC377
    out, trace = [], []
    for key in wave:
        # combinational signals from present state
        rel = (not k1) and k2
        dash = mark >> 3 & 1
        gap_q = gap >> 3 & 1
        end = gap_q and not gap_d and length != 0
        # next state
        n_mark = 0 if not (k1 or k2) else (mark + 1 if k1 and not dash else mark)
        n_gap = 0 if k1 else (gap + 1 if not gap_q else gap)
        n_shreg, n_len = shreg, length
        if end_d:
            n_shreg, n_len = 0, 0
        elif rel:
            n_shreg = ((shreg << 1) | dash) & 0xFF
            n_len = (length + 1) & 7
        if end:
            display = rom[(length << 5) | (shreg & 31)]
            out.append(display)
        trace.append(dict(key=key, k=k1, rel=int(rel), dash=dash, gapq=gap_q,
                          end=int(end), clr=end_d, L=length, disp=display))
        k2, k1 = k1, key
        mark, gap, shreg, length = n_mark, n_gap, n_shreg, n_len
        gap_d, end_d = gap_q, int(end)
    return "".join(out), trace


# ------------------------------------------------------------------- figures
def block_diagram(path):
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.set_xlim(0, 100); ax.set_ylim(0, 54); ax.axis("off")
    def box(x, y, w, h, title, sub):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4",
                                    fc="#eef3fb", ec="#1f3b6e", lw=1.4))
        ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center",
                fontsize=9.5, fontweight="bold", family="Times New Roman")
        ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center",
                fontsize=8, family="Times New Roman", color="#333")
    def arrow(x1, y1, x2, y2, label=None, lx=0, ly=1.4):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", lw=1.2, color="#222"))
        if label:
            ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, ha="center",
                    fontsize=7.5, family="Times New Roman", style="italic")
    box(1, 38, 15, 10, "Morse Key", "push button")
    box(22, 38, 17, 10, "Debounce &\nSynchroniser", "74HC14, 74HC74")
    box(1, 20, 15, 10, "Clock 40 Hz", "NE555 astable")
    box(46, 42, 18, 9, "Mark Timer", "74HC163 (dot/dash)")
    box(46, 29, 18, 9, "Gap Timer", "74HC163 (char end)")
    box(46, 15, 18, 9, "Control Logic", "74HC08/32/04, 74HC74")
    box(71, 42, 22, 9, "Symbol Shift Reg.", "2 x 74HC194 (5 bits)")
    box(71, 29, 22, 9, "Symbol Counter", "74HC163 (L, 3 bits)")
    box(71, 15, 22, 9, "Decoder ROM", "2 x AT28C16 EEPROM")
    box(71, 1, 22, 9, "Display Latch", "2 x 74HC377")
    box(40, 1, 22, 9, "14-Segment Display", "single character")
    box(22, 20, 17, 10, "Side-tone", "NE555 + buzzer")
    arrow(16, 43, 22, 43, "KEY")
    arrow(39, 45, 46, 46.5, "K")
    arrow(39, 41, 46, 33.5, "K")
    arrow(39, 39.5, 46, 21, "K, REL")
    arrow(30.5, 38, 30.5, 30, "K", lx=2, ly=0)
    arrow(8.5, 30, 8.5, 38, "CLK", lx=3, ly=0)
    arrow(64.4, 48, 70.6, 48, "DASH", ly=0.8)
    arrow(55, 28.6, 55, 24.4, "GAP", lx=2.5, ly=-0.6)
    # control bus: REL / CLR to shift register and counter, END to latch
    g = dict(color="#666", lw=1.1, ls="--")
    ax.plot([64.4, 67.5], [19.5, 19.5], **g)
    ax.plot([67.5, 67.5], [4, 44.5], **g)
    for y in (44.5, 31):
        ax.annotate("", xy=(70.6, y), xytext=(67.5, y), arrowprops=dict(arrowstyle="-|>", color="#666", lw=1.1))
    ax.annotate("", xy=(70.6, 4), xytext=(67.5, 4), arrowprops=dict(arrowstyle="-|>", color="#666", lw=1.1))
    ax.text(66.8, 36, "REL, CLR", fontsize=7.5, family="Times New Roman", style="italic", color="#444", rotation=90, ha="center")
    ax.text(66.8, 11, "END", fontsize=7.5, family="Times New Roman", style="italic", color="#444", rotation=90, ha="center")
    arrow(93.4, 46.5, 96.5, 46.5); ax.plot([96.5, 96.5], [46.5, 21], color="#222", lw=1.2)
    arrow(96.5, 21, 93.6, 21, "A4-A0", lx=-0.6, ly=-2.6)
    arrow(82, 28.6, 82, 24.4, "A7-A5", lx=4.5, ly=-0.6)
    arrow(82, 14.6, 82, 10.4, "D15-D0", lx=5, ly=-0.6)
    ax.plot([70.6, 69], [7, 7], color="#222", lw=1.2); ax.plot([69, 69], [7, 7], color="#222")
    arrow(70.6, 7, 62.4, 7, "segments", lx=-1.5, ly=-2.6)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def timing_diagram(trace, path):
    sigs = [("KEY", "key"), ("K (sync)", "k"), ("DASH", "dash"), ("REL", "rel"),
            ("GAP", "gapq"), ("END", "end"), ("CLR", "clr")]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    n = len(trace)
    for i, (label, key) in enumerate(sigs):
        y0 = (len(sigs) - i) * 1.5
        xs, ys = [], []
        for t, row in enumerate(trace):
            xs += [t, t + 1]; ys += [y0 + 0.9 * row[key]] * 2
        ax.plot(xs, ys, color="#1f3b6e", lw=1.3)
        ax.text(-1.5, y0 + 0.4, label, ha="right", va="center", fontsize=9, family="Times New Roman")
    y_l = 0.0
    prev = None
    for t, row in enumerate(trace):
        if row["L"] != prev:
            ax.text(t + 0.3, y_l + 0.4, str(row["L"]), fontsize=7.5, family="Times New Roman")
            ax.plot([t, t], [y_l, y_l + 0.9], color="#888", lw=0.8)
            prev = row["L"]
    ax.text(-1.5, y_l + 0.4, "L", ha="right", va="center", fontsize=9, family="Times New Roman")
    ax.set_xlim(-12, n); ax.set_ylim(-0.4, len(sigs) * 1.5 + 1.4)
    ax.set_yticks([]); ax.set_xticks(range(0, n + 1, 10)); ax.set_xlabel("clock ticks (40 Hz, 4 ticks = 1 dot unit)", family="Times New Roman")
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    rom = build_rom()
    write_hex(rom)
    tests = ["SOS", "HELLO WORLD", "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG", "0123456789"]
    for msg in tests:
        exp = msg.replace(" ", "")
        got, _ = simulate(key_waveform(msg), rom)
        got_j, _ = simulate(key_waveform(msg, jitter=1), rom)
        print(f"{msg!r:48} ideal={'PASS' if got == exp else 'FAIL ' + got}  "
              f"+/-1 tick jitter={'PASS' if got_j == exp else 'FAIL ' + got_j}")
    # timing diagram for letter "A"
    _, tr = simulate(key_waveform("A"), rom)
    timing_diagram(tr[:40], os.path.join(HERE, "fig_timing.png"))
    block_diagram(os.path.join(HERE, "fig_block.png"))
    print("A ->", f"{address('.-'):02X}", " SOS letters:", [f"{address(MORSE[c]):02X}" for c in "SO"])
