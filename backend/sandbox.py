import os
import shutil
import subprocess
from typing import Dict, List, Any

class WorkspaceSandbox:
    def __init__(self, workspace_path: str = "workspace"):
        # Resolve to absolute path
        self.workspace_path = os.path.abspath(workspace_path)
        os.makedirs(self.workspace_path, exist_ok=True)
        
    def _safe_path(self, relative_path: str) -> str:
        """Resolve path and ensure it stays inside the workspace directory."""
        # Clean the relative path
        relative_path = relative_path.replace("\\", "/")
        if relative_path.startswith("/"):
            relative_path = relative_path[1:]
            
        full_path = os.path.abspath(os.path.join(self.workspace_path, relative_path))
        if not full_path.startswith(self.workspace_path):
            raise PermissionError(f"Path traversal detected! Attempted to access {full_path} outside sandbox.")
        return full_path

    def write_file(self, file_path: str, content: str) -> str:
        """Write content to file inside workspace."""
        full_path = self._safe_path(file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return os.path.relpath(full_path, self.workspace_path).replace("\\", "/")

    def read_file(self, file_path: str) -> str:
        """Read content from file inside workspace."""
        full_path = self._safe_path(file_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def delete_file(self, file_path: str) -> bool:
        """Delete file inside workspace."""
        full_path = self._safe_path(file_path)
        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
            return True
        return False

    def list_files(self) -> List[Dict[str, Any]]:
        """Recursively list all files in the workspace (excluding pycache, etc.)."""
        file_list = []
        for root, dirs, files in os.walk(self.workspace_path):
            # Exclude cache directories
            dirs[:] = [d for d in dirs if d not in [".pytest_cache", "__pycache__", ".git"]]
            for file in files:
                if file.endswith((".pyc", ".pyo")):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.workspace_path).replace("\\", "/")
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    content = "[Binary or unreadable file]"
                    
                file_list.append({
                    "path": rel_path,
                    "size": os.path.getsize(full_path),
                    "content": content
                })
        return file_list

    def clear(self):
        """Clean all files in workspace."""
        for name in os.listdir(self.workspace_path):
            full_path = os.path.join(self.workspace_path, name)
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)

    def execute_test(self, test_file: str) -> Dict[str, Any]:
        """Execute Python unit test file and return output."""
        full_test_path = self._safe_path(test_file)
        if not os.path.exists(full_test_path):
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Test file not found: {test_file}",
                "exit_code": -1
            }

        # We run the command inside the workspace directory so imports work relative to workspace
        cmd = ["uv", "run", "python", "-m", "unittest", test_file]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=15.0
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired as e:
            return {
                "success": False,
                "stdout": e.stdout or "",
                "stderr": "Test execution timed out (limit: 15s). Check for infinite loops.",
                "exit_code": -2
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Failed to run command: {str(e)}",
                "exit_code": -3
            }
