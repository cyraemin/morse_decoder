"""Tests for MorseLab.  Run:  python -m unittest test_morselab -v"""
import json
import os
import unittest

import morse_logic as ml

HERE = os.path.dirname(os.path.abspath(__file__))


class TestDecoder(unittest.TestCase):
    def test_sos(self):
        self.assertEqual(ml.decode("... --- ...").text, "SOS")

    def test_hello_world(self):
        r = ml.decode(".... . .-.. .-.. --- / .-- --- .-. .-.. -..")
        self.assertEqual(r.text, "HELLO WORLD")
        self.assertTrue(r.ok)

    def test_digits(self):
        morse = ".---- ..--- ...-- ....- ..... -.... --... ---.. ----. -----"
        self.assertEqual(ml.decode(morse).text, "1234567890")

    def test_whitespace_and_extra_separators(self):
        self.assertEqual(ml.decode("   ...   ---  ...  ").text, "SOS")
        self.assertEqual(ml.decode("/ .- // -... /").text, "A B")
        self.assertEqual(ml.decode(".-/-...").text, "A B")

    def test_lookalike_symbols(self):
        self.assertEqual(ml.decode("••• ––– •••").text, "SOS")

    def test_invalid_sequence(self):
        r = ml.decode("... -------- ...")
        self.assertEqual(r.text, "S?S")
        self.assertFalse(r.ok)
        self.assertIn("not a valid Morse character", r.errors[0])

    def test_invalid_characters(self):
        r = ml.decode("... abc")
        self.assertEqual(r.text, "S?")
        self.assertIn("contains", r.errors[0])

    def test_empty(self):
        for s in ("", "   ", "/"):
            r = ml.decode(s)
            self.assertEqual(r.text, "")
            self.assertTrue(r.ok)

    def test_punctuation(self):
        self.assertEqual(ml.decode(".-.-.- --..-- ..--..").text, ".,?")


class TestEncoder(unittest.TestCase):
    def test_lowercase_and_words(self):
        self.assertEqual(ml.encode("  hello   world ").morse,
                         ".... . .-.. .-.. --- / .-- --- .-. .-.. -..")

    def test_unsupported(self):
        r = ml.encode("A#B")
        self.assertEqual(r.morse, ".- -...")
        self.assertEqual(r.unsupported, ["#"])

    def test_round_trip_every_character(self):
        text = "".join(ml.CHAR_TO_MORSE)
        self.assertEqual(ml.decode(ml.encode(text).morse).text, text)

    def test_table_has_no_duplicate_codes(self):
        self.assertEqual(len(ml.MORSE_TO_CHAR), len(ml.CHAR_TO_MORSE))


class TestSignal(unittest.TestCase):
    def durations(self, morse):
        s = ml.to_signal(morse)
        return [(lvl, s.times[i + 1] - s.times[i]) for i, lvl in enumerate(s.levels)], s.total_units

    def test_sos_timing(self):
        steps, total = self.durations("... --- ...")
        expected = ([(1, 1), (0, 1)] * 2 + [(1, 1), (0, 3)]
                    + [(1, 3), (0, 1)] * 2 + [(1, 3), (0, 3)]
                    + [(1, 1), (0, 1)] * 2 + [(1, 1)])
        self.assertEqual(steps, expected)
        self.assertEqual(total, 27)

    def test_word_gap_is_7(self):
        steps, total = self.durations(". / .")
        self.assertEqual(steps, [(1, 1), (0, 7), (1, 1)])
        self.assertEqual(total, 9)

    def test_all_five_timing_rules(self):
        # "AM / E": dot, dash, symbol gap, letter gap and word gap all appear
        steps, total = self.durations(".- -- / .")
        self.assertEqual(steps, [(1, 1), (0, 1), (1, 3),      # A: dot, 1-unit gap, dash
                                 (0, 3),                      # letter gap
                                 (1, 3), (0, 1), (1, 3),      # M: dash, gap, dash
                                 (0, 7),                      # word gap
                                 (1, 1)])                     # E: dot
        self.assertEqual(total, 23)

    def test_letter_labels(self):
        s = ml.to_signal(".- / -")
        self.assertEqual([l[2] for l in s.letters], ["A", "T"])

    def test_empty_and_invalid(self):
        self.assertEqual(ml.to_signal("").total_units, 0)
        self.assertEqual(ml.to_signal("-------- xyz").total_units, 0)


