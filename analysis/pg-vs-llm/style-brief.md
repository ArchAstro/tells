# Generate idea-essays (matched to `human/paul_graham/`)

Write **50** standalone idea-essays into `llm/<model>/essays/`.

This is the **same assignment** as the 50 human essays in `human/paul_graham/`. Those essays share a subject, a reader, and a style. Match all three. Do **not** impersonate Paul Graham, quote him, cite him, or reuse his labels (`founder mode`, `ramen profitable`, `schlep blindness`, `default alive`, `maker's schedule`, etc.). Invent new examples.

---

## 1. Subject matter

These are not op-eds, memoir, news, or productivity tips. They are **attempts to name a mechanism** in one of these territories:

| Share of the 50 | Territory | What an essay in it actually does |
|---:|---|---|
| ~40% | Startups and companies | How young companies live or die: users, hiring, growth, fundraising, founders vs professional managers, why a piece of conventional business advice is wrong |
| ~25% | Work, ambition, character | What it takes to do ambitious work: effort, taste, stubbornness, earnestness, early work, what to work on |
| ~20% | Writing, thinking, ideas | How ideas get made and tested: writing as thinking, heresy, taste, expertise, saying something new |
| ~10% | Wealth and power | How people get rich, taxes, inequality, who actually builds things — argued as mechanisms, not moral sermons |
| ~5% | Specific people or scenes | A person, a company, or a place used as a case that yields a general rule |

Every essay needs **one payload**: a distinction, a missing category, or a claim that sounds slightly too simple and then turns out to be load-bearing. Examples of the *shape* of a payload (do not reuse these theses):

- People treat X as one thing; it is two, and the difference decides outcomes.
- The advice everyone gives is the right advice for a different job than the one you have.
- The question you should ask first is not the one that sounds sophisticated.
- A virtue and its neighboring vice are not the same behavior labeled after the fact.

Stay inside this world: founders, programmers, students who might become those, investors, writers, ambitious people choosing what to work on. Concrete furniture: a company at month 9, a hiring decision, a draft, a city, a school, a fundraising meeting. Not: electoral politics as the main subject, culture-war recap, product pitches, literature-class close reading, wellness, or "the future of AI."

If the topic names a startup object (users, growth, managers), write about **actual companies**. If it names writing or thinking, write about **doing the work**, not about "content."

---

## 2. Reader

Write as if the reader is smart, busy, and already in this world — a founder, a would-be founder, a programmer, a student who might become one. They do not need the field defined. They do need the usual story about it taken apart.

Do not write up to academics or down to a general-interest magazine. No "in today's rapidly changing world." No policy-brief cadence. The implied contract is: *I noticed something working people get wrong; here is the piece that was missing.*

---

## 3. Style

### Diction
- Short, ordinary words. Prefer `get`, `try`, `wrong`, `work`, `idea` to `obtain`, `endeavor`, `incorrect`, `labor`, `concept`.
- Conversational written English, not speech-with-um. Contractions are fine. Slang is not the point.
- Define one term in plain words if it pays rent (`by X I mean…`). Then use it. Do not build a vocabulary of branded phrases.
- Almost no em dashes (the human set is ~0.2 per 1k characters). Use commas, periods, or a new sentence.
- Italics for stress on a word, sparingly. Bold only if you are naming a term you will reuse.

### Sentences
- Median ~15 words. Mix 8-word punches with a 25-word explanation. Almost no 40-word stacks.
- One job per sentence. If a sentence contains an "and" that starts a new thought, split it.
- Occasional very short paragraph (one sentence) after a claim, as a turn. About 1 in 6 paragraphs is that short. The rest are 3–6 sentences / 40–80 words.

### Voice
- `you` more than `I`. `You` is the reader in the situation. `I` is only for things a person could actually have seen or done — not a fake diary.
- First person plural (`we`) when talking about a group the writer is in (people who start companies, people who write).
- Calm confidence. Not hype, not hedging into mush. Strongest claim that is still true. If you must qualify, qualify the scope (`in early companies`, `once you have users`), not the courage of the sentence.

### Moves that belong here
1. Open with the claim or the incident. Sentence one is already the essay.
2. Split a lump into two, or name the thing people have been circling.
3. Give **one** example enough room to work (a company, a person, a piece of writing). Do not sprinkle famous names.
4. Take the obvious objection in the next paragraph and answer it. Not a FAQ block.
5. Analogies from ordinary life (a coach, a 3-year-old, a car that needs a crank), not from mythology or pop science.
6. A mid-essay "why does this happen?" that goes one level down into mechanism.
7. Stop when the idea is done. One short coda at most. No recap, no call to action, no "in conclusion."

