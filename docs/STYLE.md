# How these documents are written

**BLUF:** Every teaching page here has three layers, in this order: the bottom line up front, a short scene in
which Professor Feynman teaches his student Daniel the one idea the page turns on, and then the exact reference.
A test (`tests/unit/test_docs_match_code.py`) fails a page that breaks the pattern, a link that goes nowhere, or
a command the code does not have.

## The three layers

| Layer | What it is | The test for it |
|---|---|---|
| **BLUF** | The answer first: what this is, what to type, what you get. Two to four sentences, starting `**BLUF:**`, directly under the title | A reader who stops here can still act |
| **The scene** | Daniel has a real problem and asks about it. The Professor answers in plain words with one everyday comparison, then checks that Daniel can use the idea | It teaches one idea, and someone who skips it loses no fact |
| **The reference** | Tables, commands, flags, defaults, exit codes, limits. Complete and exact | A reader who arrives from a search finds the row |

Nothing true may live only in the scene. The scene explains; the reference states. That is what lets one page
serve the person reading top to bottom and the person who searched for a flag.

## The two characters

**Professor Feynman** teaches the way the method named for him asks: say it in plain words, use a comparison
from ordinary life, find the place where the comparison breaks, and say so. He does not lecture. He asks Daniel
what he thinks will happen, and lets him be wrong.

**Daniel** is his student: capable, new to this, and in the middle of doing something. He asks the question a
newcomer would really ask, pushes back when an answer is too tidy, and ends each scene by saying the idea back in
his own words or by trying it.

The Professor is a fictional teacher, named in homage. Nothing he says here is a quotation from, or attributed
to, the physicist Richard Feynman.

## Rules for a scene

1. **One idea.** If a page has two, it gets two scenes, each under the section it belongs to.
2. **Daniel wants something.** Open on his problem, not on the topic.
3. **Plain words first.** A term is used only after it has been explained in words a newcomer has.
4. **One comparison, and its limit.** Say where the comparison stops being true.
5. **End on a test.** Daniel predicts, tries or restates. If he could not, the scene is not finished.
6. **Short.** Six to fourteen lines of dialogue. Written as a block quote, each line starting with the speaker's
   name in bold.
7. **No fact lives only here.** Every command, number and limit in a scene also appears in the reference below it.

## Rules for every page

- **True to the code.** Say what is built, what is built and unproven, and what is not built. Never round up.
- **Commands are copied from a run**, not from memory, and the command tree and the environment variables are
  checked against the code by the test.
- **Scannable.** Short paragraphs, a table where there are three or more of the same kind of thing, a code block
  for anything to be typed.
- **A hook, not hype.** The first line may be punchy. It may not claim anything the code does not do.
- **Plain English.** No em dashes or en dashes; a comma, a colon or a new sentence does the job.

## Which pages are plain

Some pages are read under pressure, or by a program, or as a record of a decision. They get a BLUF where it
helps and no scene:

- `docs/adr/`, `CHANGELOG.md` and `changelog.d/`: decisions and history
- `SECURITY.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, `LICENSE` and [THREAT_MODEL.md](THREAT_MODEL.md)
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `llms.txt` and `llms-full.txt`: read by models, which do best with
  direct instructions
- this page
