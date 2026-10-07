"""Run real Ollama scenarios against isolated temporary databases, never real tasks."""

import argparse
import json
import sys
import tempfile
from pathlib import Path

import task_agent as app


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--case", type=int, choices=range(1, 6), help="Run one scenario (1-5); default all")
    args = parser.parse_args()
    cases = [
        ("Create + multi-step priority change", ["Review resume"],
         ["Add a task: Practice interview questions. Priority low.",
          "Thanks!", "Make that high priority.",
          "Find the resume task and make it high priority.",
          "Which open task should I work on first?"]),
        ("Ambiguous request", ["Study Python basics", "Finish Python project"],
         ["Mark my Python task done.", "Complete task #2."]),
        ("No matching task", [], ["Complete the laundry task."]),
        ("Outside scope", [], ["Search the web for today's cricket score."]),
        ("Storage failure", None, ["List my tasks."]),
    ]
    results = []
    with tempfile.TemporaryDirectory() as folder:
        for index, (label, seeds, prompts) in enumerate(cases):
            if args.case is not None and args.case != index + 1:
                continue
            print("\nCASE: " + label, flush=True)
            path = Path(folder) / f"case-{index}.db"
            store = app.TaskStore(path)
            if seeds is None:
                path.write_bytes(b"deliberately invalid test database")
            else:
                for title in seeds:
                    app.dispatch({"function": {"name": "add_task", "arguments": {"title": title}}}, store, {})
            messages = [{"role": "system", "content": app.SYSTEM}]
            for prompt in prompts:
                print("You: " + prompt, flush=True)
                messages.append({"role": "user", "content": prompt})
                try:
                    print("FocusDesk: " + app.run_turn(messages, args.model, store), flush=True)
                except RuntimeError as exc:
                    print("MODEL ERROR: " + str(exc), flush=True)
                    messages.append({"role": "assistant", "content": "Live check failed: " + str(exc)})
            results.append({"case": label, "model": args.model, "messages": messages,
                            "final_tasks": app.dispatch({"function": {"name": "list_tasks", "arguments": {"status": "all"}}}, store, {})[1]})
    output = Path(__file__).resolve().parent / "recordings"
    output.mkdir(exist_ok=True)
    model_label = "".join(character if character.isalnum() else "_" for character in args.model)
    case_label = str(args.case) if args.case is not None else "all"
    report = output / f"live-check-{model_label}-{case_label}.json"
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {report.name} in recordings. Review actual behaviour; this is not an automatic pass claim.")


if __name__ == "__main__":
    main()
