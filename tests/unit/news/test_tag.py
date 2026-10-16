from datos.news.domain.tag import TAG_MAX_CHARS, TAGS_PER_ARTICLE_MAX, Tag, clean_tags


def test_a_tag_is_stored_once_whatever_its_case_or_spacing() -> None:
    tags = clean_tags(["Elecciones  Generales", "elecciones generales", " ELECCIONES GENERALES "])

    assert tags == (Tag(key="elecciones generales", label="Elecciones Generales"),)


def test_tags_keep_the_order_of_the_feed_and_the_first_spelling() -> None:
    tags = clean_tags(["Política", "Sanidad", "política"])

    assert [tag.label for tag in tags] == ["Política", "Sanidad"]


def test_empty_and_blank_tags_are_dropped() -> None:
    assert clean_tags(["", "   ", "\n"]) == ()


def test_a_sentence_is_not_a_tag() -> None:
    assert clean_tags(["x" * (TAG_MAX_CHARS + 1)]) == ()
    assert len(clean_tags(["x" * TAG_MAX_CHARS])) == 1


def test_an_article_keeps_the_first_tags_only() -> None:
    tags = clean_tags([f"tag {n}" for n in range(TAGS_PER_ARTICLE_MAX + 5)])

    assert len(tags) == TAGS_PER_ARTICLE_MAX
    assert tags[0].label == "tag 0"


def test_accents_are_part_of_the_tag() -> None:
    # "Política" and "Politica" stay apart: folding accents is a choice not made here.
    assert len(clean_tags(["Política", "Politica"])) == 2
