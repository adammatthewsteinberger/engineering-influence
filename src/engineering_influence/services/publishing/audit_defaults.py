# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Default phrase lists for the manuscript audit."""


class AuditDefaults:
    """High-confidence scaffold phrases and rhetorical formulas.

    The forbidden phrases are signs that a planning packet or proof note leaked into
    reader-facing copy. They are deliberately narrower than general editorial advice.
    """

    FORBIDDEN_PHRASES = (
        "Evidence packet:",
        "Case study:",
        "The chapter's central claim should",
        "The chapter’s central claim should",
        "The five-part model",
        "The preceding chapter",
        "The current proof",
        "The final version",
        "The book opens where",
        "Development Edition",
        "Development Proof",
        "Status: drafting",
        "[PLACEHOLDER",
        "[TESTIMONY",
        "[TODO",
        "[TBD",
        "[VERIFY",
    )

    FORMULA_PHRASES = (
        "the question is not",
        "the answer is not",
        "the danger is",
        "the task is",
        "the retrieval is",
    )
