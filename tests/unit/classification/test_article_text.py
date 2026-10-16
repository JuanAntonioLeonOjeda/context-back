from datos.classification.domain.text import TAGS_IN_TEXT_MAX, article_text, tags_line


def test_without_tags_the_text_is_the_headline_and_the_lead() -> None:
    assert article_text("Titular", "Entradilla.") == "Titular Entradilla."
    assert article_text("Titular", None) == "Titular"
    assert article_text("Titular", "") == "Titular"


def test_the_tags_go_between_the_headline_and_the_lead() -> None:
    assert (
        article_text("Titular", "Entradilla.", ("Sanidad", "Madrid"))
        == "Titular Etiquetas: Sanidad, Madrid. Entradilla."
    )


def test_an_article_without_a_lead_ends_with_its_tags() -> None:
    assert article_text("Titular", None, ("Sanidad",)) == "Titular Etiquetas: Sanidad."


def test_only_the_first_tags_are_read() -> None:
    tags = tuple(f"tag{n}" for n in range(TAGS_IN_TEXT_MAX + 3))

    text = article_text("Titular", None, tags)

    assert f"tag{TAGS_IN_TEXT_MAX - 1}" in text
    assert f"tag{TAGS_IN_TEXT_MAX}" not in text


def test_the_tags_never_push_the_headline_out_of_the_front() -> None:
    assert article_text("Titular", "Entradilla.", ("A",)).startswith("Titular ")


def test_the_line_of_tags_is_the_one_the_text_carries() -> None:
    tags = ("Sanidad", "Madrid")

    assert tags_line(tags) in article_text("Titular", "Entradilla.", tags)
    assert tags_line(()) == ""
