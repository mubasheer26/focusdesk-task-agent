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
model workflow is described as a successful update. The Qwen3 observations below record the subsequent checks.

## Qwen3 checks on 7 October 2026

The default model is qwen3:4b. The client requests non-thinking mode and
removes legacy thinking markup from final responses.

- A real add_task call saved Practice interview questions with low priority.
- A clean final response confirmed the saved task after the response-format fix.
- The initial broader run encountered a Windows terminal encoding error when the
  model returned an emoji. live_check.py now explicitly uses UTF-8 output.
- The focused rerun used `python live_check.py --case 2`.
- For two Python tasks, the model called find_tasks and the application correctly
  asked which task ID the user meant. Neither task was changed.
- The follow-up Complete task #2 encountered an Ollama request failure. Completion
  was NOT verified; the final database still contained two open tasks.

The core five-tool implementation and multi-step application flow pass automated
checks, but a complete successful real-model completion/priority workflow with
Qwen3 has not yet been established on this machine. README conversations are
illustrative, not claimed transcripts. Model behaviour and CPU response times
remain practical limitations.

Run individual scenarios with `python live_check.py --case 1` through `--case 5`,
or omit --case for the full suite. These use temporary databases, not real tasks.

## Public source verification

The public GitHub archive opened without authentication. Published task_agent.py,
README.md, LEARN_TANGLISH.md, tests/test_task_agent.py and .gitignore were compared
with local source and matched exactly before this final documentation update.