### Moves that do not
- Throat-clearing: "I've been thinking a lot about…", "X is more important than ever."
- Antithesis stacks: "It's not X. It's Y. And it's not Y either — it's Z."
- Visible outline: `##` headings, numbered "N things", bullet lists.
- Moralizing. Describe what happens. Let the reader feel the implication.
- Academic vapor: "the issue is complex and many factors must be considered."
- LLM cadence: delve, tapestry, landscape, crucial, robust, nuanced, "in this essay I will."
- Fake intimacy: invented conversations with named famous founders, fake YC batch numbers, "a founder said to me last Tuesday" with a celebrity attached. Generalized "founders I talk to" is the ceiling.

### Titles
Short, like the control set. Patterns that fit:

- `How to X`
- `Why X`
- `The X of Y` / `X and Y`
- A two- or three-word name for the missing category
- A question only if the essay answers it (`Default Alive or Default Dead?`)

The title should be the payload, not a tease. After reading it you already know the bet.

---

## 4. Shape and length

Measured on the 50 human essays (use the middle of the band):

| Trait | Target |
|---|---|
| Words | **1,200–1,800**, aim **~1,500** (set median is 1,533) |
| Paragraphs | ~25–30 |
| Open | claim or puzzle in the first 2–3 sentences |
| Close | last paragraph is still thinking, not summarizing |
| Questions | ~1 per 15 sentences, to turn a corner |
| Sections | none |

File format:

```
# Title

<prose paragraphs only>
```

`NNN-slug.md` for `001`–`050`. Topic **N** below is file `NNN`. No meta, no AI talk, no source comment.

---

## 5. Topics (one per file)

These are prompts for a payload, not titles you must keep. Write a new title in the style above. Do not write two essays on the same distinction. Mix should roughly follow the table in §1 — do not turn every topic into a writing essay or every topic into a vibe piece about "ambition."

**Startups and companies**
1. Why the first ten users teach a different lesson than the next thousand
2. When hiring a "real CEO" is the mistake
3. How to tell a company that is quietly dying from one that is merely ugly
4. Why founders get given the operating manual for a different job
5. What to do in the month after a launch that did not work
6. Why "hire good people and leave them alone" fails in a company the founder still understands
7. The difference between a customer and an audience
8. When raising money changes what the company is allowed to notice
9. Why competitors are a worse source of strategy than users
10. How a company gets captured by its own org chart
11. What "traction" hides
12. Why some products can only be sold by the people who built them
13. The point at which process starts existing to protect people from the founder
14. How to decide whether a pivot is cowardice or taste
15. Why office politics show up earlier than founders expect
16. What investors actually herd on (it is not the idea)
17. How to talk to a big company that wants to "partner" without getting eaten
18. Why the boring parts of a startup are usually the company
19. The difference between a scene of builders and a scene of people who talk about building
20. When growth is a different business than the one that got you users

**Work, ambition, character**
21. Why ambitious people underestimate maintenance
22. The difference between persistence and obstinacy *before* you know the outcome
23. How to pick work you will still respect if it stays small
24. Why early success is a worse teacher than early failure
25. The kind of stubbornness that updates
26. How to stay a beginner in a field you already know
27. Why being easy to work with can be a tax on the work
28. What luck looks like from inside a long project
29. How to use boredom as a compass without using it as an excuse
30. The ambition that does not look like ambition yet
31. Why "follow your passion" is the wrong unit (the unit is a kind of work)
32. How to keep a private metric no one else can see

**Writing, thinking, ideas**
33. Why writing something down changes what you believe
34. The difference between taste and preference
35. How to tell if a disagreement is about words
36. Why the second draft is where most people lose the idea
37. What "obvious once you say it" is worth
38. How reading starts to substitute for doing
39. Why useful writing is a bet on a specific claim, not a tour of a topic
40. The temptation to become a commentator on your own field
41. How to notice you are performing competence
42. Why some ideas can only be had while making the thing

**Wealth, power, selection**
43. How people actually get rich now (the mechanism, not the sermon)
44. Why markets underprice patience
45. What a wealth tax would change besides revenue
46. Why "fair" processes produce timid products
47. How institutions launder taste into procedure
48. The difference between earning a fortune and being adjacent to one

**Case / scene**
49. A city that should have become a hub and why it did not (invent the case; make the rule general)
50. A person who was underestimated for a quality that later turned out to be the whole game (composite, not a celebrity profile)

---

## 6. Process

1. Write `001`–`010`, count words, rewrite any body outside 1,200–1,800.
2. Continue in batches of 10 with the same length discipline.
3. Finish with a table: filename, title, word count, and which territory (§1) it landed in.
4. If more than ~8 of the 50 are in one territory, rewrite the extras into the missing ones.

A finished essay should be something you could publish next to the human set without the reader needing a new genre. Same subject world, same reader, same prose pressure — new idea.
