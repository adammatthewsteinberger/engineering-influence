# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FallbackSearchProvider: the backup is asked when the primary cannot help, and only then."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.models.search_hit import SearchHit
from engineering_influence.services.fallback_search_provider import FallbackSearchProvider

A = (SearchHit("https://a.test/", "A"),)
B = (SearchHit("https://b.test/", "B"),)


class Fake(SearchProviderInterface):
    def __init__(self, outcome: tuple[SearchHit, ...] | BaseException) -> None:
        self.outcome = outcome
        self.asked: list[tuple[str, int]] = []

    def search(self, query: str, count: int) -> tuple[SearchHit, ...]:
        self.asked.append((query, count))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def app_error(code: str) -> ApplicationError:
    return ApplicationError(code=code, message=code.lower(), http_status=502)


def test_it_is_a_search_provider() -> None:
    assert isinstance(FallbackSearchProvider(Fake(A), Fake(B)), SearchProviderInterface)


def test_the_primarys_links_are_used_and_the_backup_is_never_asked() -> None:
    primary, backup = Fake(A), Fake(B)
    assert FallbackSearchProvider(primary, backup).search("bees", 3) == A
    assert primary.asked == [("bees", 3)]
    assert backup.asked == []


@pytest.mark.parametrize(
    "failure",
    [
        TransientStageError("down"),
        CapacityExhaustedError("quota"),
        app_error("SEARCH_REJECTED"),
        app_error("SEARCH_UNEXPECTED_REPLY"),
    ],
    ids=["transient", "capacity", "rejected", "unexpected"],
)
def test_a_primary_that_fails_is_replaced_by_the_backup(failure: BaseException) -> None:
    primary, backup = Fake(failure), Fake(B)
    assert FallbackSearchProvider(primary, backup).search("bees", 3) == B
    assert backup.asked == [("bees", 3)]


def test_a_query_the_primary_calls_invalid_is_not_sent_to_the_backup() -> None:
    primary, backup = Fake(app_error("SEARCH_QUERY_INVALID")), Fake(B)
    with pytest.raises(ApplicationError) as error:
        FallbackSearchProvider(primary, backup).search("", 3)
    assert error.value.code == "SEARCH_QUERY_INVALID"
    assert backup.asked == []


def test_a_primary_that_finds_nothing_is_replaced_by_the_backup() -> None:
    primary, backup = Fake(()), Fake(B)
    assert FallbackSearchProvider(primary, backup).search("bees", 3) == B
    assert backup.asked == [("bees", 3)]


def test_nothing_from_either_is_nothing() -> None:
    assert FallbackSearchProvider(Fake(()), Fake(())).search("bees", 3) == ()


def test_when_the_backup_fails_too_its_error_is_raised_with_the_primarys_as_context() -> None:
    first, second = TransientStageError("searxng down"), CapacityExhaustedError("brave quota")
    with pytest.raises(CapacityExhaustedError) as error:
        FallbackSearchProvider(Fake(first), Fake(second)).search("bees", 3)
    assert error.value is second
    assert error.value.__context__ is first


def test_a_failure_nobody_expected_is_not_hidden_by_the_backup() -> None:
    primary, backup = Fake(RuntimeError("a bug")), Fake(B)
    with pytest.raises(RuntimeError, match="a bug"):
        FallbackSearchProvider(primary, backup).search("bees", 3)
    assert backup.asked == []
