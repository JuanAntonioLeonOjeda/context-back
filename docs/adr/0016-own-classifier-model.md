# ADR-0016: The own classifier: SetFit on a multilingual encoder, sectors and levels, promotion set before training

- **Status:** Accepted
- **Date:** 2026-10-14
- **Phase:** news-live

## Context

ADR-0008 decided that labels come from rules first and then from the author's own model, trained on
hand labels, never from an LLM. ADR-0015 put both behind one `ArticleClassifier` port and stores every
classification with its classifier and version. The rules run today; this ADR decides the model: which
encoder, which labels it takes over, how its training sample is drawn and, before any training, what
it must prove to replace the rules.

Constraints that shape it:

- **Spanish and Catalan.** 3Cat publishes in Catalan; Spanish-only encoders are out (ADR-0008).
- **Small hand-labelled data.** 400 training labels to start, in sessions of 100, grown only while the
  learning curve still rises (D2 of the phase plan). The blind test set has 200 articles, ~14 per
  outlet, half random and half enriched by broad sector keywords, each with its stratum
  (`specs/foundation/plan.md`).
- **No GPU and no external service.** Training and batch classification run on the author's machine,
  as jobs; never in the API image.
- **Where the rules are weak.** Sector keywords mix policy with noise (an illness at a wedding, news
  from Hungary) and levels are rarely named (`data/classification/README.md`); communities, from a
  gazetteer of places and institutions, are the rules' strong part.

## Options considered

### Encoder
- **A — `paraphrase-multilingual-mpnet-base-v2`** (chosen): Apache-2.0; trained on 50+ languages,
  Catalan among them; 768-dimension vectors, 0.3 B parameters.
  - Pros: the best quality of the multilingual paraphrase encoders checked; a permissive licence; the
    standard choice for SetFit.
  - Cons: the slowest of the three on a CPU; reads 128 tokens, so a long lead is cut.
- **B — `paraphrase-multilingual-MiniLM-L12-v2`**: same licence and languages, 384 dimensions,
  0.1 B parameters.
  - Pros: about three times smaller; faster to train and to run.
  - Cons: lower quality. Kept as the fallback if A is too slow to train on the author's CPU, measured
    and not assumed.
- **C — `multilingual-e5-small`**: MIT; lists Catalan.
  - Cons: needs `query:` and `passage:` prefixes; its size and details could not be checked from its
    card on 2026-10-14.

### What the model labels
- **A — sectors and government levels; communities stay with the rules** (chosen).
  - Pros: the model works where keywords fail; the gazetteer keeps what it does well, and the label
    the model must learn is smaller.
  - Cons: the stored labels of an article come from two classifiers (see Consequences).
- **B — all three families.** Cons: more labels to learn from 400 examples, in the family where the
  rules are already good.
- **C — sectors only.** Cons: levels decide the attribution (ADR-0014); leaving them to keywords
  leaves most articles "not determined".

### When the training sample is drawn
- **A — on 2026-10-21, after a week of collection** (chosen), with the stratification of the test set
  (equal per outlet, half random and half enriched by broad sector keywords, stratum recorded, fixed
  seed), and disjoint from the test set by construction and by a test.
  - Pros: more days, more distinct stories; one day of news repeats the same story across outlets.
  - Cons: a week later than possible.
- **B — now (two days of collection).** Cons: the sample would repeat few stories, and the model
  would learn those.

### How promotion is decided
- **A — criteria set by the author before training, per label family** (chosen).
- **B — decide after seeing the results.** Cons: any threshold chosen after the numbers can be bent
  to them.

## Decision

The own model is **SetFit on `paraphrase-multilingual-mpnet-base-v2`**, multi-label (one-vs-rest) for
two families: **sectors** (education, health, housing) and **government levels** (state, regional,
local). Communities stay with the rules. Its input is the headline and the lead, cut at the encoder's
128 tokens. If training on the author's CPU proves too slow, the fallback is
`paraphrase-multilingual-MiniLM-L12-v2`, and that change is recorded here.

The training sample is drawn on 2026-10-21 as described in option A above, and labelled by the author
in Label Studio with no proposals, in sessions of 100 (`data/train/train-set-v1.jsonl`).

**Promotion, set by the author on 2026-10-14, before any training.** On the blind test set, for each
family separately, with the attribution of each article computed by ADR-0014's rule from the labels
(the gold labels for the reference, the predicted ones for each classifier), the model replaces the
rules for that family only if all three hold:

1. **Better overall.** Its macro-F1 on the **random half** of the test set is at least **5 points**
   above that of the rules. The random half is used because the enriched half was drawn with
   keywords and favours a keyword classifier.
2. **No outlet left behind.** For every outlet, the number of its articles whose labels of that family
   are exactly right is no more than **2** below that of the rules. The threshold is in articles,
   not in a percentage: with ~14 articles per outlet, a percentage jumps with each article.
3. **No party wronged.** For every party, the number of articles that the model's labels attribute to
   it with "high" confidence and the gold labels do not is **not higher** than with the rules.

A family that fails stays with the rules. The decision is per family, so the model can take sectors
and leave levels, or the reverse.

The three numbers (5 points, 2 articles, no increase) were proposed by the assistant as a starting
point and accepted by the author; they are the author's to defend and to change before training, never
after.

## Consequences

- What gets easier: the model is measured against the rules on the same test set, by the same code,
  overall, per outlet and per party; a family is promoted or not by a rule written in advance, so the
  result cannot be argued into a pass.
