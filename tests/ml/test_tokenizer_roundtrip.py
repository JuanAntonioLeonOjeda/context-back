"""The tokenizer of a saved model is the encoder's: `uv run pytest -m ml`.

Loading a saved model prints a warning that cites a Mistral model ("incorrect regex pattern ...
set `fix_mistral_regex=True`"). It does not apply to this encoder (XLM-R): checked on 2026-10-16
over the 5,477 stored articles, the saved tokenizer gives the same ids as the encoder's for every
one, and following the warning's advice (`fix_mistral_regex=True`) changes the ids of 4,991 of
them. So the flag is NOT set. This test keeps watching that the saved model tokenizes like the
encoder after any upgrade of transformers, tokenizers or SetFit. Needs the encoder in the Hugging
Face cache (see test_setfit_real.py). Never runs in CI.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.ml

ENCODER = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
# Spanish and Catalan, with accents, the middle dot, apostrophes, numbers and a long lead: what the
# model will read.
TEXTS = [
    "La Consejería amplía las plazas de infantil en los colegios públicos",
    "El Govern declara noves zones tensionades de lloguer a l'àrea metropolitana",
    "Etiquetas: Ceuta, Crisis migratoria. El Gobierno investiga la entrada de 40 personas.",
    "Sanitat obre un nou centre d'atenció primària al barri de Sant Andreu",
    "L·lúcia Martínez presenta el pla «Habitatge 2030» davant el Parlament",
    " ".join(["El Servicio de Salud reduce las listas de espera en los hospitales"] * 12),
]


def test_a_saved_model_tokenizes_like_its_encoder(tmp_path: Path) -> None:
    from setfit import SetFitModel
    from transformers import AutoTokenizer

    model = SetFitModel.from_pretrained(
        ENCODER, labels=["sector:health"], multi_target_strategy="one-vs-rest"
    )
    model.save_pretrained(str(tmp_path))

    # transformers ships no type information for the tokenizer: it is read through its call only.
    original = AutoTokenizer.from_pretrained(ENCODER)  # type: ignore[no-untyped-call]
    saved = AutoTokenizer.from_pretrained(str(tmp_path))  # type: ignore[no-untyped-call]

    assert (
        saved(TEXTS, truncation=True, max_length=128)["input_ids"]
        == original(TEXTS, truncation=True, max_length=128)["input_ids"]
    )
