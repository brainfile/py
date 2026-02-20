import unittest
from brainfile import (
    Task,
    Subtask,
    formatTaskForGitHub,
    formatTaskForLinear,
)

class TestFormatters(unittest.TestCase):
    def setUp(self):
        self.task = Task(
            id="task-1",
            title="Fix bug",
            description="The bug description",
            priority="high",
            tags=["bug", "urgent"],
            subtasks=[
                Subtask(id="st-1", title="Subtask 1", completed=True),
                Subtask(id="st-2", title="Subtask 2", completed=False),
            ],
            relatedFiles=["src/main.py"],
        )

    def test_format_github(self):
        payload = formatTaskForGitHub(self.task, {
            "boardTitle": "Test Board",
            "fromColumn": "todo",
            "extraLabels": ["automation"]
        })
        
        self.assertEqual(payload["title"], "[task-1] Fix bug")
        self.assertIn("The bug description", payload["body"])
        self.assertIn("- [x] Subtask 1", payload["body"])
        self.assertIn("- [ ] Subtask 2", payload["body"])
        self.assertIn("**Board:** Test Board", payload["body"])
        self.assertIn("**Column:** todo", payload["body"])
        self.assertIn("## Related Files", payload["body"])
        self.assertIn("`src/main.py`", payload["body"])
        
        self.assertIn("bug", payload["labels"])
        self.assertIn("urgent", payload["labels"])
        self.assertIn("priority:high", payload["labels"])
        self.assertIn("automation", payload["labels"])
        self.assertEqual(payload["state"], "closed")

    def test_format_linear(self):
        payload = formatTaskForLinear(self.task, {
            "boardTitle": "Test Board",
            "fromColumn": "todo",
        })
        
        self.assertEqual(payload["title"], "Fix bug") # Linear defaults to no ID
        self.assertIn("The bug description", payload["description"])
        self.assertIn("- [x] Subtask 1", payload["description"])
        self.assertEqual(payload["priority"], 2) # high -> 2
        self.assertIn("bug", payload["labelNames"])
        self.assertEqual(payload["stateName"], "Done")

if __name__ == "__main__":
    unittest.main()
