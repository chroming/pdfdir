from hypothesis import given, settings
from hypothesis import strategies as st

from src.convert import AmbiguousPageLabelError, convert_dir_text, is_in, split_page_num

safe_title = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs", "Cc"),
        blacklist_characters="\r\n0123456789",
    ),
    min_size=1,
    max_size=30,
)


@settings(max_examples=100, deadline=None)
@given(
    entries=st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=12),
            safe_title,
            st.one_of(st.none(), st.integers(min_value=1, max_value=10_000)),
        ),
        min_size=1,
        max_size=30,
    )
)
def test_converted_tree_always_has_valid_parent_indexes(entries):
    lines = [
        f"{' ' * indentation}{title}{'' if page is None else f' {page}'}"
        for indentation, title, page in entries
    ]

    try:
        result = convert_dir_text(
            "\n".join(lines), level_by_space=True, fix_non_seq=True,
        )
    except AmbiguousPageLabelError as exc:
        assert 1 <= exc.line_number <= len("\n".join(lines).splitlines())
        return

    assert list(result) == list(range(sum(bool(line.strip()) for line in lines)))
    assert [item["num"] for item in result.values()] == sorted(
        item["num"] for item in result.values()
    )
    for index, item in result.items():
        if "parent" in item:
            assert item["parent"] in result
            assert item["parent"] < index


@settings(max_examples=100, deadline=None)
@given(
    title=safe_title.filter(lambda value: not value.endswith((" ", ".", "-"))),
    page=st.integers(min_value=-10_000, max_value=10_000),
)
def test_page_suffix_round_trips(title, page):
    assert split_page_num(f"{title} {page}") == (title, page)


@settings(max_examples=100, deadline=None)
@given(
    text=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        max_size=200,
    )
)
def test_arbitrary_directory_text_returns_tree_or_explicit_page_label_error(text):
    try:
        result = convert_dir_text(text)
    except AmbiguousPageLabelError as exc:
        assert 1 <= exc.line_number <= len(text.splitlines())
        assert exc.label
        return

    assert list(result) == list(range(len(result)))


def test_invalid_level_regular_expression_is_treated_as_no_match(caplog):
    assert is_in("Chapter", "[") is False
    assert "regex error" in caplog.text
