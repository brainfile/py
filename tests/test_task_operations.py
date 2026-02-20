import os
import shutil
import tempfile
import unittest
from brainfile import (
    addTaskFile,
    moveTaskFile,
    completeTaskFile,
    deleteTaskFile,
    appendLog,
    listTasks,
    findTask,
    searchTaskFiles,
    searchLogs,
    readTaskFile,
    generateNextFileTaskId,
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
        result = addTaskFile(self.board_dir, {"title": "Task 1", "column": "todo"})
        self.assertTrue(result["success"])
        self.assertEqual(result["task"].title, "Task 1")
        self.assertTrue(os.path.exists(result["filePath"]))
        
        doc = readTaskFile(result["filePath"])
        self.assertEqual(doc.task.title, "Task 1")
        self.assertEqual(doc.task.column, "todo")

    def test_generate_next_id(self):
        addTaskFile(self.board_dir, {"id": "task-1", "title": "T1", "column": "todo"})
        next_id = generateNextFileTaskId(self.board_dir)
        self.assertEqual(next_id, "task-2")

        addTaskFile(self.board_dir, {"id": "epic-5", "title": "E5", "column": "todo", "type": "epic"})
        next_epic_id = generateNextFileTaskId(self.board_dir, typePrefix="epic")
        self.assertEqual(next_epic_id, "epic-6")

    def test_move_task_file(self):
        res = addTaskFile(self.board_dir, {"title": "Task 1", "column": "todo"})
        path = res["filePath"]
        
        move_res = moveTaskFile(path, "done", newPosition=5)
        self.assertTrue(move_res["success"])
        self.assertEqual(move_res["task"].column, "done")
        self.assertEqual(move_res["task"].position, 5)
        
        doc = readTaskFile(path)
        self.assertEqual(doc.task.column, "done")

    def test_complete_task_file(self):
        res = addTaskFile(self.board_dir, {"title": "Task 1", "column": "todo"})
        path = res["filePath"]
        
        comp_res = completeTaskFile(path, self.logs_dir)
        self.assertTrue(comp_res["success"])
        self.assertFalse(os.path.exists(path))
        self.assertTrue(os.path.exists(comp_res["filePath"]))
        self.assertIsNotNone(comp_res["task"].completed_at)
        
        # Check it's in logs
        docs = searchLogs(self.logs_dir, "Task 1")
        self.assertEqual(len(docs), 1)

    def test_complete_epic_with_children(self):
        # Create epic
        epic_res = addTaskFile(self.board_dir, {
            "id": "epic-1", 
            "title": "Epic 1", 
            "column": "todo", 
            "type": "epic",
            "subtasks": ["task-1", "task-2"]
        })
        
        # Create children
        addTaskFile(self.board_dir, {"id": "task-1", "title": "Child 1", "column": "todo", "parentId": "epic-1"})
        addTaskFile(self.board_dir, {"id": "task-2", "title": "Child 2", "column": "todo", "parentId": "epic-1"})
        
        comp_res = completeTaskFile(epic_res["filePath"], self.logs_dir)
        self.assertTrue(comp_res["success"])
        
        doc = readTaskFile(comp_res["filePath"])
        self.assertIn("## Child Tasks", doc.body)
        self.assertIn("task-1: Child 1", doc.body)
        self.assertIn("task-2: Child 2", doc.body)

    def test_delete_task_file(self):
        res = addTaskFile(self.board_dir, {"title": "Task 1", "column": "todo"})
        path = res["filePath"]
        
        del_res = deleteTaskFile(path)
        self.assertTrue(del_res["success"])
        self.assertFalse(os.path.exists(path))

    def test_append_log(self):
        res = addTaskFile(self.board_dir, {"title": "Task 1", "column": "todo"})
        path = res["filePath"]
        
        appendLog(path, "First log", agent="otto")
        doc = readTaskFile(path)
        self.assertIn("## Log", doc.body)
        self.assertIn("[otto]: First log", doc.body)
        
        appendLog(path, "Second log")
        doc = readTaskFile(path)
        self.assertIn("Second log", doc.body)
        self.assertEqual(doc.body.count("## Log"), 1)

    def test_list_and_find_tasks(self):
        addTaskFile(self.board_dir, {"id": "t1", "title": "Apple", "column": "todo", "priority": "high"})
        addTaskFile(self.board_dir, {"id": "t2", "title": "Banana", "column": "done", "tags": ["fruit"]})
        
        all_tasks = listTasks(self.board_dir)
        self.assertEqual(len(all_tasks), 2)
        
        todo_tasks = listTasks(self.board_dir, filters={"column": "todo"})
        self.assertEqual(len(todo_tasks), 1)
        self.assertEqual(todo_tasks[0].task.id, "t1")
        
        found = findTask(self.board_dir, "t2")
        self.assertIsNotNone(found)
        self.assertEqual(found.task.title, "Banana")

    def test_search_tasks(self):
        addTaskFile(self.board_dir, {"title": "Fix bug", "column": "todo"}, body="Found in production")
        addTaskFile(self.board_dir, {"title": "Add feature", "column": "todo"}, body="Requested by user")
        
        results = searchTaskFiles(self.board_dir, "production")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].task.title, "Fix bug")
        
        results = searchTaskFiles(self.board_dir, "feature")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].task.title, "Add feature")

if __name__ == "__main__":
    unittest.main()
