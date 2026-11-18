# Data Card

The experiment uses a bounded snapshot of AI-MO/NuminaMath-1.5 at revision `1b05109f9e5c1ad06c0663519502416c30b300f8`. Ingestion reads Parquet batches using range requests and stops after 800 rows, with a configured scan cap of 4,000. It does not download the entire corpus. The source link and upstream notices are in `THIRD_PARTY_NOTICES.md`.

The snapshot contains `problem`, `solution`, answer/validity metadata and source fields. The source-provided validity annotations identify 670 valid problems, 129 incomplete problems and one record containing multiple problems; solution annotations identify 737 valid, 61 incomplete, one NaN and one unsolved solution. All 800 sampled records are labeled `olympiads` and `synthetic=False` by the source. These descriptions apply to this bounded snapshot, not the whole dataset.

Spark trims fields, rejects null/empty problems and missing/too-short/too-long solutions, normalizes question whitespace/case for identity, removes exact normalized-question/solution duplicates, sorts the output and writes JSON. It retains 799 records. The split stage further deduplicates normalized questions regardless of their solution, leaving 798 rows: 642 training, 83 validation and 73 test. The split report records SHA-256 hashes; the live verification checks question-set disjointness.

The split uses seed 42 and a SHA-256 bucket of the normalized question. It avoids dependence on input row order and keeps duplicate question variants out of different partitions. Training also reports fully truncated examples whose response tokens cannot be supervised within 256 tokens; these are excluded rather than silently treated as usable training examples.

This pipeline's validity gate is structural. It does not discard every source record annotated incomplete or independently verify mathematical truth. The EDA and 25-row review preserve those annotations and warnings for audit. The first-row sample and its Olympiad source concentration limit representativeness, and maximum token length favors short visible completions. Expert curation, validity-based ablations and a broader unseen correctness benchmark are appropriate next experiments.

Raw stage reports, EDA distributions, the sample review, split hashes and measured throughput are DVC outputs and are copied to `reports/evidence/` for submission review.
