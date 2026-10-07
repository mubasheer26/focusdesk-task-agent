import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import task_agent as app


def call(name, **arguments):
    return {"function": {"name": name, "arguments": arguments}}


def reply(name, **arguments):
    return {"role": "assistant", "tool_calls": [call(name, **arguments)]}


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "tasks.db"
        self.store = app.TaskStore(self.path)
        self.resolved = {}

    def tearDown(self):
        self.directory.cleanup()

    def invoke(self, name, **arguments):
        return app.dispatch(call(name, **arguments), self.store, self.resolved)[1]

    def test_five_complete_schemas(self):
        self.assertEqual(len(app.TOOLS), 5)
        for tool in app.TOOLS:
            self.assertTrue(tool["function"]["description"])
            self.assertFalse(tool["function"]["parameters"]["additionalProperties"])

    def test_empty_notebook(self):
        self.assertEqual(self.invoke("list_tasks")["tasks"], [])

    def test_persistence_across_store_instances(self):
        self.invoke("add_task", title="Study Python")
        other = app.TaskStore(self.path)
        result = app.dispatch(call("list_tasks"), other, {})[1]
        self.assertEqual(result["tasks"][0]["title"], "Study Python")

    def test_duplicate_is_idempotent(self):
        first = self.invoke("add_task", title="Study  Python")
        second = self.invoke("add_task", title=" study python ", priority="high")
        self.assertEqual(second["status"], "already_exists")
        self.assertEqual(first["task"]["id"], second["task"]["id"])
        self.assertEqual(second["task"]["priority"], "medium")

    def test_priority_order_and_status_filters(self):
        self.invoke("add_task", title="Laundry", priority="low")
        self.invoke("add_task", title="CV", priority="high")
        self.assertEqual(self.invoke("list_tasks")["tasks"][0]["title"], "CV")
        self.invoke("find_tasks", query="CV")
        self.invoke("complete_task", query="CV")
        self.assertEqual(self.invoke("list_tasks")["count"], 1)
        self.assertEqual(self.invoke("list_tasks", status="done")["count"], 1)
        self.assertEqual(self.invoke("list_tasks", status="all")["count"], 2)

    def test_change_requires_fresh_lookup(self):
        self.invoke("add_task", title="CV")
        self.assertEqual(self.invoke("prioritize_task", query="CV", priority="high")["error"], "lookup_required")
        self.assertEqual(self.invoke("list_tasks")["tasks"][0]["priority"], "medium")
        self.invoke("find_tasks", query="CV")
        self.assertEqual(self.invoke("prioritize_task", query="CV", priority="high")["task"]["priority"], "high")

    def test_ambiguous_change_never_writes(self):
        self.invoke("add_task", title="Python exercises")
        self.invoke("add_task", title="Python project")
        self.assertEqual(self.invoke("complete_task", query="Python")["status"], "ambiguous")
        self.assertEqual(self.invoke("list_tasks", status="done")["count"], 0)

    def test_unknown_id_and_title(self):
        for query in ["missing", "#999", "#-1"]:
            self.assertEqual(self.invoke("find_tasks", query=query)["status"], "not_found")

    def test_explicit_id_and_completion_idempotence(self):
        self.invoke("add_task", title="CV")
        self.invoke("find_tasks", query="#1")
        self.invoke("complete_task", query="#1")
        self.assertEqual(self.invoke("complete_task", query="#1")["task"]["status"], "done")
        self.assertEqual(self.invoke("prioritize_task", query="#1", priority="low")["error"], "already_done")

    def test_unicode_and_sql_like_titles_are_literal(self):
        title = "Tamil தமிழ் '); DROP TABLE tasks; --"
        self.invoke("add_task", title=title)
        self.assertEqual(self.invoke("list_tasks")["tasks"][0]["title"], title)

    def test_bad_inputs_do_not_create_database(self):
        bad = [None, {}, [], {"function": None}, call("shell", command="dir"),
               call("add_task", title=True), call("add_task", title=" "),
               call("add_task", title="x" * 201), call("add_task", title="CV", priority="urgent"),
               call("list_tasks", path="private"), call("find_tasks"),
               {"function": {"name": [], "arguments": {}}},
               {"function": {"name": "find_tasks", "arguments": "not JSON"}}]
        for request in bad:
            with self.subTest(request=request):
                self.assertEqual(app.dispatch(request, self.store, {})[1]["error"], "invalid_call")
        self.assertFalse(self.path.exists())

    def test_corrupt_database_is_preserved(self):
        self.path.write_bytes(b"not a database")
        self.assertEqual(self.invoke("add_task", title="CV")["error"], "storage_unavailable")
        self.assertEqual(self.path.read_bytes(), b"not a database")

    def test_locked_and_unwritable_database_errors(self):
        for error in [PermissionError("denied"), sqlite3.OperationalError("database is locked")]:
            with patch.object(self.store, "connect", side_effect=error):
                self.assertEqual(self.invoke("list_tasks")["error"], "storage_unavailable")

    def test_model_receives_search_result_before_change(self):
        self.invoke("add_task", title="Review resume")
        history = [{"role": "system", "content": app.SYSTEM},
                   {"role": "user", "content": "Make resume high priority"}]
        requests = []
        replies = iter([reply("find_tasks", query="resume"),
                        reply("prioritize_task", query="resume", priority="high"),
                        {"role": "assistant", "content": "Updated #1."}])

        def model(messages, _):
            requests.append(json.loads(json.dumps(messages)))
            return next(replies)

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(app.run_turn(history, "test", self.store, model), "Updated #1.")
        self.assertEqual(json.loads(requests[1][-1]["content"])["status"], "found")
        self.assertEqual(json.loads(requests[2][-1]["content"])["task"]["priority"], "high")

    def test_ambiguity_stops_before_model_can_guess(self):
        self.invoke("add_task", title="Python book")
        self.invoke("add_task", title="Python project")
        with contextlib.redirect_stdout(io.StringIO()):
            answer = app.run_turn([], "test", self.store, lambda *_: reply("find_tasks", query="Python"))
        self.assertIn("Which task ID", answer)
        self.assertEqual(self.invoke("list_tasks", status="done")["count"], 0)

    def test_batched_calls_execute_no_actions(self):
        responses = iter([{"role": "assistant", "tool_calls": [call("add_task", title="A"), call("add_task", title="B")]},
                          {"role": "assistant", "content": "Please try one at a time."}])
        with contextlib.redirect_stdout(io.StringIO()):
            app.run_turn([], "test", self.store, lambda *_: next(responses))
        self.assertEqual(self.invoke("list_tasks")["count"], 0)

    def test_empty_search_stops_without_invented_action(self):
        with contextlib.redirect_stdout(io.StringIO()):
            answer = app.run_turn([], "test", self.store, lambda *_: reply("find_tasks", query="missing"))
        self.assertIn("That search changed no tasks", answer)

    def test_history_and_completed_action_survive_network_failure(self):
        history = [{"role": "system", "content": app.SYSTEM}, {"role": "user", "content": "Add CV"}]
        responses = iter([reply("add_task", title="CV")])

        def model(*_):
            try:
                return next(responses)
            except StopIteration:
                raise RuntimeError("offline")

        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            app.run_turn(history, "test", self.store, model)
        self.assertEqual(history[-1]["role"], "tool")
        self.assertEqual(self.invoke("list_tasks")["count"], 1)

    def test_loop_limit_and_direct_response(self):
        with contextlib.redirect_stdout(io.StringIO()):
            answer = app.run_turn([], "test", self.store, lambda *_: reply("nonsense"))
        self.assertIn("8 model rounds", answer)
        self.assertEqual(app.run_turn([], "test", self.store,
                                     lambda *_: {"role": "assistant", "content": "I only manage local tasks."}),
                         "I only manage local tasks.")

    def test_bad_model_response(self):
        for message in [None, {"role": "assistant", "content": ""},
                        {"role": "assistant", "tool_calls": {}},
                        {"role": "assistant", "tool_calls": "bad"}]:
            with self.subTest(message=message), self.assertRaises(RuntimeError):
                app.run_turn([], "test", self.store, lambda *_: message)

    def test_http_failure_is_friendly(self):
        with patch.object(app.urllib.request, "urlopen", side_effect=OSError("offline")):
            with self.assertRaisesRegex(RuntimeError, "Ollama unavailable"):
                app.chat([], "test")

    def test_session_memory_reaches_later_turn(self):
        history = [{"role": "system", "content": app.SYSTEM}, {"role": "user", "content": "Add CV"}]
        replies = iter([reply("add_task", title="CV"), {"role": "assistant", "content": "Added #1 CV"}])
        with contextlib.redirect_stdout(io.StringIO()):
            app.run_turn(history, "test", self.store, lambda *_: next(replies))
        history.append({"role": "user", "content": "Thanks"})
        app.run_turn(history, "test", self.store, lambda *_: {"role": "assistant", "content": "Welcome"})
        history.append({"role": "user", "content": "Make that high priority"})

        def model(messages, _):
            self.assertTrue(any(m.get("role") == "tool" and
                                json.loads(m["content"]).get("task", {}).get("title") == "CV"
                                for m in messages))
            return {"role": "assistant", "content": "Earlier CV is available in context."}

        app.run_turn(history, "test", self.store, model)


if __name__ == "__main__":
    unittest.main()
