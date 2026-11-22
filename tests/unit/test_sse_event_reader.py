# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SseEventReader: the message events of a Server-Sent Events stream, with every line bounded."""

import pytest

from engineering_influence.infrastructure.tools.interfaces.sse_event_reader_interface import (
    SseEventReaderInterface,
)
from engineering_influence.infrastructure.tools.sse_event_reader import SseEventReader


def reader(limit: int = 1000) -> SseEventReader:
    return SseEventReader(limit)


def test_it_is_an_event_reader() -> None:
    assert isinstance(reader(), SseEventReaderInterface)


def test_a_line_limit_below_one_is_refused() -> None:
    with pytest.raises(ValueError, match="at least one byte"):
        SseEventReader(0)


def test_an_event_ends_at_a_blank_line() -> None:
    found = reader()
    assert found.feed(b'data: {"a":1}\n') == []
    assert found.feed(b"\n") == ['{"a":1}']


def test_the_data_of_several_events_in_one_chunk_comes_back_in_order() -> None:
    assert reader().feed(b"data: one\n\ndata: two\n\ndata: three\n\n") == ["one", "two", "three"]


def test_the_data_lines_of_one_event_are_joined_with_a_newline() -> None:
    assert reader().feed(b"data: a\ndata: b\ndata:\ndata: c\n\n") == ["a\nb\n\nc"]


def test_one_leading_space_after_the_colon_is_dropped_and_no_more() -> None:
    assert reader().feed(b"data:no space\n\ndata:  two spaces\n\n") == ["no space", " two spaces"]


def test_carriage_return_line_feed_endings_are_read() -> None:
    assert reader().feed(b"data: x\r\n\r\ndata: y\r\n\r\n") == ["x", "y"]


def test_an_event_split_across_chunks_at_any_byte_is_the_same_event() -> None:
    stream = b"event: message\ndata: caf\xc3\xa9\ndata: two\n\ndata: next\n\n"
    for size in range(1, len(stream) + 1):
        found, got = reader(), []
        for start in range(0, len(stream), size):
            got.extend(found.feed(stream[start : start + size]))
        assert got == ["café\ntwo", "next"], size


def test_an_event_named_message_is_returned_and_any_other_name_is_skipped() -> None:
    stream = b"event: message\ndata: yes\n\nevent: ping\ndata: no\n\nevent: \ndata: nameless\n\n"
    assert reader().feed(stream) == ["yes", "nameless"]


def test_the_name_applies_to_one_event_only() -> None:
    assert reader().feed(b"event: ping\ndata: no\n\ndata: yes\n\n") == ["yes"]


def test_comments_ids_retries_and_unknown_fields_are_ignored() -> None:
    stream = b": keep-alive\nid: 7\nretry: 1000\nweird: x\ndata: kept\n\n"
    assert reader().feed(stream) == ["kept"]


def test_a_blank_line_with_no_data_ends_nothing() -> None:
    assert reader().feed(b"\n\n: comment\n\nevent: message\n\n") == []


def test_an_event_the_stream_stops_in_the_middle_of_is_never_returned() -> None:
    found = reader()
    assert found.feed(b"data: whole\n\ndata: cut off\n") == ["whole"]


def test_a_field_without_a_colon_is_that_field_with_an_empty_value() -> None:
    assert reader().feed(b"data\ndata: kept\n\n") == ["\nkept"]
    assert reader().feed(b"event: ping\nevent\ndata: kept\n\n") == ["kept"]


def test_a_line_of_exactly_the_limit_is_read_and_one_byte_more_is_refused() -> None:
    body = b"d" * 10
    assert SseEventReader(15).feed(b"data: " + body[:9] + b"\n\n") == ["d" * 9]
    with pytest.raises(ValueError, match="longer than 15 bytes"):
        SseEventReader(15).feed(b"data: " + body + b"\n\n")


def test_a_finished_line_longer_than_the_limit_is_refused() -> None:
    with pytest.raises(ValueError, match="longer than 10 bytes"):
        SseEventReader(10).feed(b"data: " + b"x" * 20 + b"\n")


def test_a_line_that_never_ends_is_refused_as_soon_as_it_is_too_long() -> None:
    found = SseEventReader(10)
    assert found.feed(b"data: ab") == []
    with pytest.raises(ValueError, match="longer than 10 bytes"):
        found.feed(b"cdef")


def test_text_that_is_not_utf8_is_refused() -> None:
    with pytest.raises(ValueError):
        reader().feed(b"data: \xff\xfe\n\n")


def test_event_names_and_data_that_are_not_utf8_are_both_refused() -> None:
    with pytest.raises(ValueError):
        reader().feed(b"event: \xff\n")


def test_a_field_that_is_ignored_may_hold_any_bytes() -> None:
    assert reader().feed(b"id: \xff\xfe\ndata: ok\n\n") == ["ok"]


def test_a_line_that_has_not_ended_may_be_exactly_the_limit_long_and_no_longer() -> None:
    found = SseEventReader(10)
    assert found.feed(b"x" * 10) == []
    with pytest.raises(ValueError, match="longer than 10 bytes"):
        found.feed(b"y")
