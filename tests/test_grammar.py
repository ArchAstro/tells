"""Gold sentences for the WordNet grammar classifier."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

from tells.grammar.classify import classify


def ids(sentence: str) -> set[str]:
    return {s.id for s in classify(sentence)}


class GrammarGold(unittest.TestCase):
    def test_zero_relative(self):
        self.assertIn("zero_relative_clause", ids("The man I saw left."))
        self.assertIn("zero_relative_clause", ids("People we know never say that."))
        self.assertIn("zero_relative_clause", ids("That is the book she wrote."))
        self.assertIn("zero_relative_clause", ids("The company the founders built failed."))

    def test_zero_relative_absent_when_complementizer_present(self):
        self.assertNotIn("zero_relative_clause", ids("The man that I saw left."))
        self.assertNotIn("zero_relative_clause", ids("The man who I saw left."))

    def test_yesterday_is_not_a_relative(self):
        self.assertNotIn("zero_relative_clause", ids("Yesterday I left."))

    def test_coord_adjective_is_not_a_wh_relative_head(self):
        sent = "It's also more formal and distant, which gives permission to drift."
        self.assertNotIn("wh_relative_clause", ids(sent))
        self.assertIn("sentential_relative", ids(sent))

    def test_that_and_wh_relatives(self):
        self.assertIn("that_relative_clause", ids("The man that I saw left."))
        self.assertIn("wh_relative_clause", ids("The man who I saw left."))
        self.assertIn("wh_relative_clause", ids("The man who saw me left."))

    def test_reduced_relative(self):
        self.assertIn("reduced_relative_clause", ids("The man sitting in the corner left."))

    def test_complements_need_wordnet_that_frame(self):
        self.assertIn("that_complement", ids("I think that he left."))
        self.assertIn("zero_that_complement", ids("I think he left."))
        # eat does not license a that-clause in WordNet
        self.assertNotIn("zero_that_complement", ids("I eat he left."))
        self.assertNotIn("that_complement", ids("I eat that he left."))

    def test_infinitive_and_gerund_frames(self):
        self.assertIn("infinitival_complement", ids("She wants to go."))
        self.assertIn("gerund_complement", ids("He enjoys reading books."))

    def test_ditransitive_needs_frame_14(self):
        self.assertIn("ditransitive", ids("She told him a story."))
        self.assertNotIn("ditransitive", ids("She saw him a story."))
        self.assertNotIn(
            "ditransitive",
            ids("The last straw for me was a sentence I read a couple days ago."),
        )

    def test_voice_and_info_structure(self):
        self.assertIn("be_passive", ids("The book was written in 1960."))
        self.assertIn("there_existential", ids("There is a problem."))
        self.assertIn("it_extraposition", ids("It is clear that we failed."))
        self.assertIn("it_cleft", ids("It was the founder who left."))

    def test_appositive_that_vs_relative(self):
        self.assertIn("noun_appositive_that", ids("The fact that he left surprised me."))
        self.assertNotIn("that_relative_clause", ids("The fact that he left surprised me."))
        self.assertIn("that_relative_clause", ids("The book that she wrote sold."))

    def test_clause_types(self):
        self.assertIn("conditional_if", ids("If you leave, I leave."))
        self.assertIn("concessive", ids("Although it rained, we walked."))
        self.assertIn("polar_question", ids("Do you know the man I saw?"))
        self.assertIn("wh_question", ids("What did you see?"))
        self.assertIn("whether_if_complement", ids("I don't know if he left."))

    def test_sentence_can_carry_several_structures(self):
        got = ids("Do you know the man I saw?")
        self.assertTrue({"polar_question", "zero_relative_clause"} <= got)

    def test_span_covers_the_relative(self):
        hits = classify("The man I saw left.")
        zero = [h for h in hits if h.id == "zero_relative_clause"]
        self.assertEqual(len(zero), 1)
        self.assertIn("man I saw", zero[0].span)

    def test_wordnet_evidence_attached(self):
        hits = classify("I think he left.")
        z = next(h for h in hits if h.id == "zero_that_complement")
        self.assertTrue(any(name.startswith("think.v.") for name in z.wordnet))


class GrammarEssayGold(unittest.TestCase):
    def test_imperative(self):
        self.assertIn("imperative", ids("Leave the room."))
        self.assertIn("imperative", ids("Don't wait for permission."))
        self.assertIn("imperative", ids("Please sit down."))
        self.assertNotIn("imperative", ids("Do you know?"))
        self.assertNotIn("imperative", ids("I leave the room."))

    def test_clefts(self):
        self.assertIn("pseudo_cleft", ids("What he wants is a raise."))
        self.assertIn("reverse_pseudo_cleft", ids("A raise is what he wants."))
        self.assertNotIn("pseudo_cleft", ids("What did he want?"))
        self.assertNotIn("it_cleft", ids("What he wants is a raise."))

    def test_dative_alternation(self):
        prep = ids("She gave a book to him.")
        dbl = ids("She gave him a book.")
        self.assertIn("prepositional_dative", prep)
        self.assertNotIn("ditransitive", prep)
        self.assertIn("ditransitive", dbl)
        self.assertNotIn("prepositional_dative", dbl)
        self.assertNotIn("prepositional_dative", ids("She walked to him."))

    def test_purpose_vs_complement_infinitive(self):
        self.assertIn("purpose_infinitive", ids("I left to catch the train."))
        self.assertIn("purpose_infinitive", ids("He stopped to rest."))
        self.assertIn("purpose_infinitive", ids("I went to the store to buy milk."))
        self.assertIn("infinitival_complement", ids("She wants to go."))
        self.assertNotIn("purpose_infinitive", ids("She wants to go."))
        self.assertNotIn("infinitival_complement", ids("I left to catch the train."))

    def test_free_relative(self):
        self.assertIn("free_relative", ids("I heard what he said."))
        self.assertIn("free_relative", ids("Whoever comes will speak."))
        self.assertIn("free_relative", ids("They live where the river bends."))
        self.assertNotIn("free_relative", ids("The man who left stayed."))
        self.assertNotIn("free_relative", ids("What did you see?"))

    def test_comparatives(self):
        self.assertIn("comparative_than", ids("The new idea is bigger than the old one."))
        self.assertIn("comparative_than", ids("This is more interesting than that."))
        self.assertIn("equative_as", ids("She is as stubborn as he is."))
        self.assertIn("comparative_correlative", ids("The more I think, the more I worry."))

    def test_adjunct_clauses(self):
        self.assertIn("because_adjunct", ids("I left because it rained."))
        self.assertIn("when_adjunct", ids("When the money runs out, you stop."))
        self.assertIn("so_that_purpose", ids("He whispered so that nobody would hear."))
        self.assertNotIn("when_adjunct", ids("I know when he left."))
        self.assertNotIn("when_adjunct", ids("The day when we met was cold."))

    def test_coordination(self):
        self.assertIn("np_coordination", ids("The founder and the first user left."))
        self.assertIn("clausal_coordination", ids("I left and she stayed."))
        self.assertIn("correlative_coordination", ids("Both the idea and the execution matter."))
        self.assertNotIn("np_coordination", ids("It's more formal and distant."))
        self.assertNotIn("clausal_coordination", ids("The founder and the first user left."))

    def test_nominal_apposition(self):
        self.assertIn("nominal_apposition", ids("My friend the lawyer left."))
        self.assertNotIn("zero_relative_clause", ids("My friend the lawyer left."))
        self.assertIn("nominal_apposition", ids("Paul Graham, the essayist, wrote it."))
        self.assertNotIn("nominal_apposition", ids("The coffee cup broke."))

    def test_fronting_and_inversion(self):
        self.assertIn("negative_inversion", ids("Never have I seen such a mess."))
        self.assertIn("negative_inversion", ids("Rarely does a founder get two chances."))
        self.assertIn("negative_inversion", ids("Not only did he leave, but she stayed."))
        self.assertNotIn("negative_inversion", ids("I have never seen it."))
        self.assertIn("locative_inversion", ids("Down the hill came the children."))
        self.assertIn("locative_inversion", ids("Into the room walked the founder."))
        self.assertIn("object_fronting", ids("This I cannot accept."))
        self.assertNotIn("object_fronting", ids("This is a book."))



class Determinism(unittest.TestCase):
    def test_wordnet_lookup_ignores_hash_seed(self):
        # words with more than one WordNet form (inflection, exception list): their sense order once came from a set
        code = ("from tells.grammar.tokens import _pack\n"
                "words = [('saw', 'VBD'), ('left', 'VBD'), ('found', 'VBD'), ('leaves', 'NNS'), ('axes', 'NNS'),\n"
                "         ('bases', 'NNS'), ('lay', 'VBD'), ('felt', 'VBD'), ('better', 'JJR'), ('ground', 'VBN')]\n"
                "print([_pack(w, p)[:4] for w, p in words])")
        outs = set()
        for seed in ("1", "2", "3", "4"):
            env = {**os.environ, "PYTHONHASHSEED": seed}
            outs.add(subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                                    check=True).stdout)
        self.assertEqual(len(outs), 1)


if __name__ == "__main__":
    unittest.main()
