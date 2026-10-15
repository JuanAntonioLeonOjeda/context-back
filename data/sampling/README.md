# Sampling for hand labelling

How the articles to be labelled by hand are drawn: the blind test set (`data/eval/`,
`specs/foundation/plan.md`, "Blind test set method") and the training set (`data/train/`, ADR-0016).
Both use the same method, run by `python -m datos.classification sample`.

## The method

1. **Candidates**: every stored article collected up to a cut-off date (`--until`), minus every
   article already in any set of `data/train/` or `data/eval/`. The database keeps growing, so the
   cut-off and the seed make a sample reproducible.
2. **Equal allocation per outlet**: the size is split evenly among the outlets; the remainder goes one
   by one to the outlets in the order of their ids.
3. **Half random, half enriched** within each outlet; an odd article goes to the random half.
   - The **random** half is drawn first, from all the outlet's candidates, so it is a plain random
     sample of that outlet. The promotion criteria of ADR-0016 are measured on it.
   - The **enriched** half is drawn from the remaining candidates that match a term of
     `enrichment-terms.csv`. A purely random draw holds few sector articles; the enrichment brings
     positives and hard negatives.
   - When an outlet has too few enriched candidates, the gap is filled with more random ones, and the
     shortfall is recorded in the sample's metadata.
4. The sample is shuffled with the same seed, so a labelling session of 100 mixes outlets.
5. Each article records its stratum (`random` or `enriched`).

## `enrichment-terms.csv`

`stem, sector_id, match, language`. Text is compared without accents and in lower case. `prefix`
matches a word that starts with the stem (`hospital` matches `hospitales`); `word` matches the whole
word only, for acronyms (`fp`, `mir`, `vpo`).

**Broad on purpose.** It is not a classifier and is never used to label: it only decides which
articles may enter the enriched half. It catches articles the rules classifier misses
(`data/classification/`) and articles that are not about policy at all (an illness in a hospital,
a flat for sale): both are useful to label. Its version (a hash of the file) is recorded with each
sample, so the test and training sets can be compared to the terms they were drawn with.

Written on 2026-10-14 from the sector boundaries of `docs/labelling-guide.md`, in Spanish and
Catalan; reviewed and accepted by the author on 2026-10-15, before the first sample is drawn. A
term can be added later: it only changes the samples drawn afterwards, and each sample records the
version of the list it used.

## What is stored

- In git, `data/<set>/<sample>.jsonl`: one line per article with its id, outlet, URL and stratum;
  and `<sample>.meta.json`: the seed, the cut-off, the size, the allocation, the shortfalls and the
  version of the enrichment terms. Never a headline or a lead.
- Out of git, `var/labelstudio/<sample>.json`: the Label Studio tasks, with the headline and the lead
  only. The outlet is not shown to the person labelling (`docs/labelling-guide.md`).

## From Label Studio to the labelled set

After each session of 100 (and after the second pass over the `unsure` ones), export the project from
Label Studio as **JSON** (Export → JSON, not "JSON-MIN") and save it under `var/labelstudio/`, which
is out of git: the export carries the headlines and the leads.

```bash
uv run python -m datos.classification export-labels --set train \
  --sample train-sample-v1 --export var/labelstudio/export.json
```

It writes `data/train/train-set-v1.jsonl` (`data/eval/test-set-v1.jsonl` with `--set eval`): one line
per answered article with its id, stratum, `communities`, `sectors`, `government_levels` and
`unsure`. Never the text.

- The stratum comes from the sample file, not from the tool.
- An answer with nothing chosen is a row with no labels ("none of these", as the guide says); a
  skipped article, or one not answered yet, is named in the summary and left out.
- It stops, naming the article, on: an article twice in the export or not in the sample, an article
  with more than one answer (keep one in the tool), a sector, level or community outside the
  vocabulary, or a field the interface does not have.
- The file is rewritten whole and sorted by article id: the same answers give the same bytes, and the
  file's hash is what a model's card records as the labels it was trained on. Export again after
  every session; the final file is the one after the second pass.
- `tests/fixtures/labelstudio/export.json` has the shape of an export but was written by hand, not
  captured: check the first real export against it.
