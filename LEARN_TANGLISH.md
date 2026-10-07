# FocusDesk: simple Tanglish-la kathukalam

## 1. Namma enna build pannirukkom?

FocusDesk = unga personal task notebook + AI assistant. "Resume review task add
pannu", "Python task mudinjiduchu", "Important task first kaattu" nu pesalam.

AI decide pannum; Python actual work seyyum; SQLite task-ai save pannum.
AI sonna mattum task save aagiduchu-nu artham illa. Successful tool result dhaan proof.

Example: receptionist = model; office register = database; register-la write panna
rules = Python functions. Receptionist rules-ai bypass panna koodadhu.

## 2. Yen indha use case?

Five unrelated tools serkkala. Orey real problem: pending work manage pannuradhu.
Add, list, find, complete, prioritize ellame andha problem-ku useful.
Web search or notification tool illa. App close pannina reminder varadhu.

## 3. Run epdi?

Ollama open pannunga. Terminal-la indha focusdesk folder-kulla ponga:

```powershell
python task_agent.py
```

Model missing-na `ollama pull qwen3:4b`. Extra pip package/API key thevai illa.

Try: `Add a task: Review resume. Priority medium.`
Then: `Find the resume task and make it high priority.`

## 4. Imports enna seyyudhu?

- `argparse`: --model and --db terminal options read pannum.
- `json`: Python dictionary-ai API-ku JSON text-a convert pannum.
- `sqlite3`: local database read/write panna built-in module.
- `sys`: Windows terminal-la Unicode text print panna help pannum.
- `urllib.request`: local Ollama-kku HTTP request anuppum.
- `urllib.error`: HTTP errors-ai separately handle pannum.
- `closing`: database connection use mudinja close pannum.
- `Path`: file location portable-a handle pannum.

`import` na already irukkura useful code-ai namma program-la use panradhu.

## 5. SYSTEM: model-oda job description

`SYSTEM = """..."""` is a long text string. Model-oda role, allowed actions,
boundaries, ambiguity rules ellam inga irukku. Idhu Python function illa; model-kku
instructions. Model instructions-ai miss pannalaam, so Python checks-um venum.

Mukkiyamaana rules: first find; then change. Multiple tasks-na user-kitta kelunga.
Tool fail aana success-nu solladheenga. Task title-kulla instruction irundhaalum
adhai task data-a mattum treat pannunga.

## 6. schema(): tool menu card

`def schema(name, description, properties, required):` reusable helper create pannum.
Same JSON structure-ai five times ezhudhaama helper use panrom.

`name`: model call panna vendiya exact function name.
`description`: eppo andha tool use pannanum.
`properties`: accepted input fields and types.
`required`: compulsory fields.
`additionalProperties: False`: unrelated extra field allow pannaadhu.

`QUERY` query input rules store pannum. `PRIORITY` high/medium/low allowed values
store pannum. `TOOLS` five schemas-oda list. `SCHEMAS` tool name-ai key-a use panna
dictionary; validation time-la correct schema quick-a edukkalam.

## 7. clean(): text neat-a maathuradhu

```python
return " ".join(text.split())
```

`split()` extra spaces remove panni words list tharum. `join()` single space use
panni reconnect pannum. "Study  Python" and "Study Python" same title-a handle aagum.

## 8. TaskStore: database work seyyura class

Class = related data/functions oru place-la group pannuradhu.
`__init__` new TaskStore create aagumbodhu database path remember pannum.
`self.path` andha object-oda file location.

`connect()` folder missing-na create pannum; SQLite connection open pannum.
`timeout=3` database busy irundha short wait; forever hang aagadhu.
`row_factory = sqlite3.Row` database rows-ai named fields use panni read panna help.

`with closing(self.connect()) as db, db:` connection close-um transaction-um
manage pannum. Success-na commit; write exception-na rollback. Half update avoid pannum.

`CREATE TABLE IF NOT EXISTS` first use-la task table create pannum.
Each row-la id, title, priority, status irukkum.
ID automatic-a increment aagum. Status open/done; priority high/medium/low.

`BEGIN IMMEDIATE` write transaction reserve pannum. Two writers same time-la
duplicate check and insert race pannaama serialized-a execute aagum.

`rows = [dict(row) for row in ...]` database records-ai Python dictionaries list-a maathum.

## 9. add_task branch

`if name == "add_task"`: requested action add-na indha block.
Title clean pannuvom. Existing open task title case-insensitive-a match aana
existing task return pannuvom; duplicate row create panna maattom.

`next(..., None)` first matching row irundha edukkum; illaina None.
`args.get("priority", "medium")` priority missing-na medium use pannum.

`INSERT ... VALUES(?,?,?)` placeholders use pannum. User text SQL code-a execute
aagadhu; separate parameters-a database-kku pogum.
`cursor.lastrowid` newly created task ID. Result dictionary-la actual task return.

## 10. list_tasks branch

