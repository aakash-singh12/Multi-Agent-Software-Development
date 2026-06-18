import unittest
import os
import shutil
import asyncio
from backend.bus import MessageBus
from backend.sandbox import WorkspaceSandbox
from backend.llm import LLMClient

class TestMessageBus(unittest.TestCase):
    def setUp(self):
        self.bus = MessageBus()

    def test_publish_and_history(self):
        async def run_test():
            await self.bus.publish(
                sender="planner",
                event_type="test_event",
                message="Test log message",
                payload={"data": "value"}
            )
            
        asyncio.run(run_test())
        
        history = self.bus.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["sender"], "planner")
        self.assertEqual(history[0]["message"], "Test log message")
        self.assertEqual(history[0]["payload"]["data"], "value")

    def test_listener_callback(self):
        received_events = []
        
        def listener(event):
            received_events.append(event)
            
        self.bus.register_listener(listener)
        
        async def run_test():
            await self.bus.publish("system", "info", "Hello World")
            
        asyncio.run(run_test())
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0]["message"], "Hello World")


class TestWorkspaceSandbox(unittest.TestCase):
    def setUp(self):
        self.sandbox_dir = "test_workspace_sandbox"
        self.sandbox = WorkspaceSandbox(self.sandbox_dir)

    def tearDown(self):
        if os.path.exists(self.sandbox_dir):
            shutil.rmtree(self.sandbox_dir)

    def test_file_write_read(self):
        file_path = "subdir/test_file.py"
        content = "print('hello')"
        
        saved_path = self.sandbox.write_file(file_path, content)
        self.assertEqual(saved_path, "subdir/test_file.py")
        
        read_content = self.sandbox.read_file(file_path)
        self.assertEqual(read_content, content)

    def test_path_traversal_protection(self):
        with self.assertRaises(PermissionError):
            self.sandbox.read_file("../some_external_file.txt")

    def test_execute_test(self):
        # Write a dummy test case inside sandbox
        test_code = """import unittest
class DummyTest(unittest.TestCase):
    def test_success(self):
        self.assertTrue(True)
"""
        self.sandbox.write_file("test_dummy.py", test_code)
        
        # Execute test
        res = self.sandbox.execute_test("test_dummy.py")
        self.assertTrue(res["success"])
        self.assertEqual(res["exit_code"], 0)


class TestLLMClientSimulation(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient(provider="simulation")

    def test_simulation_responses(self):
        async def run_test():
            planner_res = await self.client.generate("planner", "some prompt")
            self.assertIn("tasks", planner_res)
            
            engineer_res = await self.client.generate("engineer", "some prompt")
            self.assertIn("code", engineer_res)
            
            reviewer_res = await self.client.generate("reviewer", "some prompt")
            self.assertIn("approved", reviewer_res)
            
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
