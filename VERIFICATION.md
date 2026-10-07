# Verification — 6–7 October 2026

## Deterministic application tests

Run from this folder: `python -m unittest discover -s tests -v`.
All 23 tests passed on 7 October 2026, including Qwen response-format handling. Tests use temporary databases and scripted model replies, not a real model.
They exercise input validation, persistent data, priority order, status filtering,
duplicate prevention, ambiguous matches, lookup-before-write, storage errors,
loop limits, HTTP failure, and preservation of completed actions after failure.

## First real-model run: llama3.2

The initial installed model was tested through `python live_check.py`.

| Scenario | Observation |
| --- | --- |
| Add task | Correct add_task call and saved row |
| Search then prioritize | Found the task, but emitted JSON-looking text instead of a real second tool call; priority was not changed |
| Ambiguous Python task | Application stopped with both candidate IDs; no mutation |
| User selected #2 | Model skipped lookup, got lookup_required, and then gave an incorrect no-results reply; no mutation |
| Missing laundry task | Correct application no-results response |
| Outside-scope cricket query | Model unnecessarily searched local tasks instead of clearly stating its boundary |
| Invalid temporary database | Correct storage error; existing bytes preserved |

These results are why deterministic tests alone are insufficient. No failed
model workflow is described as a successful update. A second model evaluation is
being prepared; this report will be updated with its actual outcome.

## Qwen3 configuration

The default model is now qwen3:4b. The client requests non-thinking mode and
removes legacy thinking markup from final responses. The complete real-model
scenario run is still in progress; no full live-pass claim is made yet.
