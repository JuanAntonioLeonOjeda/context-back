from collections.abc import Sequence
from datetime import UTC, datetime

from datos.stories.application.embed_articles import ArticleToEmbed, embed_new
from datos.stories.domain.text import embedding_text
from datos.stories.infrastructure.sentence_encoder import SentenceEncoder

SINCE = datetime(2026, 9, 1, tzinfo=UTC)


class FakeEncoder:
    name = "fake"
    version = "fake-v1"

    def __init__(self) -> None:
        self.seen: list[str] = []

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        self.seen.extend(texts)
        return [[float(len(text))] for text in texts]


class InMemoryEmbeddings:
    def __init__(self, articles: list[ArticleToEmbed]) -> None:
        self._articles = articles
        self.vectors: dict[tuple[int, str], list[float]] = {}

    def missing(self, encoder_version: str, *, since: datetime, limit: int) -> list[ArticleToEmbed]:
        pending = [a for a in self._articles if (a.article_id, encoder_version) not in self.vectors]
        return pending[:limit]

    def add(
        self, encoder_name: str, encoder_version: str, vectors: Sequence[tuple[int, list[float]]]
    ) -> int:
        new = [(i, v) for i, v in vectors if (i, encoder_version) not in self.vectors]
        self.vectors.update({(i, encoder_version): v for i, v in new})
        return len(new)


def articles(count: int) -> list[ArticleToEmbed]:
    return [ArticleToEmbed(n, f"Headline {n}", None) for n in range(1, count + 1)]


def test_every_missing_article_gets_a_vector_across_several_batches() -> None:
    repository = InMemoryEmbeddings(articles(150))

    stored = embed_new(FakeEncoder(), repository, since=SINCE)

    assert stored == 150
    assert len(repository.vectors) == 150


def test_running_again_embeds_nothing() -> None:
    repository = InMemoryEmbeddings(articles(3))
    embed_new(FakeEncoder(), repository, since=SINCE)
    second = FakeEncoder()

    assert embed_new(second, repository, since=SINCE) == 0
    assert second.seen == []


def test_the_encoder_reads_the_headline_and_the_lead_and_no_tags() -> None:
    repository = InMemoryEmbeddings([ArticleToEmbed(1, "Headline", "The lead.")])
    encoder = FakeEncoder()

    embed_new(encoder, repository, since=SINCE)

    assert encoder.seen == ["Headline The lead."]


def test_a_missing_lead_leaves_no_trailing_space() -> None:
    assert embedding_text("Headline", None) == "Headline"


class FakeSentenceModel:
    max_seq_length = 128

    def encode(self, sentences: list[str], **options: object) -> list[list[float]]:
        assert options == {"normalize_embeddings": True}
        return [[1.0, 0.0] for _ in sentences]


def test_the_encoder_version_says_the_model_and_how_much_text_it_reads() -> None:
    encoder = SentenceEncoder("sentence-transformers/some-model", FakeSentenceModel())

    assert encoder.version == "some-model-max128"
    assert encoder.encode(["a", "b"]) == [[1.0, 0.0], [1.0, 0.0]]
