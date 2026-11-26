# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The order to draft a screenplay's scenes, from prompt 09: the images and All Is Lost first, the acts in order, and the
likely-shared scenes last."""

from typing import ClassVar

from engineering_influence.services.interfaces.screenplay_drafting_order_interface import (
    ScreenplayDraftingOrderInterface,
)


class ScreenplayDraftingOrder(ScreenplayDraftingOrderInterface):
    """Cards are `(number, beat)`. A card's number must be unique, and every shareable number must be a card. The
    first group is drafted in the order `FIRST_BEATS`; the rest keep their card order, with the shareable ones last."""

    FIRST_BEATS: ClassVar[tuple[str, ...]] = ("Opening Image", "Closing Image", "All Is Lost")

    def order(
        self, cards: tuple[tuple[int, str], ...], shareable: frozenset[int]
    ) -> tuple[int, ...]:
        """The drafting order of the card numbers."""
        numbers = [number for number, _ in cards]
        if len(set(numbers)) != len(numbers):
            raise ValueError("each scene card has a number of its own")
        if not shareable <= set(numbers):
            raise ValueError("a shareable scene must be one of the cards")
        first = sorted(
            (
                (self.FIRST_BEATS.index(beat), number)
                for number, beat in cards
                if beat in self.FIRST_BEATS
            )
        )
        first_numbers = [number for _, number in first]
        rest = [number for number in numbers if number not in first_numbers]
        ordinary = [number for number in rest if number not in shareable]
        last = [number for number in rest if number in shareable]
        return tuple(first_numbers + ordinary + last)