- What gets harder / what we accept:
  - The stored labels of an article can come from two classifiers (communities from the rules, sectors
    or levels from the model). That needs one more adapter behind the `ArticleClassifier` port, a
    composite with its own id and a version made of both versions (ADR-0015 fits it).
  - The test set is small: ~100 random articles, few positives per sector. A 5-point margin can be
    within the noise; the evaluation reports a 95 % bootstrap interval next to each metric, and the
    criteria apply to the point estimates, as decided.
  - A new dependency group (`ml`: `setfit`, `sentence-transformers`, `torch` for CPU), never in the API
    image; pinned versions, licences checked when added (task 17).
  - Weights stay out of git, in `models/`, named by training-set version, encoder and seed; a model
    that cannot be retrained from the repository and the database is not promoted.
- What would make us revisit this: a learning curve still rising at 400 examples (grow the sample
  before deciding); intervals wider than the 5-point margin (a larger test set, v2); a test set that
  shows the rules wrong on communities (then the model takes them too, by a new decision).

## Implementation decisions (2026-10-15)

Decided by the author before writing the model's code (task 17):

- **Threshold**: a label is assigned when its probability is at least **0.5**, fixed and written in
  the model's metadata. Tuning it by cross-validation on 400 articles (some 50 to 60 per sector)
  would give a noisy threshold; it is never tuned on the test set.
- **What the model stores as evidence**: the probability of each label it gives, in a `scores`
  field of `Labels`; a model has no term to point at, and an empty term would satisfy the contract
  test while saying nothing.
- **The model's version**: a hash of its weights file, because training on a CPU is not exact to
  the bit; the metadata records the training set, the encoder, the seed and the library versions.
- **Tests without network or GPU**: the adapter's logic is tested with a fake predictor; the test
  with SetFit itself is marked `ml` and does not run in CI.
- **Where the model classifies once promoted**: not decided yet; training runs on the author's
  machine with `uv`. After task 18, a separate image for the jobs with the `ml` group, so the API
  image stays small.
- **Composite classifier**: what is stored and read once the model takes a family. It takes each
  family from its assigned classifier, keeps only the evidence of those families, and its version
  names the source of every family (`communities=rules@…;sectors=setfit@…;levels=…`).
- **The `ml` group and its versions** (measured 2026-10-15): `setfit==1.2.0` with the ranges its
  maintainers test against (`transformers<5`, `sentence-transformers<6`, `huggingface-hub<1`,
  `datasets<5`), and upper bounds on eight transitive packages that were less than two weeks old
  (`constraint-dependencies` in `pyproject.toml`; a global `exclude-newer` does not resolve for every
  Python the project supports). 62 packages, none newer than 2026-10-01; no locked package moved.
  The group is not a default one and is not in the API image: tests check it, and the built image
  (452 MB) has no torch. The virtual environment grows from 191 MB to 1.1 GB.
- **Training speed**: on the author's Mac, torch uses MPS (the Apple GPU). A tiny model (12 examples)
  trains in 18 s with the encoder cached; the first run also downloads the encoder (about 1.2 GB).
  The real figure with 400 examples is measured by the training job (unit 4), and decides whether
  MiniLM is needed.
- **Contrastive pairs, measured 2026-10-15**: SetFit 1.2.0 oversamples by default, so 400 examples
  give 89,168 pairs; at the measured 1.9 pairs/s (40 examples, 400 pairs, 227 s on MPS) that is
  about 13 hours. The training job fixes `num_iterations=20`: 16,000 pairs for 400 examples, about
  2.4 hours. The count is printed before training (`train --dry-run`) and stored in the model
  card. This corrects an earlier note that gave 20 iterations as SetFit's own default.
- **The learning curve** (decided 2026-10-15, before any training): it is measured inside the
  training set, never on the test set. The set is split in 4 folds by stratum with a fixed seed;
  with one fold held out, the model is trained on nested subsets of 100, 200 and 300 of the rest
  and its macro-F1 per family is measured on the held-out fold. With 400 labels there is no point
  at 400: some articles are always held out. Two of the four folds are run (about 7 hours with
  mpnet, one night); each point is stored as it ends, so a run can be resumed and the other two
  folds added later. mpnet, not MiniLM, because the curve must describe the model that is
  trained.
- **When the curve "still rises"**: 100 more articles are labelled when the mean macro-F1 over the
  folds run rises by **at least 3 points from 200 to 300**, in either family. Proposed by the
  assistant and accepted by the author before seeing any curve; with 100 held-out articles a
  smaller rise is within the noise.
- **No MLflow for now**: a dozen trainings at most; the model's metadata and the versioned
  evaluation report are enough, and a model registry would be a second source of truth next to
  this ADR. The metadata keeps the fields MLflow would log, so adding it later is cheap. Revisit
  with periodic retraining, a hyperparameter search or a second model.

## Verification

- Encoders: Hugging Face model cards of `paraphrase-multilingual-mpnet-base-v2` and
  `paraphrase-multilingual-MiniLM-L12-v2` (licence Apache-2.0, vector size, 128-token limit,
  parameters) and the Sentence Transformers documentation, "Pretrained Models" (the 50+ training
  languages, Catalan included), read on 2026-10-14. `multilingual-e5-small`: card front matter (MIT,
  Catalan listed); the rest not read.
- Where the rules are weak: `data/classification/README.md`, coverage of 2026-10-14.
- The test set method and its strata: `specs/foundation/plan.md`, "Blind test set method".
- The criteria are applied by the evaluation of task 18 (`specs/news-live/tasks.md`).
