import unittest
from brainfile import (
    Board,
    Column,
    Task,
    Contract,
    Deliverable,
    ValidationConfig,
    setTaskContract,
    clearTaskContract,
    setTaskContractStatus,
    patchTaskContract,
    addTaskContractDeliverable,
    removeTaskContractDeliverable,
    addTaskContractValidationCommand,
    removeTaskContractValidationCommand,
    addTaskContractConstraint,
    removeTaskContractConstraint,
)

class TestContractOperations(unittest.TestCase):
    def setUp(self):
        self.task = Task(id="task-1", title="Task 1")
        self.column = Column(id="todo", title="To Do", tasks=[self.task])
        self.board = Board(title="Test Board", columns=[self.column])

    def test_set_clear_contract(self):
        contract = Contract(status="ready", constraints=["Must work"])
        res = setTaskContract(self.board, "task-1", contract)
        self.assertTrue(res.success)
        self.assertEqual(res.board.columns[0].tasks[0].contract.status, "ready")
        
        # Clear contract
        res = clearTaskContract(res.board, "task-1")
        self.assertTrue(res.success)
        self.assertIsNone(res.board.columns[0].tasks[0].contract)

    def test_set_contract_status(self):
        contract = Contract(status="draft")
        res = setTaskContract(self.board, "task-1", contract)
        
        res = setTaskContractStatus(res.board, "task-1", "ready")
        self.assertTrue(res.success)
        self.assertEqual(res.board.columns[0].tasks[0].contract.status, "ready")

    def test_patch_contract(self):
        contract = Contract(status="draft")
        res = setTaskContract(self.board, "task-1", contract)
        
        patch = {"status": "in_progress", "constraints": ["C1"]}
        res = patchTaskContract(res.board, "task-1", patch)
        self.assertTrue(res.success)
        c = res.board.columns[0].tasks[0].contract
        self.assertEqual(c.status, "in_progress")
        self.assertEqual(c.constraints, ["C1"])

    def test_manage_deliverables(self):
        contract = Contract(status="ready")
        res = setTaskContract(self.board, "task-1", contract)
        
        # Add deliverable
        d = Deliverable(type="file", path="src/app.py", description="The app")
        res = addTaskContractDeliverable(res.board, "task-1", d)
        self.assertTrue(res.success)
        self.assertEqual(len(res.board.columns[0].tasks[0].contract.deliverables), 1)
        
        # Remove deliverable
        res = removeTaskContractDeliverable(res.board, "task-1", "src/app.py")
        self.assertTrue(res.success)
        self.assertIsNone(res.board.columns[0].tasks[0].contract.deliverables)

    def test_manage_validation_commands(self):
        contract = Contract(status="ready", validation=ValidationConfig(commands=["pytest"]))
        res = setTaskContract(self.board, "task-1", contract)
        
        # Add command
        res = addTaskContractValidationCommand(res.board, "task-1", "ruff check")
        self.assertTrue(res.success)
        self.assertEqual(res.board.columns[0].tasks[0].contract.validation.commands, ["pytest", "ruff check"])
        
        # Remove command
        res = removeTaskContractValidationCommand(res.board, "task-1", "pytest")
        self.assertTrue(res.success)
        self.assertEqual(res.board.columns[0].tasks[0].contract.validation.commands, ["ruff check"])

    def test_manage_constraints(self):
        contract = Contract(status="ready", constraints=["C1"])
        res = setTaskContract(self.board, "task-1", contract)
        
        # Add constraint
        res = addTaskContractConstraint(res.board, "task-1", "C2")
        self.assertTrue(res.success)
        self.assertEqual(res.board.columns[0].tasks[0].contract.constraints, ["C1", "C2"])
        
        # Remove constraint
        res = removeTaskContractConstraint(res.board, "task-1", "C1")
        self.assertTrue(res.success)
        self.assertEqual(res.board.columns[0].tasks[0].contract.constraints, ["C2"])

if __name__ == "__main__":
    unittest.main()
