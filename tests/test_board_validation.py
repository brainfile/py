import unittest

from brainfile import (
    BoardConfig,
    ColumnConfig,
    TypeEntry,
    getBoardTypes,
    validateColumn,
    validateType,
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
        types = getBoardTypes(self.config)
        self.assertIn("epic", types)
        self.assertIn("adr", types)
        self.assertEqual(types["epic"].id_prefix, "epic")

    def test_validate_type(self):
        # Valid types
        res = validateType(self.config, "epic")
        self.assertTrue(res["valid"])

        res = validateType(self.config, "task")
        self.assertTrue(res["valid"])

        # Invalid type
        res = validateType(self.config, "bug")
        self.assertFalse(res["valid"])
        self.assertIn("bug", res["error"])
        self.assertIn("Available types: task, epic, adr", res["error"])

        # Not strict - everything valid
        config2 = BoardConfig(columns=[], strict=False)
        res = validateType(config2, "bug")
        self.assertTrue(res["valid"])

    def test_validate_column(self):
        # Valid column
        res = validateColumn(self.config, "todo")
        self.assertTrue(res["valid"])

        # Invalid column
        res = validateColumn(self.config, "backlog")
        self.assertFalse(res["valid"])
        self.assertIn("backlog", res["error"])
        self.assertIn("Available columns: todo, done", res["error"])

        # Not strict - everything valid
        config2 = BoardConfig(columns=[], strict=False)
        res = validateColumn(config2, "backlog")
        self.assertTrue(res["valid"])


if __name__ == "__main__":
    unittest.main()
