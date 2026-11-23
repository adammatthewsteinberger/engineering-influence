# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Says whether a model is recorded as allowing the violence and heat a brief asks for."""

from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.services.interfaces.content_policy_interface import (
    ContentPolicyInterface,
)


class ContentPolicy(ContentPolicyInterface):
    """A brief's levels against the ceilings recorded for a model, before anything is spent.

    This project does not know any provider's usage policy and does not claim to. The person records, per model in
    their own catalog, the most violence and heat they have read the provider allow (``max_violence`` and
    ``max_heat``). A model with nothing recorded is held to ``BASELINE_VIOLENCE`` and ``BASELINE_HEAT``, the
    mildest levels above none, so a brief that asks for more is refused until the person has looked and said so.
    A brief that sets no level is never refused.
    """

    BASELINE_VIOLENCE: ClassVar[str] = "mild"
    BASELINE_HEAT: ClassVar[str] = "sweet"

    def problems(self, brief: BookBrief, model: ProviderDescriptor) -> tuple[str, ...]:
        """One sentence for each level the brief asks for that the model is not recorded as allowing."""
        found: list[str] = []
        for label, wanted, recorded, baseline, levels in (
            (
                "violence",
                brief.violence,
                model.max_violence,
                self.BASELINE_VIOLENCE,
                BookBrief.VIOLENCE_LEVELS,
            ),
            ("heat", brief.heat, model.max_heat, self.BASELINE_HEAT, BookBrief.HEAT_LEVELS),
        ):
            if wanted is None:
                continue
            allowed = recorded or baseline
            if levels.index(wanted) <= levels.index(allowed):
                continue
            where = f"{model.provider}/{model.model}"
            if recorded is None:
                found.append(
                    f"the brief asks for {label} {wanted}, and no {label} ceiling is recorded for {where}, "
                    f"so {allowed} is the most it may ask; read {model.usage_policy_url} and set "
                    f"max_{label} in the catalog entry"
                )
            else:
                found.append(
                    f"the brief asks for {label} {wanted}, but {where} is recorded as allowing up to {allowed}"
                )
        return tuple(found)

    def require(self, brief: BookBrief, model: ProviderDescriptor) -> None:
        """Return when the model allows the brief, or raise an ApplicationError (CONTENT_LEVEL_NOT_ALLOWED) saying why not."""
        found = self.problems(brief, model)
        if found:
            raise ApplicationError(
                code="CONTENT_LEVEL_NOT_ALLOWED", message="; ".join(found), http_status=422
            )
