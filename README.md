# FocusDesk — a local task-management AI agent

Keep track of study, job-search and everyday tasks through a conversational CLI.
FocusDesk uses an Ollama language model to select tools, and Python + SQLite to
store real tasks and enforce safe updates. It runs locally without an API key or
third-party Python packages.

**One use case:** personal task management. This is not a web researcher, general
assistant, or background reminder service. No emails, alarms or notifications are sent.

## Quick start

Requires Python 3.10+ and [Ollama](https://ollama.com/download).
Open Ollama and install the tools-capable model if needed:

```powershell
ollama pull qwen3:4b
```

Open a terminal in this `focusdesk` folder:

```powershell
python task_agent.py
```

Optional configuration:

```powershell
python task_agent.py --model qwen3:4b --db data/my-tasks.db
```

`/exit` quits. `/reset` clears conversation history but preserves tasks.
The default database is `data/tasks.db` beside the script. First use creates it.
You do not need to install SQLite separately. Model download needs internet;
inference uses the local Ollama endpoint afterward.

## Five tools with explicit schemas

| Tool | Parameters | Behaviour |
| --- | --- | --- |
| `add_task` | `title`, optional `priority` | Save an open task; default medium; avoid duplicate open titles |
| `list_tasks` | optional `status`: open/done/all | Read tasks, sorted high → medium → low, then ID |
| `find_tasks` | `query` | Search title words or an explicit `#ID`; identify no match or ambiguity |
| `complete_task` | `query` | Complete a uniquely found task after a lookup in this turn |
| `prioritize_task` | `query`, `priority`: high/medium/low | Change priority after a lookup in this turn |

Each schema contains a name, description, parameter types, allowed values, required
fields, and `additionalProperties: false`. Python validates the arguments again;
the schema alone is not treated as a guarantee.

## Multi-step decisions

```text
User: Find the resume task and make it high priority.
  ↓
Model requests find_tasks(query="resume")
  ↓
Python reads the database and returns a match
  ↓
Model sees that result and requests prioritize_task(query="resume", priority="high")
  ↓
Python verifies the lookup and updates the task
  ↓
Model sees the confirmed update and responds
```

If a search returns several matches, the application ends the turn with a question
listing the candidate IDs. It does not let the model pick one in the same turn.
An update without a successful lookup returns `lookup_required`. Lookup evidence
is fresh each turn, and the database is checked again when applying the update.

The model chooses the workflow. Python enforces validation, unambiguous updates,
transactions and error handling. Dependent tool calls must happen in separate
model rounds: if the model batches calls, none of that batch is executed.

## Conversation memory

The running `messages` list retains system instructions, user messages, assistant
responses, tool calls and tool results. Every model request receives this list.
Clear follow-ups such as “make that high priority” can use earlier context.
Unclear references should trigger a question. Tasks persist across restarts;
the conversation does not. Long histories are not summarized automatically.

## Five example conversations

These are illustrative walkthroughs of intended behaviour, not copied live
transcripts. Wording and model routing vary. See `VERIFICATION.md` for observations.
Each example starts with the database state described below it.

### 1. Add, find, prioritize and plan

Starting with an empty notebook:

```text
You: Add a task: Review resume. Priority medium.
Tool: add_task(title="Review resume", priority="medium") → added #1
FocusDesk: Added #1 Review resume, medium priority.

You: Find the resume task and make it high priority.
Tool: find_tasks(query="resume") → found #1
Tool: prioritize_task(query="resume", priority="high") → updated #1
FocusDesk: #1 Review resume is now high priority.

You: What should I work on first?
Tool: list_tasks(status="open") → #1 Review resume, high
FocusDesk: Start with #1 Review resume, your highest-priority open task.
```

### 2. Ambiguous task: ask, then complete

Starting with #1 Study Python basics and #2 Finish Python project:

```text
You: Mark my Python task done.
Tool: find_tasks(query="Python") → two matches
FocusDesk: Several tasks match: #1 Study Python basics (open); #2 Finish
Python project (open). Which task ID do you mean?

You: Complete task #2.
Tool: find_tasks(query="#2") → found #2
Tool: complete_task(query="#2") → updated #2
FocusDesk: Completed #2 Finish Python project.
```

### 3. Empty results: never invent a task

Starting with an empty notebook:

```text
You: List my tasks.
Tool: list_tasks() → tasks: [], count: 0
FocusDesk: You have no open tasks. What would you like to add?

You: Complete the laundry task.
Tool: find_tasks(query="laundry") → not_found
FocusDesk: No task matched that search. Please give another title or #ID.
That search changed no tasks.
```

### 4. Storage failure: preserve existing data

Starting with an unreadable, locked, or invalid database:

```text
You: List my tasks.
Tool: list_tasks() → storage_unavailable
FocusDesk: Cannot access the task database. Check file permissions or restore
a valid backup. No reset was attempted.
```

The application does not delete or replace a damaged database automatically.
Use the isolated automated test to reproduce corruption; do not damage real tasks.

### 5. Outside scope: state the boundary

```text
You: Search the web for today's cricket score.
FocusDesk: I manage local tasks and cannot search the web. I can help add,
list, prioritize or complete your tasks.

You: Remind me automatically tomorrow at 9 AM.
FocusDesk: I cannot send scheduled notifications. Would you like to save a
task instead? What should its title be?
```

## Errors and tricky inputs

- Unknown tool, missing input, extra field, wrong type or invalid priority:
  return a structured `invalid_call` observation; model may correct it.
- Empty title or a title/query longer than 200 characters: reject it.
- Several matching tasks: stop and ask for an ID without changing data.
- No match: stop with an honest no-results message.
- Duplicate open title: return the existing task, without changing its priority.
- Completed task: repeated completion is harmless; reprioritization is rejected.
- Database failure: report it without silently resetting the notebook.
- Ollama offline, missing model or malformed response: readable CLI error.
- Network failure after a successful write: the action stays saved and its result
  stays in memory, so a failed final response does not erase work.
- Repeated tool loops: stop after eight model rounds.

Tool names and arguments are logged before execution, followed by actual results.
These are execution traces, not the model's private reasoning. Task titles may
contain private information: local database and transcript folders are git-ignored.

## Verification

```powershell
python -m unittest discover -s tests -v
python live_check.py
```

The automated tests use temporary databases and scripted model replies to verify
application behaviour. They do not prove model reliability. `live_check.py` makes
real local-model requests for five scenarios, creates isolated databases, and saves
the actual messages and final task state to a model-labelled JSON file in `recordings/`.
One case deliberately uses an invalid temporary database to test failure handling.

## Files and learning guide

- `task_agent.py`: tools, SQLite storage, validation, agent loop and CLI.
- `tests/test_task_agent.py`: deterministic regression tests.
- `live_check.py`: actual-model evaluation scenarios.
- `LEARN_TANGLISH.md`: simple beginner walkthrough.
- `VERIFICATION.md`: verified results and known limitations.

## Practical limits

This is a local educational portfolio project, not a hosted multi-user service.
SQLite transactions protect writes, but the app has no accounts, encryption,
notification scheduler, bulk operations, due-date parser or task deletion tool.
Search uses case-insensitive title words, not semantic retrieval. A small language
model can still misunderstand intent or make extra calls; inspect logged results.
Application safeguards prevent ambiguous updates after an ambiguous tool result;
they do not prove the model interpreted every natural-language request correctly.

API pattern: [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling).
