import os
import shutil
import tempfile
import unittest
from brainfile import (
    add_task_file,
    move_task_file,
    complete_task_file,
    delete_task_file,
    append_log,
    list_tasks,
    find_task,
    search_task_files,
    search_logs,
    read_task_file,
    generate_next_file_task_id,
)

class TestTaskOperations(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.board_dir = os.path.join(self.test_dir, "board")
        self.logs_dir = os.path.join(self.test_dir, "logs")
        os.makedirs(self.board_dir)
        os.makedirs(self.logs_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_add_task_file(self):
        result = add_task_file(self.board_dir, {"title": "Task 1", "column": "todo"})
        self.assertTrue(result["success"])
        self.assertEqual(result["task"].title, "Task 1")
        self.assertTrue(os.path.exists(result["file_path"]))

        doc = read_task_file(result["file_path"])
        self.assertEqual(doc.task.title, "Task 1")
        self.assertEqual(doc.task.column, "todo")

    def test_generate_next_id(self):
        add_task_file(self.board_dir, {"id": "task-1", "title": "T1", "column": "todo"})
        next_id = generate_next_file_task_id(self.board_dir)
        self.assertEqual(next_id, "task-2")

        add_task_file(self.board_dir, {"id": "epic-5", "title": "E5", "column": "todo", "type": "epic"})
        next_epic_id = generate_next_file_task_id(self.board_dir, type_prefix="epic")
        self.assertEqual(next_epic_id, "epic-6")

    def test_move_task_file(self):
        res = add_task_file(self.board_dir, {"title": "Task 1", "column": "todo"})
        path = res["file_path"]

        move_res = move_task_file(path, "done", new_position=5)
        self.assertTrue(move_res["success"])
        self.assertEqual(move_res["task"].column, "done")
        self.assertEqual(move_res["task"].position, 5)

        doc = read_task_file(path)
        self.assertEqual(doc.task.column, "done")

    def test_complete_task_file(self):
        res = add_task_file(self.board_dir, {"title": "Task 1", "column": "todo"})
        path = res["file_path"]

        comp_res = complete_task_file(path, self.logs_dir)
        self.assertTrue(comp_res["success"])
        self.assertFalse(os.path.exists(path))
        self.assertEqual(comp_res["file_path"], os.path.join(self.logs_dir, "ledger.jsonl"))
        self.assertTrue(os.path.exists(comp_res["file_path"]))
        self.assertIsNotNone(comp_res["task"].completed_at)

        # Ledger mode should not move markdown files into logs/
        docs = search_logs(self.logs_dir, "Task 1")
        self.assertEqual(len(docs), 0)

    def test_complete_epic_with_children(self):
        # Create epic
        epic_res = add_task_file(self.board_dir, {
            "id": "epic-1",
            "title": "Epic 1",
            "column": "todo",
            "type": "epic",
            "subtasks": ["task-1", "task-2"]
        })

        # Create children
        add_task_file(self.board_dir, {"id": "task-1", "title": "Child 1", "column": "todo", "parent_id": "epic-1"})
        add_task_file(self.board_dir, {"id": "task-2", "title": "Child 2", "column": "todo", "parent_id": "epic-1"})

        comp_res = complete_task_file(epic_res["file_path"], self.logs_dir, legacy_mode=True)
        self.assertTrue(comp_res["success"])

        doc = read_task_file(comp_res["file_path"])
        self.assertIn("## Child Tasks", doc.body)
        self.assertIn("task-1: Child 1", doc.body)
        self.assertIn("task-2: Child 2", doc.body)

    def test_delete_task_file(self):
        res = add_task_file(self.board_dir, {"title": "Task 1", "column": "todo"})
        path = res["file_path"]

        del_res = delete_task_file(path)
        self.assertTrue(del_res["success"])
        self.assertFalse(os.path.exists(path))

    def test_append_log(self):
        res = add_task_file(self.board_dir, {"title": "Task 1", "column": "todo"})
        path = res["file_path"]

        append_log(path, "First log", agent="otto")
        doc = read_task_file(path)
        self.assertIn("## Log", doc.body)
        self.assertIn("[otto]: First log", doc.body)

        append_log(path, "Second log")
        doc = read_task_file(path)
        self.assertIn("Second log", doc.body)
        self.assertEqual(doc.body.count("## Log"), 1)

    def test_list_and_find_tasks(self):
        add_task_file(self.board_dir, {"id": "t1", "title": "Apple", "column": "todo", "priority": "high"})
        add_task_file(self.board_dir, {"id": "t2", "title": "Banana", "column": "done", "tags": ["fruit"]})

        all_tasks = list_tasks(self.board_dir)
        self.assertEqual(len(all_tasks), 2)

        todo_tasks = list_tasks(self.board_dir, filters={"column": "todo"})
        self.assertEqual(len(todo_tasks), 1)
        self.assertEqual(todo_tasks[0].task.id, "t1")

        found = find_task(self.board_dir, "t2")
        self.assertIsNotNone(found)
        self.assertEqual(found.task.title, "Banana")

    def test_search_tasks(self):
        add_task_file(self.board_dir, {"title": "Fix bug", "column": "todo"}, body="Found in production")
        add_task_file(self.board_dir, {"title": "Add feature", "column": "todo"}, body="Requested by user")

        results = search_task_files(self.board_dir, "production")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].task.title, "Fix bug")

        results = search_task_files(self.board_dir, "feature")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].task.title, "Add feature")

if __name__ == "__main__":
    unittest.main()
