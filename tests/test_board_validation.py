import unittest

from brainfile.board_validation import (
    BoardValidationResult,
    get_board_types,
    validate_column,
    validate_type,
)
from brainfile import (
    BoardConfig,
    ColumnConfig,
    TypeEntry,
)


class TestBoardValidation(unittest.TestCase):
    def setUp(self):
        self.config = BoardConfig(
            columns=[
                ColumnConfig(id="todo", title="To Do"),
                ColumnConfig(id="done", title="Done"),
            ],
            strict=True,
            types={
                "epic": TypeEntry(id_prefix="epic", completable=True),
                "adr": TypeEntry(id_prefix="adr", completable=False),
            }
        )

    def test_get_board_types(self):
        types = get_board_types(self.config)
        self.assertIn("epic", types)
        self.assertIn("adr", types)
        self.assertEqual(types["epic"].id_prefix, "epic")

    def test_validate_type(self):
        # Valid types
        res = validate_type(self.config, "epic")
        self.assertTrue(res["valid"])

        res = validate_type(self.config, "task")
        self.assertTrue(res["valid"])

        # Invalid type
        res = validate_type(self.config, "bug")
        self.assertFalse(res["valid"])
        self.assertIn("bug", res["error"])
        self.assertIn("Available types: task, epic, adr", res["error"])

        # Not strict - everything valid
        config2 = BoardConfig(columns=[], strict=False)
        res = validate_type(config2, "bug")
        self.assertTrue(res["valid"])

    def test_validate_column(self):
        # Valid column
        res = validate_column(self.config, "todo")
        self.assertTrue(res["valid"])

        # Invalid column
        res = validate_column(self.config, "backlog")
        self.assertFalse(res["valid"])
        self.assertIn("backlog", res["error"])
        self.assertIn("Available columns: todo, done", res["error"])

        # Not strict - everything valid
        config2 = BoardConfig(columns=[], strict=False)
        res = validate_column(config2, "backlog")
        self.assertTrue(res["valid"])


if __name__ == "__main__":
    unittest.main()