Status default open. User all ketta open/done rendu status-um return.
`tasks.sort(key=...)` high first, medium next, low last; same priority-na ID order.
`PRIORITIES.index(...)` high=0, medium=1, low=2 nu sorting number tharum.
Empty notebook-na `tasks: []`, `count: 0`. Idhu error illa; valid empty result.

## 11. Search and ambiguity

Query `#2` madhiri start aana exact ID search.
Illaina query words ellam title-la irukka-nu check pannuvom.
`casefold()` case difference ignore panna use pannuvom.

Zero matches: `not_found`.
Two or more matches: `ambiguous` plus matching tasks.
Exactly one: `found` plus task.

`resolved[query] = task["id"]` successful lookup evidence save pannum.
Indha dictionary current user turn-ku mattum. Idhu full conversation memory illa.

## 12. Complete and priority change

`resolved.get(query) != task["id"]` na model proper lookup pannala.
App `lookup_required` return pannum. Task change aagadhu.

`UPDATE tasks SET status='done' WHERE id=?` chosen task mattum complete pannum.
Prioritize-na priority column change aagum. Already done task reprioritize panna
error return; open task-ku mattum priority useful.

Model task ID guess pannaama, tool result observe panni next action edukka indha
lookup check help pannum. Data change panna munnadi database match thirumba check aagum.

## 13. dispatch(): security guard / input checker

Model output-ai direct Python function-a execute panna koodadhu.
`call["function"]`, `function["name"]` requested tool details edukkum.
Name SCHEMAS-la illa-na unknown tool error.

Arguments string-a irundha `json.loads` dictionary-a maathum.
Dictionary illa-na reject. Required field missing/extra field irundha reject.
Value string-aa, enum correct-aa, length within limit-aa nu check pannum.

Validation pass aana `store.execute(...)` actual action seyyum.
`except` blocks mistakes-ai error dictionary-a maathum; app crash aagadhu.
Database fail aana storage_unavailable. Existing file delete/reset pannaadhu.

## 14. chat(): model-kku request

`payload` includes model name, full messages, five tools, temperature=0.
Temperature 0 output variation reduce pannum; correctness guarantee pannaadhu.
`stream=False` complete reply vandha apram process pannuvom.

`json.dumps(payload).encode("utf-8")` dictionary -> JSON text -> network bytes.
Request localhost:11434/api/chat-kku pogum. Internet API key thevai illa.
`json.load(response)` reply JSON-ai Python object-a maathum.
Assistant role valid-aa check pannuvom. Server offline/bad response-na readable error.

## 15. run_turn(): agent loop

`resolved = {}`: current-turn lookup evidence empty-a start.
`for _ in range(8)`: maximum eight model rounds; endless loop avoid pannum.
`request_chat(messages, model)`: full conversation + tools model-kku pogum.

Tool call illa-na final text validate panni memory-la append and return.
Tool call irundha assistant request-ai memory-la add pannuvom.

Multiple calls same reply-la vandha none execute aagum. Sequential-a one tool
call pannu-nu error observation model-kku return. Dependent actions order safe-a irukkum.

`dispatch` result terminal-la print aagum. Tool result memory-la `role: tool`
message-a add aagum. Next loop-la model andha result paathu decide pannum.

Ambiguous result-na Python direct-a choices list create panni user-kitta question
ketkum. Model-kku innoru chance kuduthu guess panna vidaadhu.
No match/storage failure-na direct honest response; invented success avoid pannum.

`finish()` application-generated response-ai memory-la add panni return pannum.

## 16. main(): terminal conversation

Command-line options read panni store and messages create pannuvom.
`while True` user questions repeatedly receive pannum.
`input(...).strip()` terminal text read panni outside whitespace remove pannum.
`/exit` loop stop; `/reset` system message mattum preserve; blank input skip.

User message append -> run_turn -> final answer print.
Model/network error catch panni CLI continue. Already saved actions undo aagadhu.
Ctrl+C/closed input-na friendly goodbye.

`if __name__ == "__main__": main()` file directly run pannina CLI start.
Tests import pannumbodhu CLI automatically start aagadhu.

## 17. Tests purinjukalam

```powershell
python -m unittest discover -s tests -v
```

Temporary database use panrom; unga real tasks touch pannaadhu. Scripted model
replies use panna tests app logic-ai check pannum. Real model intelligent-aa behave
pannudhaa-nu prove pannaadhu. Adhukku `python live_check.py` actual Ollama test.

Important practice: two Python tasks add pannunga. "Complete Python" ketta which
ID-nu question varanum; random-a task complete aaga koodadhu.

## Interview-la simple-a sollalam

"I built a local task-management agent with five tools. The model chooses actions,
but Python validates arguments and requires a fresh lookup before changing a task.
Ambiguous matches trigger a clarification question. SQLite persists tasks, while
the message history provides session memory. I tested both application logic and
real model behaviour, and documented their differences."
