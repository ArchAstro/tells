"""Sources, surface features and the model, on small hand-made corpora."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from writing_style import model as M
from writing_style.cli import main
from writing_style.features import surface
from writing_style.sources import Doc, expand, load, markdown_units, split_units, tweet_units


class Sources(unittest.TestCase):
    def test_markdown_keeps_prose_only(self):
        md = (
            "# Title\n\nI built it. It broke.\n\n```py\nx = 1\n```\n\n![pic](a.png)\n\n"
            "| a | b |\n|---|---|\n| short | This cell is long enough to count as a real sentence. |\n\n"
            "- a list item that I wrote\n<!-- hidden -->\n"
        )
        units = markdown_units(md)
        self.assertEqual(units[0], "I built it. It broke.")
        self.assertIn("This cell is long enough to count as a real sentence.", units)
        self.assertIn("a list item that I wrote", units)
        self.assertFalse(any("x = 1" in u or "short" == u or "hidden" in u for u in units))

    def test_markdown_stops_at_endnotes_and_skips_thanks(self):
        md = "I think so.[1]\n\n**Thanks** to Bob for reading.\n\n**Notes**\n\n[1] A footnote here."
        self.assertEqual(markdown_units(md), ["I think so."])

    def test_critic_markup_is_accepted(self):
        self.assertEqual(markdown_units("It {~~was~>is~~} {++very ++}good{>>note<<}."), ["It is very good."])

    def test_tweet_strips_handles_links_and_quotes(self):
        body = "@a @b 1/ this is pretty good https://x.co/1\n\n### Quoted\nsomeone else"
        self.assertEqual(tweet_units(body), ["this is pretty good"])

    def test_curly_quotes_are_normalised(self):
        self.assertEqual(split_units(["It’s fine"]), ["It's fine."])

    def test_tweet_detected_from_front_matter(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.md"
            p.write_text("---\nconversation_id: 1\n---\nI shipped it today\n")
            doc = load(p)
            self.assertEqual(doc.kind, "tweet")
            self.assertEqual(doc.sentences, ["I shipped it today."])

    def test_expand_relative_glob_and_dir(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.md").write_text("x")
            (Path(d) / "_meta.md").write_text("x")
            (Path(d) / "b.txt").write_text("x")
            self.assertEqual([p.name for p in expand(d)], ["a.md", "b.txt"])
            self.assertEqual([p.name for p in expand(f"{d}/*.md")], ["_meta.md", "a.md"])
            self.assertEqual(expand(f"{d}/missing.md"), [])


class Surface(unittest.TestCase):
    def test_features(self):
        cases = {
            "Pieces, state, invariants.": {"fragment", "short_sentence", "list_of_three"},
            "Cost: we pay for it twice.": {"colon_label", "first_person"},
            "It's basically fine, I think.": {"contraction", "hedge", "first_person"},
            "But you won't see it.": {"starts_with_conjunction", "second_person", "contraction"},
            "Skim it now and come back later.": {"imperative_start"},
            "It is not speed but trust that matters here.": {"not_x_but_y"},
            "The server owns it — always.": {"em_dash"},
        }
        for sentence, want in cases.items():
            with self.subTest(sentence):
                self.assertLessEqual(want, surface(sentence))

    def test_no_false_fragment(self):
        self.assertNotIn("fragment", surface("The server settles the job."))


def doc(name: str, sentences: list[str]) -> Doc:
    return Doc(name, name, sentences, "markdown")


PLAIN = ["The server settles the job after the push.", "I wrote the scheduler in a week.",
         "We verify every branch locally.", "It's pretty simple, I think."]
CLIPPED = ["Pieces, state, invariants.", "Skim it now.", "Worker, server, remote.", "Fast. Cheap. Safe."]


class Model(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blog = M.build_corpus("blog", [doc(f"b{i}", PLAIN * 5) for i in range(4)])
        tweets = M.build_corpus("tweets", [doc(f"t{i}", PLAIN[i % 4:i % 4 + 1]) for i in range(80)])
        cls.model = M.Model([blog, tweets])

    def test_short_docs_are_chunked(self):
        tweets = self.model.corpora[1]
        self.assertTrue(tweets.chunked)
        self.assertEqual(sum(d.n for d in tweets.docs), 80)
        self.assertFalse(self.model.corpora[0].chunked)

    def test_clipped_draft_flags_fragments_as_voice(self):
        stats, by_feature = M.draft_stats(doc("draft", CLIPPED * 5))
        rows = {r.id: r for r in M.score(stats, self.model)}
        self.assertEqual(rows["fragment"].verdict, "fix")
        self.assertEqual(rows["fragment"].direction, "too_many")
        self.assertIn("Pieces, state, invariants.", by_feature["fragment"])

    def test_matching_draft_is_clean(self):
        stats, _ = M.draft_stats(doc("draft", PLAIN * 5))
        self.assertEqual(M.n_off(M.score(stats, self.model)), 0)

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.json"
            self.model.save(p)
            back = M.Model.load(p)
            self.assertEqual(back.n, self.model.n)
            self.assertAlmostEqual(back.combined("first_person"), self.model.combined("first_person"))

    def test_calibrate_scores_every_doc(self):
        res = M.calibrate(self.model)
        self.assertEqual(len(res), sum(len(c.docs) for c in self.model.corpora))
        self.assertTrue(all(r.distance >= 0 for r in res))

    def test_reference_direction_and_steered(self):
        human = M.build_corpus("h", [doc(f"h{i}", PLAIN * 3) for i in range(5)], chunk=0)
        machine = M.build_corpus("m", [doc(f"m{i}", CLIPPED * 3) for i in range(5)], chunk=0)
        ref = M.build_reference(human, [machine])
        self.assertEqual(ref["features"]["fragment"]["direction"], "too_many")
        stats, _ = M.draft_stats(doc("draft", CLIPPED * 5))
        rows = {r.id: r for r in M.score(stats, self.model, ref)}
        self.assertTrue(rows["fragment"].ai_like)
        ref["steered"] = ["fragment"]
        rows = {r.id: r for r in M.score(stats, self.model, ref)}
        self.assertFalse(rows["fragment"].ai_like)

    def test_excluding_drops_the_named_doc(self):
        held = self.model.excluding("b0")
        self.assertEqual(held.n, self.model.n - self.model.corpora[0].docs[0].n)
        self.assertIs(self.model.excluding("not-there"), self.model)

    def test_auc(self):
        self.assertEqual(M.auc([2, 3], [0, 1]), 1.0)
        self.assertEqual(M.auc([1], [1]), 0.5)


class Cli(unittest.TestCase):
    def test_build_and_check(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for i in range(3):
                (d / f"post{i}.md").write_text("\n\n".join(PLAIN * 4))
            (d / "draft.md").write_text("\n\n".join(CLIPPED * 4))
            out = d / "m.json"
            main(["build", "-c", f"blog={d}/post*.md", "-o", str(out)])
            self.assertEqual(json.loads(out.read_text())["corpora"][0]["n_files"], 3)
            import contextlib
            import io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                main(["check", str(d / "draft.md"), "-m", str(out), "--json"])
            res = json.loads(buf.getvalue())
            self.assertGreater(res["off"], 0)
            frag = next(f for f in res["features"] if f["id"] == "fragment")
            self.assertEqual(frag["verdict"], "fix")

    def test_bundled_reference_loads(self):
        from writing_style.cli import load_reference
        ref = load_reference("pg-vs-llm")
        self.assertIn("em_dash", ref["steered"])
        self.assertEqual(ref["features"]["purpose_infinitive"]["direction"], "too_few")


if __name__ == "__main__":
    unittest.main()
