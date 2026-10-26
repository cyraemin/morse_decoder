"""MorseLab - Digital Communication Simulator (CSE-207 project).

Run from the repository root:  python -m streamlit run morselab/app.py
"""
import plotly.graph_objects as go
import streamlit as st

import morse_logic as ml

st.set_page_config(page_title="MorseLab", page_icon=":material/graphic_eq:", layout="wide")

# --------------------------------------------------------------------------
# Colours and light styling
# --------------------------------------------------------------------------
NAVY, MINT, PINK = "#1E2A4A", "#23877C", "#C2557A"   # mint/pink dark enough for white text

st.markdown(f"""
<style>
.block-container {{ padding-top: 1.6rem; max-width: 1400px; }}
h1, h2, h3 {{ color: {NAVY}; }}
div.ml-title {{ font-size: 2.1rem; font-weight: 700; color: {NAVY}; line-height: 1.1; margin: 0; }}
div.ml-sub {{ color: #5A6478; margin: 0; }}
.ml-status {{ display: inline-flex; align-items: center; gap: .5rem; float: right;
  border: 1px solid #D9E2DF; border-radius: 999px; padding: .35rem 1rem; background: white; }}
.ml-led {{ width: 11px; height: 11px; border-radius: 50%; display: inline-block; }}
div.ml-section {{ font-size: 1.25rem; font-weight: 700; color: {NAVY}; margin: 0; }}
div.ml-hint {{ color: #6B7385; font-size: .9rem; margin: 0 0 .6rem 0; }}
.ml-readout {{ background: #EEF5F3; border-radius: 10px; padding: .7rem 1rem; margin-bottom: .6rem;
  font-family: ui-monospace, Consolas, monospace; }}
.ml-block {{ display: flex; flex-wrap: wrap; align-items: center; column-gap: .8rem; row-gap: .15rem;
  border-radius: 10px; padding: .5rem .9rem; border: 1px solid rgba(30,42,74,.15); }}
.ml-block b {{ flex: 0 1 15rem; color: {NAVY}; font-size: .95rem; }}
.ml-block span {{ flex: 1 1 12rem; font-size: .85rem; color: #4F5870; }}
.ml-arrow {{ text-align: center; color: {NAVY}; line-height: 1.2; font-size: .9rem; }}
.st-key-dec_input input {{ font-family: ui-monospace, Consolas, monospace; letter-spacing: .05em; }}
.ml-ref {{ font-family: ui-monospace, Consolas, monospace; font-size: .9rem; line-height: 1.55; }}
.st-key-btn_dot button, .st-key-btn_dot button:hover, .st-key-btn_dot button:focus:not(:active) {{
  background: {MINT}; color: white; border-color: {MINT}; }}
.st-key-btn_dash button, .st-key-btn_dash button:hover, .st-key-btn_dash button:focus:not(:active) {{
  background: {PINK}; color: white; border-color: {PINK}; }}
.st-key-btn_dot button:hover, .st-key-btn_dash button:hover {{ filter: brightness(.95); }}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Session state (keeps values between button clicks)
# --------------------------------------------------------------------------
defaults = {"dec_input": "", "enc_input": "", "keypad": "", "viz_source": "Decoder input"}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


def load_example(text):
    """Example buttons: fill both inputs with the example and show it on the waveform."""
    st.session_state.dec_input = ml.encode(text).morse
    st.session_state.enc_input = text
    st.session_state.viz_source = "Decoder input"


def keypad(action, symbol=None):
    seq = st.session_state.keypad
    if action == "symbol":
        seq = ml.add_symbol(seq, symbol)
    elif action == "letter":
        seq = ml.end_letter(seq)
    elif action == "word":
        seq = ml.end_word(seq)
    elif action == "undo":
        seq = ml.undo(seq)
    elif action == "clear":
        seq = ""
    st.session_state.keypad = seq


def section(anchor, title, hint):
    st.markdown(f'<div id="{anchor}"></div><div class="ml-section">{title}</div>'
                f'<div class="ml-hint">{hint}</div>', unsafe_allow_html=True)


def md_escape(text):
    """Escape Markdown characters so user input like *ab* is shown exactly as typed."""
    return "".join("\\" + c if c in "\\`*_{}[]()#+-.!|<>~$" else c for c in text)


def show_errors(errors):
    for e in errors:
        st.error(md_escape(e))


# --------------------------------------------------------------------------
# Sidebar navigation
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### MorseLab")
    st.markdown("""
- [Home](#home)
- [Decode](#decoder)
- [Interactive input](#keypad)
- [Encode](#encoder)
- [Signal visualizer](#visualizer)
- [Logic diagram](#logic)
- [Reference](#reference)
""")
    st.divider()
    st.markdown("**About**")
    st.caption("CSE-207 Digital Electronics and Computer Organisation project. "
               "A software simulation of a digital Morse code decoder.")

# --------------------------------------------------------------------------
# Header with status LED
# --------------------------------------------------------------------------
st.markdown('<div id="home"></div>', unsafe_allow_html=True)
head_left, head_right = st.columns([4, 1])
with head_left:
    st.markdown('<div class="ml-title">MorseLab</div>'
                '<div class="ml-sub">Digital Communication Simulator</div>', unsafe_allow_html=True)
status_box = head_right.empty()


def set_status(label, colour):
    status_box.markdown(f'<div class="ml-status"><span class="ml-led" style="background:{colour}"></span>'
                        f'{label}</div>', unsafe_allow_html=True)


set_status("Processing", "#F2B544")
st.write("")

# --------------------------------------------------------------------------
# Compute all results from the current inputs
# --------------------------------------------------------------------------
dec = ml.decode(st.session_state.dec_input)
pad = ml.decode(st.session_state.keypad)
enc = ml.encode(st.session_state.enc_input)

left, right = st.columns([1, 1.25], gap="large")

# ============================== LEFT COLUMN ===============================
with left:
    # A. Decoder
    with st.container(border=True):
        section("decoder", "Morse Code Decoder", "Enter Morse code to decode it into text. "
                "Use spaces between letters and / between words.")
        with st.form("decode_form", border=False):
            st.text_input("Morse code", key="dec_input", label_visibility="collapsed",
                          placeholder="e.g.  .... . .-.. .-.. --- / .-- --- .-. .-.. -..")
            st.form_submit_button("Decode", type="primary", icon=":material/play_arrow:")
        if dec.text:
            st.caption("Decoded text (hover over the box to show the copy icon)")
            st.code(dec.text, language=None)
        show_errors(dec.errors)

    # B. Interactive input
    with st.container(border=True):
        section("keypad", "Interactive Morse Input", "Use the buttons to enter dots and dashes. "
                "Letter gap ends a letter; Word gap inserts /.")
        c1, c2, c3, c4 = st.columns(4)
        c1.button("Dot ( . )", key="btn_dot", on_click=keypad, args=("symbol", "."), width="stretch")
        c2.button("Dash ( - )", key="btn_dash", on_click=keypad, args=("symbol", "-"), width="stretch")
        c3.button("Letter gap", key="btn_letter", on_click=keypad, args=("letter",), width="stretch")
        c4.button("Word gap", key="btn_word", on_click=keypad, args=("word",), width="stretch")
        c5, c6, _, _ = st.columns(4)
        c5.button("Undo", key="btn_undo", on_click=keypad, args=("undo",),
                  icon=":material/undo:", width="stretch")
        c6.button("Clear", key="btn_clear", on_click=keypad, args=("clear",),
                  icon=":material/delete:", width="stretch")
        st.markdown(
            f'<div class="ml-readout">Current sequence:&nbsp; {st.session_state.keypad or "—"}<br>'
            f'Decoded:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; '
            f'{" ".join(pad.text) if pad.text else "—"}</div>', unsafe_allow_html=True)
        show_errors(pad.errors)

    # C. Encoder
    with st.container(border=True):
        section("encoder", "Text to Morse Encoder", "Enter text and get the Morse code.")
        with st.form("encode_form", border=False):
            st.text_input("Text", key="enc_input", label_visibility="collapsed",
                          placeholder="e.g. HELLO WORLD")
            st.form_submit_button("Encode", type="primary", icon=":material/play_arrow:")
        if enc.morse:
            st.caption("Morse code (hover over the box to show the copy icon)")
            st.code(enc.morse, language=None)
        if enc.unsupported:
            st.warning("Skipped characters with no Morse code: "
                       + md_escape(" ".join(repr(c) for c in enc.unsupported)))

# ============================== RIGHT COLUMN ==============================
with right:
    # D. Signal visualizer
    with st.container(border=True):
        section("visualizer", "Signal Visualizer",
                "Digital HIGH/LOW waveform of the selected Morse sequence "
                "(dot = 1 unit HIGH, dash = 3; gaps: 1 / 3 / 7 units LOW).")
        source = st.radio("Signal source", ["Decoder input", "Interactive input", "Encoder output"],
                          key="viz_source", horizontal=True, label_visibility="collapsed")
        morse_for_signal = {"Decoder input": st.session_state.dec_input,
                            "Interactive input": st.session_state.keypad,
                            "Encoder output": enc.morse}[source]
        sig = ml.to_signal(morse_for_signal)
        if sig.total_units == 0:
            st.info("No valid Morse sequence to draw yet. Enter or select one above.")
        else:
            xs = sig.times
            ys = sig.levels + [sig.levels[-1]]
            fig = go.Figure(go.Scatter(x=xs, y=ys, mode="lines", line_shape="hv",
                                       line=dict(color="#5EEAD4", width=2.5),
                                       hovertemplate="t = %{x} units<extra></extra>"))
            for start, end, ch in sig.letters:
                fig.add_annotation(x=(start + end) / 2, y=1.32, text=ch, showarrow=False,
                                   font=dict(color="#F8E9B0", size=13))
            fig.update_layout(
                height=250, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="#243352", plot_bgcolor="#243352", font=dict(color="#E6ECF5"),
                xaxis=dict(title="Time (units)", range=[0, sig.total_units], gridcolor="#33456A",
                           zeroline=False),
                yaxis=dict(tickvals=[0, 1], ticktext=["LOW", "HIGH"], range=[-0.25, 1.5],
                           gridcolor="#33456A", zeroline=False),
                showlegend=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            note = " · invalid letters are not drawn" if "?" in ml.decode(morse_for_signal).text else ""
            st.caption(f"Total length: {sig.total_units} units · characters drawn: {len(sig.letters)}{note}")

    # E. Logic diagram
    with st.container(border=True):
        section("logic", "Digital Logic Diagram",
                "Software simulation of the decoding process — not a physical circuit.")
        blocks = [
            ("Input", "Morse code from text box or keypad", "#FBE3EA"),
            ("Signal / Timing Interpretation", "Splits symbols, letter gaps (space) and word gaps (/)", "#E7E1F7"),
            ("Morse Decoder Logic", "Checks each code uses only dots and dashes", "#DDEBFA"),
            ("Character Mapping", "Look-up table: code → letter, digit or symbol", "#DDF3EC"),
            ("Output Display", "Shows decoded text and waveform", "#FCEBD7"),
        ]
        html = ""
        for i, (name, desc, colour) in enumerate(blocks):
            if i:
                html += '<div class="ml-arrow">↓</div>'
            html += f'<div class="ml-block" style="background:{colour}"><b>{name}</b><span>{desc}</span></div>'
        st.markdown(html, unsafe_allow_html=True)
        st.caption("Each block is a step in this program, not a physical component. For comparison, "
                   "a hardware decoder would use a counter to time HIGH/LOW durations, a shift register "
                   "to store dots (0) and dashes (1), and a ROM as the look-up table.")

    # F. Learning & reference
    with st.container(border=True):
        section("reference", "Learning & Reference", "Morse alphabet, examples and how decoding works.")
        tab_letters, tab_numbers, tab_examples, tab_how = st.tabs(
            ["Morse Alphabet", "Numbers & Punctuation", "Examples", "How It Works"])

        def ref_columns(chars, ncols):
            cols = st.columns(ncols)
            per_col = -(-len(chars) // ncols)
            for i, col in enumerate(cols):
                rows = [f"{c:<2} {ml.CHAR_TO_MORSE[c]}" for c in chars[i * per_col:(i + 1) * per_col]]
                col.markdown('<div class="ml-ref">' + "<br>".join(r.replace(" ", "&nbsp;") for r in rows)
                             + "</div>", unsafe_allow_html=True)

        with tab_letters:
            ref_columns(ml.LETTERS, 3)
        with tab_numbers:
            n1, n2 = st.columns([1, 2])
            with n1:
                ref_columns(ml.DIGITS, 1)
            with n2:
                ref_columns(ml.PUNCTUATION, 2)
        with tab_examples:
            st.caption("Click an example to load it into the decoder, encoder and waveform.")
            for example in ["SOS", "HELLO", "HELP", "HELLO WORLD", "CSE 207"]:
                e1, e2 = st.columns([1, 3])
                e1.button(example, key=f"ex_{example}", on_click=load_example, args=(example,),
                          width="stretch")
                e2.code(ml.encode(example).morse, language=None)
        with tab_how:
            st.markdown("""
**Morse code** sends each character as a pattern of short (dot) and long (dash) signals.
All timing is measured in *units*: a dot is 1 unit, a dash is 3 units, the gap inside a letter is 1 unit,
the gap between letters is 3 units and the gap between words is 7 units.

**Decoding algorithm used here**
1. Clean the input: remove extra spaces and accept look-alike symbols (•, –, _).
2. Split the sequence into words at every `/`.
3. Split each word into letter codes at the spaces.
4. Check that each code contains only `.` and `-`.
5. Look the code up in the Morse table. If it is not there, show `?` and an error message.
6. Join the letters into words and the words into the final text.

The encoder uses the **same table** in reverse, and the waveform is generated from the timing rules above.
""")
        st.caption("Quick info · Dot = 1 unit · Dash = 3 units · Symbol gap = 1 · Letter gap = 3 · Word gap = 7")

# --------------------------------------------------------------------------
# Final status LED
# --------------------------------------------------------------------------
if dec.errors or pad.errors:
    set_status("Error", "#E5484D")
else:
    set_status("Ready", MINT)
