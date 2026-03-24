# ADR 0010: Label Map Empty Line Handling

**Date:** 2026-03-24
**Status:** Accepted

## Context

The label map file is a plain text file with one label per line. The file may contain blank or whitespace-only lines. The question is how to handle them: skip them (and renumber indices), or preserve them as empty strings in the lookup table?

## Decision

Every line, including blank and whitespace-only lines, **consumes one index slot**. Blank lines are stored as empty strings (`""`) in the label map. The index of each line in the file is its index in the label map, regardless of whether the line is blank.

**Example:**
```
person         ← index 0: "person"
bicycle        ← index 1: "bicycle"
car            ← index 2: "car"
               ← index 3: "" (blank line)
motorcycle     ← index 4: "motorcycle"
```

Parsed result: `{0: "person", 1: "bicycle", 2: "car", 3: "", 4: "motorcycle"}`

## Rationale

- **Index alignment with model output** — inference models output raw integer class indices (0, 1, 2, 3, ...). These indices must map directly to label file line numbers without renumbering. If the label file has a blank line at index 3, then a model output of `3` must resolve to the empty string, not skip over it to index `4`.
- **Tight coupling to training** — the label map file is usually generated alongside a trained model. The model's class indices are determined by the training dataset's label order. Skipping blank lines in the label map would cause a mismatch if the training data also has gaps (e.g., classes [0, 1, 2, 4] if class 3 was removed).
- **No ambiguity in parsing** — every line is either a label or empty; no "skip" rule introduces ambiguity.

## Error Handling

If a raw model output references an index that corresponds to an empty string in the label map:

- **No automatic skip** — the empty string is returned as-is.
- **ParseError if label map is all empty** — if the label map file exists but contains no non-blank lines, `ParseError` is raised because the label map is useless (InferenceEngine cannot resolve any class to a meaningful label).
- **Downstream validation** — the Detection Pipeline or Stream API may choose to filter out detections with empty labels before returning results, but `InferenceEngine.detect()` does not do this automatically.

## Why Not Skip Blank Lines?

The alternative of skipping blank lines and renumbering introduces:

1. **Index mismatch** — model output `3` would map to "motorcycle" instead of empty-string or cause an IndexError.
2. **Hidden bugs** — an off-by-one error in label map generation would silently mislabel detections without clear error signals.
3. **Training-inference coupling** — the training pipeline and the label map must stay in sync; skipping lines breaks this contract.

## Alternatives Considered

- **Skip blank lines, renumber indices** — rejected for the alignment reasons above.
- **Trim trailing blank lines only** — rejected because trailing blanks are not special; they should be handled the same as leading or interior blanks.
- **Require a non-empty label on every line** — too restrictive and doesn't reflect real training workflows.

## Consequences

- Label map files must be generated with care to match model training class indices exactly.
- Test fixtures must include label maps with intentional blank lines if that scenario is to be verified.
- If a model outputs an out-of-range index (e.g., 100 when the label map has only 5 lines), `ParseError` is raised; this is a configuration error, not a runtime failure.

## Superseded By / Supersedes

N/A