class TestKeypad(unittest.TestCase):
    def test_sequence_building_and_undo(self):
        seq = ""
        for action in [".", ".", ".", "L", "-", "-", "-", "W", ".", "-"]:
            if action == "L":
                seq = ml.end_letter(seq)
            elif action == "W":
                seq = ml.end_word(seq)
            else:
                seq = ml.add_symbol(seq, action)
        self.assertEqual(seq, "... --- / .-")
        self.assertEqual(ml.decode(seq).text, "SO A")
        seq = ml.undo(ml.undo(seq))
        self.assertEqual(seq, "... --- / ")
        self.assertEqual(ml.undo(seq), "... ---")

    def test_separators_ignored_when_empty_or_repeated(self):
        self.assertEqual(ml.end_letter(""), "")
        self.assertEqual(ml.end_word(""), "")
        self.assertEqual(ml.end_word(ml.end_word(".")), ". / ")
        self.assertEqual(ml.end_letter(". "), ". ")
        self.assertEqual(ml.undo(""), "")


class TestImageExtraction(unittest.TestCase):
    """Generates Morse images with Pillow and checks the extractor reads them."""

    @staticmethod
    def drawn(text, d=12, invert=False):
        from PIL import Image, ImageDraw
        morse = ml.encode(text).morse
        width = 40 + sum({".": 2 * d, "-": 4 * d, " ": 2 * d, "/": 8 * d}[c] for c in morse)
        fg, bg = ("white", "black") if invert else ("black", "white")
        img = Image.new("RGB", (width, 6 * d), bg)
        draw, x, y = ImageDraw.Draw(img), 20, 3 * d
        for w, word in enumerate(morse.split(" / ")):
            if w:
                draw.line([(x + 2 * d, y + 2 * d), (x + 4 * d, y - 2 * d)], fill=fg, width=max(2, d // 3))
                x += 7 * d
            for i, code in enumerate(word.split(" ")):
                x += 2 * d if i else 0
                for j, sym in enumerate(code):
                    x += d if j else 0
                    length = d if sym == "." else 3 * d
                    shape = draw.ellipse if sym == "." else draw.rectangle
                    shape([x, y - d // 2, x + length, y + d // 2], fill=fg)
                    x += length
        return img

    @staticmethod
    def as_bytes(img, fmt="PNG", **options):
        import io
        buf = io.BytesIO()
        img.save(buf, fmt, **options)
        return buf.getvalue()

    def decoded(self, data):
        import morse_image as mi
        return ml.decode(mi.extract_morse(data).morse).text

    def test_drawn_images(self):
        for text in ["SOS", "HELLO WORLD", "CSE 207"]:
            self.assertEqual(self.decoded(self.as_bytes(self.drawn(text))), text)
            self.assertEqual(self.decoded(self.as_bytes(self.drawn(text, invert=True))), text)
            self.assertEqual(self.decoded(self.as_bytes(self.drawn(text, d=6), "JPEG", quality=60)), text)

    def test_printed_text(self):
        from PIL import Image, ImageDraw, ImageFont
        morse = ml.encode("HELLO WORLD").morse
        font = ImageFont.load_default(size=48)
        img = Image.new("RGB", (int(font.getlength(morse)) + 60, 96), "white")
        ImageDraw.Draw(img).text((30, 24), morse, fill="black", font=font)
        self.assertEqual(self.decoded(self.as_bytes(img)), "HELLO WORLD")

    def test_bad_inputs_give_messages(self):
        import morse_image as mi
        from PIL import Image, ImageFilter
        cases = [b"", b"not an image", self.as_bytes(Image.new("RGB", (50, 50)), "GIF"),
                 self.as_bytes(Image.new("RGB", (300, 200), "white")),
                 self.as_bytes(self.drawn("SOS").filter(ImageFilter.GaussianBlur(12))),
                 b"0" * (6 * 1024 * 1024)]
        for data in cases:
            result = mi.extract_morse(data)
            self.assertEqual(result.morse, "")
            self.assertTrue(result.error)


class TestApp(unittest.TestCase):
    """Drives the real Streamlit page: clicks buttons and submits forms."""

    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self.at = AppTest.from_file(os.path.join(HERE, "app.py"), default_timeout=30).run()
        self.assertFalse(self.at.exception)

    def btn(self, key):
        return self.at.button(key=key)

    def labelled(self, label):
        return next(b for b in self.at.button if b.label == label)

    def submit(self, key, value, button):
        """Type into a form field and press its submit button in the same run."""
        self.at.text_input(key=key).set_value(value)
        self.labelled(button).click()
        self.at.run()

    def status_html(self):
        return " ".join(m.value for m in self.at.markdown if "ml-status" in m.value)

    def test_initial_page(self):
        self.assertIn("Ready", self.status_html())
        self.assertEqual(len(self.at.tabs), 4)

    def test_decoder_form(self):
        self.submit("dec_input", "... --- ...", "Decode")
        self.assertIn("SOS", [c.value for c in self.at.code])

    def test_decoder_error_sets_status(self):
        self.submit("dec_input", "... ---------", "Decode")
        self.assertTrue(self.at.error)
        self.assertIn("Error", self.status_html())

    def test_keypad_buttons(self):
        for key in ["btn_dot", "btn_dot", "btn_dot", "btn_letter", "btn_dash", "btn_dash",
                    "btn_dash", "btn_word", "btn_dot", "btn_dot", "btn_undo"]:
            self.btn(key).click().run()
        readout = " ".join(m.value for m in self.at.markdown if "ml-readout" in m.value)
        self.assertIn("... --- / .", readout)
        self.assertIn("S O   E", readout)
        self.assertEqual(self.at.session_state.keypad, "... --- / .")
        self.btn("btn_clear").click().run()
        self.assertEqual(self.at.session_state.keypad, "")

    def test_encoder_form(self):
        self.submit("enc_input", "hello world", "Encode")
        self.assertIn(".... . .-.. .-.. --- / .-- --- .-. .-.. -..", [c.value for c in self.at.code])

    def test_example_button_populates_inputs(self):
        self.btn("ex_HELP").click().run()
        self.assertEqual(self.at.session_state.dec_input, ".... . .-.. .--.")
        self.assertIn("HELP", [c.value for c in self.at.code])

    def test_every_example_decodes_to_itself(self):
        for example in ["SOS", "HELLO", "HELP", "HELLO WORLD", "CSE 207"]:
            self.btn(f"ex_{example}").click().run()
            self.assertEqual(self.at.session_state.dec_input, ml.encode(example).morse)
            self.assertEqual(self.at.session_state.enc_input, example)
            self.assertIn(example, [c.value for c in self.at.code])

    def test_error_clears_back_to_ready(self):
        self.submit("dec_input", "........", "Decode")
        self.assertIn("Error", self.status_html())
        self.submit("dec_input", "...", "Decode")
        self.assertIn("Ready", self.status_html())
        self.assertFalse(self.at.error)

    def test_markdown_characters_shown_literally(self):
        self.submit("dec_input", "*ab*", "Decode")
        self.assertIn(r"\*ab\*", self.at.error[0].value)

    def test_empty_inputs(self):
        self.labelled("Decode").click().run()
        self.labelled("Encode").click().run()
        self.assertFalse(self.at.error)
        self.assertEqual(len(self.at.code), 5)   # only the 5 example boxes, no result boxes
        self.assertIn("No valid Morse sequence", self.at.info[0].value)

    def test_gap_buttons_and_undo(self):
        for key in ["btn_dot", "btn_letter", "btn_letter", "btn_word", "btn_word"]:
            self.btn(key).click().run()
        self.assertEqual(self.at.session_state.keypad, ". / ")   # repeated gaps ignored
        self.btn("btn_undo").click().run()
        self.assertEqual(self.at.session_state.keypad, ".")      # undo removes " / " in one step

    def chart_steps(self):
        spec = json.loads(self.at.get("plotly_chart")[0].proto.spec)
        x, y = spec["data"][0]["x"], spec["data"][0]["y"]
        return [(y[i], x[i + 1] - x[i]) for i in range(len(x) - 1)]

    def test_plotted_waveform_matches_each_source(self):
        self.btn("ex_SOS").click().run()                          # decoder input = SOS
        self.btn("btn_dot").click().run()                         # keypad = "."
        self.submit("enc_input", "T E", "Encode")                     # encoder output = "- / ."
        expected = {
            "Decoder input": ([(1, 1), (0, 1)] * 2 + [(1, 1), (0, 3)] + [(1, 3), (0, 1)] * 2
                              + [(1, 3), (0, 3)] + [(1, 1), (0, 1)] * 2 + [(1, 1)]),
            "Interactive input": [(1, 1)],
            "Encoder output": [(1, 3), (0, 7), (1, 1)],
        }
        for source, steps in expected.items():
            self.at.radio(key="viz_source").set_value(source).run()
            self.assertFalse(self.at.exception)
            self.assertEqual(self.chart_steps(), steps, source)


if __name__ == "__main__":
    unittest.main()
