"""Core Morse code logic for MorseLab.

Everything the app shows (decoded text, encoded text, waveform) is computed
here from ONE mapping table, so encoding and decoding always agree.

Morse text format used throughout:
    dots and dashes   .  -
    letter separator  one or more spaces
    word separator    /           e.g.  "... --- ... / .... .."
"""
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# 1. The single mapping table (ITU-R M.1677-1 International Morse Code)
# --------------------------------------------------------------------------
CHAR_TO_MORSE = {
    # letters
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    # digits
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    # common punctuation
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--",
    "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...",
    ";": "-.-.-.", "=": "-...-", "+": ".-.-.", "-": "-....-", "_": "..--.-",
    '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}

# Reverse table, built automatically from the one above (never typed by hand).
MORSE_TO_CHAR = {code: char for char, code in CHAR_TO_MORSE.items()}

LETTERS = [c for c in CHAR_TO_MORSE if c.isalpha()]
DIGITS = [c for c in CHAR_TO_MORSE if c.isdigit()]
PUNCTUATION = [c for c in CHAR_TO_MORSE if not c.isalnum()]

# Look-alike characters people often type or paste instead of . and -
_NORMALISE = str.maketrans({
    "·": ".", "•": ".", "∙": ".",          # middle dot, bullet
    "–": "-", "—": "-", "−": "-", "_": "-",  # en/em dash, minus
    "|": "/", "\\": "/",
})

# Timing rules, in units (1 unit = length of one dot)
DOT_UNITS = 1
DASH_UNITS = 3
SYMBOL_GAP = 1   # between dots/dashes of the same letter
LETTER_GAP = 3   # between letters
WORD_GAP = 7     # between words


# --------------------------------------------------------------------------
# 2. Decoder: Morse -> text
# --------------------------------------------------------------------------
@dataclass
class DecodeResult:
    text: str = ""
    errors: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors


def split_morse(morse):
    """Split Morse text into words, each a list of letter codes.

    Leading/trailing spaces, repeated spaces and empty words (e.g. "//")
    are ignored.
    """
    cleaned = morse.translate(_NORMALISE).strip()
    words = []
    for chunk in cleaned.split("/"):
        codes = chunk.split()
        if codes:
            words.append(codes)
    return words


def decode(morse):
    """Decode Morse text. Invalid letters become '?' and are listed in errors."""
    result = DecodeResult()
    if not morse or not morse.strip():
        return result

    out_words = []
    for w, codes in enumerate(split_morse(morse), start=1):
        word_text = ""
        for code in codes:
            bad = sorted(set(code) - {".", "-"})
            if bad:
                result.errors.append(
                    f"Word {w}: '{code}' contains {', '.join(repr(b) for b in bad)}. "
                    "Use only dots (.), dashes (-), spaces and /.")
                word_text += "?"
            elif code not in MORSE_TO_CHAR:
                result.errors.append(f"Word {w}: '{code}' is not a valid Morse character.")
                word_text += "?"
            else:
                word_text += MORSE_TO_CHAR[code]
        out_words.append(word_text)
    result.text = " ".join(out_words)
    return result


# --------------------------------------------------------------------------
# 3. Encoder: text -> Morse
# --------------------------------------------------------------------------
@dataclass
class EncodeResult:
    morse: str = ""
    unsupported: list = field(default_factory=list)   # characters that were skipped


def encode(text):
    """Encode text (any case) to Morse. Letters split by ' ', words by ' / '."""
    result = EncodeResult()
    words = []
    for word in text.upper().split():
        codes = []
        for ch in word:
            if ch in CHAR_TO_MORSE:
                codes.append(CHAR_TO_MORSE[ch])
            elif ch not in result.unsupported:
                result.unsupported.append(ch)
        if codes:
            words.append(" ".join(codes))
    result.morse = " / ".join(words)
    return result


# --------------------------------------------------------------------------
# 4. Digital signal: Morse -> HIGH/LOW timing
# --------------------------------------------------------------------------
@dataclass
class Signal:
    times: list      # step start times (units); last entry is the end time
    levels: list     # level (1 = HIGH, 0 = LOW) for each step
    letters: list    # (start, end, character) for labelling each letter
    total_units: int


def to_signal(morse):
    """Convert Morse text to a digital waveform using the standard timing rules.

    Invalid letters are skipped (the decoder reports them).
    """
    words = [[c for c in codes if c in MORSE_TO_CHAR] for codes in split_morse(morse)]
    words = [codes for codes in words if codes]

    steps, letters, t = [], [], 0
    def add(level, units):
        nonlocal t
        steps.append((t, level))
        t += units

    for w, codes in enumerate(words):
        if w:
            add(0, WORD_GAP)
        for i, code in enumerate(codes):
            if i:
                add(0, LETTER_GAP)
            start = t
            for j, sym in enumerate(code):
                if j:
                    add(0, SYMBOL_GAP)
                add(1, DOT_UNITS if sym == "." else DASH_UNITS)
            letters.append((start, t, MORSE_TO_CHAR[code]))

    times = [s[0] for s in steps] + [t]
    levels = [s[1] for s in steps]
    return Signal(times=times, levels=levels, letters=letters, total_units=t)


# --------------------------------------------------------------------------
# 5. Interactive keypad helpers (operate on a Morse string)
# --------------------------------------------------------------------------
def add_symbol(seq, symbol):
    return seq + symbol


def end_letter(seq):
    """Close the current letter (adds a space unless one is already there)."""
    if not seq.strip() or seq.endswith(" "):
        return seq
    return seq + " "


def end_word(seq):
    """Close the current word with ' / ' (ignored if the sequence is empty)."""
    stripped = seq.rstrip()
    if not stripped or stripped.endswith("/"):
        return seq
    return stripped + " / "


def undo(seq):
    """Remove the last action: a word separator, letter separator or symbol."""
    if seq.endswith(" / "):
        return seq[:-3]
    return seq[:-1]
