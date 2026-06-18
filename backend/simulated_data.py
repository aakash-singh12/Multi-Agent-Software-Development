SIMULATED_SCENARIOS = {
    "lru_cache": {
        "title": "Thread-Safe LRU Cache",
        "description": "Create a thread-safe Least Recently Used (LRU) Cache in Python using collections.OrderedDict with capacity limit and O(1) lookups.",
        "events": [
            # 1. Planner starts
            {
                "sender": "planner",
                "event_type": "planning_started",
                "message": "Analyzing feature request and decomposing into subtasks: 'Create a thread-safe LRU Cache...'",
                "payload": {}
            },
            {
                "sender": "planner",
                "event_type": "planning_completed",
                "message": "Successfully decomposed request into 2 tasks.",
                "payload": {
                    "tasks": [
                        {
                            "id": "task_1",
                            "title": "Implement LRUCache Class",
                            "description": "Write a thread-safe LRU Cache with capacity limit, get, and put methods.",
                            "file_path": "lru_cache.py",
                            "action": "CREATE",
                            "dependencies": []
                        }
                    ],
                    "test_plan": "Write unit tests in test_lru_cache.py to verify capacity eviction, item updates, and concurrent access safety."
                }
            },
            # 2. Engineer writes initial code (violates thread safety)
            {
                "sender": "engineer",
                "event_type": "code_started",
                "message": "Writing code for task 'Implement LRUCache Class' (lru_cache.py)...",
                "payload": {}
            },
            {
                "sender": "engineer",
                "event_type": "code_written",
                "message": "Completed writing code for 'lru_cache.py'.",
                "payload": {
                    "file_path": "lru_cache.py",
                    "action": "CREATE",
                    "explanation": "Implemented standard LRU cache using collections.OrderedDict. Dict operations are O(1). Need to check thread safety.",
                    "original_code": "",
                    "code": """from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
"""
                }
            },
            # 3. Reviewer reviews and REJECTS (missing locks)
            {
                "sender": "reviewer",
                "event_type": "review_started",
                "message": "Reviewing changes in 'lru_cache.py' (Reviewer Model: Claude 3.5 Haiku - Cross-Model Review)...",
                "payload": {}
            },
            {
                "sender": "reviewer",
                "event_type": "review_completed",
                "message": "Review finished: Changes Requested.",
                "payload": {
                    "approved": False,
                    "reviewer_model": "claude-3-5-haiku",
                    "comments": [
                        "CRITICAL: The prompt requested a thread-safe cache. This implementation does not use any synchronization mechanisms.",
                        "Race conditions will occur when multiple threads call get() or put() concurrently, leading to corruption of the OrderedDict.",
                        "Please import the threading module and wrap the operations in get() and put() using a threading.Lock."
                    ]
                }
            },
            # 4. Engineer refactors based on review feedback
            {
                "sender": "engineer",
                "event_type": "code_started",
                "message": "Addressing Reviewer Feedback: Adding threading locks to ensure thread safety in lru_cache.py...",
                "payload": {}
            },
            {
                "sender": "engineer",
                "event_type": "code_written",
                "message": "Completed writing code for 'lru_cache.py'.",
                "payload": {
                    "file_path": "lru_cache.py",
                    "action": "MODIFY",
                    "explanation": "Added threading.RLock() as a class variable lock. Wrapped get() and put() within with blocks for safety.",
                    "original_code": """from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
""",
                    "code": """from collections import OrderedDict
import threading

class LRUCache:
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.lock = threading.RLock()

    def get(self, key: int) -> int:
        with self.lock:
            if key not in self.cache:
                return -1
            self.cache.move_to_end(key)
            return self.cache[key]

    def put(self, key: int, value: int) -> None:
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
"""
                }
            },
            # 5. Reviewer reviews again and APPROVES
            {
                "sender": "reviewer",
                "event_type": "review_started",
                "message": "Reviewing updated changes in 'lru_cache.py' (Reviewer Model: Claude 3.5 Haiku - Cross-Model Review)...",
                "payload": {}
            },
            {
                "sender": "reviewer",
                "event_type": "review_completed",
                "message": "Review finished: Approved.",
                "payload": {
                    "approved": True,
                    "reviewer_model": "claude-3-5-haiku",
                    "comments": [
                        "Thread safety verified. Using RLock (Reentrant Lock) is a good decision, allowing recursive lock acquisitions by the same thread.",
                        "Dict size checks and evictions are properly synchronized inside critical sections."
                    ]
                }
            },
            # 6. Tester runs tests
            {
                "sender": "tester",
                "event_type": "test_started",
                "message": "Generating and running tests in 'test_lru_cache.py' to verify 'lru_cache.py'...",
                "payload": {}
            },
            {
                "sender": "system",
                "event_type": "info",
                "message": "Wrote test suite to 'test_lru_cache.py'. Executing tests...",
                "payload": {
                    "test_code": """import unittest
import threading
import time
from lru_cache import LRUCache

class TestLRUCache(unittest.TestCase):
    def test_cache_capacity(self):
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        self.assertEqual(cache.get(1), 10)
        cache.put(3, 30) # evicts key 2
        self.assertEqual(cache.get(2), -1)
        self.assertEqual(cache.get(3), 30)

    def test_concurrent_access(self):
        cache = LRUCache(100)
        threads = []
        
        def worker(start):
            for i in range(start, start + 50):
                cache.put(i, i * 10)
                cache.get(i)
                
        for t in range(5):
            thread = threading.Thread(target=worker, args=(t * 100,))
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
            
        self.assertTrue(len(cache.cache) <= 100)

if __name__ == '__main__':
    unittest.main()
"""
                }
            },
            {
                "sender": "tester",
                "event_type": "test_completed",
                "message": "Test execution finished: Passed.",
                "payload": {
                    "success": True,
                    "test_file_path": "test_lru_cache.py",
                    "exit_code": 0,
                    "stdout": "..\n----------------------------------------------------------------------\nRan 2 tests in 0.052s\n\nOK\n",
                    "stderr": "",
                    "test_explanation": "Wrote two test cases testing basic capacity limits and concurrent multithreading race-safety verification."
                }
            },
            # 7. Documenter drafts PR
            {
                "sender": "documenter",
                "event_type": "pr_started",
                "message": "Compiling SDLC records and drafting Pull Request description...",
                "payload": {}
            },
            {
                "sender": "documenter",
                "event_type": "pr_drafted",
                "message": "Successfully compiled and created PR_DESCRIPTION.md.",
                "payload": {
                    "pr_markdown": """# PR: Thread-Safe LRU Cache Implementation

## Description
This pull request introduces a highly performant, thread-safe Least Recently Used (LRU) Cache in Python. It maintains $O(1)$ lookup and insertions while safely guarding cache mutation operations against race conditions under concurrent multithreading.

## Key Changes
- Created [lru_cache.py](file:///workspace/lru_cache.py) containing the main `LRUCache` implementation.
- Utilized `collections.OrderedDict` to preserve insertion and access history.
- Structured code locking via `threading.RLock` to synchronize gets and puts across threads.

## Code Quality & Reviews
- Reviewed and Critiqued by **Reviewer Agent (Claude 3.5 Haiku)**.
- *Revision 1*: Rejected due to thread synchronization omissions.
- *Revision 2*: Approved after RLock context manager bounds were added.

## Automated Verification
- Created test suite [test_lru_cache.py](file:///workspace/test_lru_cache.py).
- Executed unit tests in sandbox.
- **Result: PASS (2 tests in 0.05s)**
- Coverage covers capacity eviction, key updates, and multi-thread contention stress-tests.
"""
                }
            }
        ]
    },
    "jwt_auth": {
        "title": "JWT Auth Decorator",
        "description": "Build a JWT authentication decorator in Python for routing functions that decodes tokens, verifies expiration, and injects user context.",
        "events": [
            {
                "sender": "planner",
                "event_type": "planning_started",
                "message": "Analyzing feature request and decomposing into subtasks: 'JWT authentication decorator...'",
                "payload": {}
            },
            {
                "sender": "planner",
                "event_type": "planning_completed",
                "message": "Successfully decomposed request into 1 task.",
                "payload": {
                    "tasks": [
                        {
                            "id": "task_1",
                            "title": "Implement JWT Auth Decorator",
                            "description": "Write a python module containing requires_jwt decorator that parses auth headers and validates payload.",
                            "file_path": "auth.py",
                            "action": "CREATE",
                            "dependencies": []
                        }
                    ],
                    "test_plan": "Write unit tests in test_auth.py to verify decoding, mock signature validation, and header failure responses."
                }
            },
            {
                "sender": "engineer",
                "event_type": "code_started",
                "message": "Writing code for task 'Implement JWT Auth Decorator' (auth.py)...",
                "payload": {}
            },
            {
                "sender": "engineer",
                "event_type": "code_written",
                "message": "Completed writing code for 'auth.py'.",
                "payload": {
                    "file_path": "auth.py",
                    "action": "CREATE",
                    "explanation": "Implemented requires_jwt decorator. Uses mock helper or PyJWT if installed. Standardized bearer token parsing.",
                    "original_code": "",
                    "code": """import functools
import time

class JWTException(Exception):
    pass

def requires_jwt(secret_key: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            auth_header = request.get("headers", {}).get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return {"status": 401, "error": "Missing or invalid authorization header"}
            
            token = auth_header.split(" ")[1]
            try:
                # Decodes header (Mock implementation for demonstration)
                # In real scenario: payload = jwt.decode(token, secret_key, algorithms=['HS256'])
                parts = token.split(".")
                if len(parts) != 3:
                    raise JWTException("Invalid token format")
                
                # We simulate token payload validation
                # Mock token: user_id:123.exp:1700000000.signature
                payload_str = parts[1]
                payload = dict(x.split(":") for x in payload_str.split(","))
                
                exp = int(payload.get("exp", 0))
                if exp < time.time():
                    return {"status": 401, "error": "Token has expired"}
                
                request["user"] = {"id": payload.get("user_id"), "role": payload.get("role", "user")}
            except Exception:
                return {"status": 401, "error": "Invalid authentication token"}
                
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
"""
                }
            },
            {
                "sender": "reviewer",
                "event_type": "review_started",
                "message": "Reviewing changes in 'auth.py' (Reviewer Model: GPT-4o - Cross-Model Review)...",
                "payload": {}
            },
            {
                "sender": "reviewer",
                "event_type": "review_completed",
                "message": "Review finished: Approved.",
                "payload": {
                    "approved": True,
                    "reviewer_model": "gpt-4o",
                    "comments": [
                        "Clean implementation of python decorator pattern.",
                        "Using functools.wraps preserves function meta properties. Correctly maps HTTP 401 outputs."
                    ]
                }
            },
            {
                "sender": "tester",
                "event_type": "test_started",
                "message": "Generating and running tests in 'test_auth.py' to verify 'auth.py'...",
                "payload": {}
            },
            {
                "sender": "system",
                "event_type": "info",
                "message": "Wrote test suite to 'test_auth.py'. Executing tests...",
                "payload": {
                    "test_code": """import unittest
import time
from auth import requires_jwt

class TestJWTAuth(unittest.TestCase):
    def test_missing_header(self):
        @requires_jwt("secret")
        def route(request):
            return "success"
        res = route({"headers": {}})
        self.assertEqual(res["status"], 401)
        self.assertIn("Missing or invalid", res["error"])

    def test_expired_token(self):
        @requires_jwt("secret")
        def route(request):
            return "success"
        # Token exp in past
        past_time = int(time.time()) - 100
        req = {"headers": {"Authorization": f"Bearer head.user_id:123,exp:{past_time}.sig"}}
        res = route(req)
        self.assertEqual(res["status"], 401)
        self.assertEqual(res["error"], "Token has expired")

    def test_valid_token(self):
        @requires_jwt("secret")
        def route(request):
            return f"user_{request['user']['id']}"
        future_time = int(time.time()) + 1000
        req = {"headers": {"Authorization": f"Bearer head.user_id:999,exp:{future_time}.sig"}}
        res = route(req)
        self.assertEqual(res, "user_999")

if __name__ == '__main__':
    unittest.main()
"""
                }
            },
            {
                "sender": "tester",
                "event_type": "test_completed",
                "message": "Test execution finished: Passed.",
                "payload": {
                    "success": True,
                    "test_file_path": "test_auth.py",
                    "exit_code": 0,
                    "stdout": "...\n----------------------------------------------------------------------\nRan 3 tests in 0.002s\n\nOK\n",
                    "stderr": "",
                    "test_explanation": "Wrote three unit tests confirming missing header rejections, expired token failures, and successful credentials injection."
                }
            },
            {
                "sender": "documenter",
                "event_type": "pr_started",
                "message": "Compiling SDLC records and drafting Pull Request description...",
                "payload": {}
            },
            {
                "sender": "documenter",
                "event_type": "pr_drafted",
                "message": "Successfully compiled and created PR_DESCRIPTION.md.",
                "payload": {
                    "pr_markdown": """# PR: JWT Authorization Decorator

## Description
Implements a custom `@requires_jwt` decorator in `auth.py` that intercepts function routing requests, parses headers for Bearer tokens, decrypts/validates credentials, and attaches user information to the request dictionary object.

## Features
- Injects `request['user']` dictionary upon validation.
- Automatically handles expired headers returning HTTP 401 unauthorized structures.
- Lightweight decorator pattern using `functools.wraps`.

## Testing
- Verified via `test_auth.py` (3 test cases passing).
- Validated credentials parsing, expired signatures, and invalid token formats.
"""
                }
            }
        ]
    },
    "rate_limiter": {
        "title": "Token Bucket Rate Limiter",
        "description": "Implement an in-memory token bucket rate limiter in Python that allows requests under a burst threshold and refilling dynamically over time.",
        "events": [
            # 1. Planner starts
            {
                "sender": "planner",
                "event_type": "planning_started",
                "message": "Analyzing feature request and decomposing into subtasks: 'Token Bucket Rate Limiter...'",
                "payload": {}
            },
            {
                "sender": "planner",
                "event_type": "planning_completed",
                "message": "Successfully decomposed request into 1 task.",
                "payload": {
                    "tasks": [
                        {
                            "id": "task_1",
                            "title": "Implement Rate Limiter Class",
                            "description": "Write a rate_limiter.py containing TokenBucketLimiter with rate and capacity configs.",
                            "file_path": "rate_limiter.py",
                            "action": "CREATE",
                            "dependencies": []
                        }
                    ],
                    "test_plan": "Write unit tests in test_rate_limiter.py to verify request allowance, consumption, and dynamic token refills."
                }
            },
            # 2. Engineer writes code (faulty refill calculation)
            {
                "sender": "engineer",
                "event_type": "code_started",
                "message": "Writing code for task 'Implement Rate Limiter Class' (rate_limiter.py)...",
                "payload": {}
            },
            {
                "sender": "engineer",
                "event_type": "code_written",
                "message": "Completed writing code for 'rate_limiter.py'.",
                "payload": {
                    "file_path": "rate_limiter.py",
                    "action": "CREATE",
                    "explanation": "Implemented Token Bucket Algorithm. Added a get_tokens() calculation step that triggers on check.",
                    "original_code": "",
                    "code": """import time

class TokenBucketLimiter:
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate # tokens per second
        self.tokens = capacity
        self.last_update = time.time()

    def consume(self, amount: float = 1.0) -> bool:
        # Refill calculation: tokens = tokens + time_elapsed * rate
        # BUG: Accumulating tokens without checking capacity limits!
        now = time.time()
        elapsed = now - self.last_update
        self.tokens += elapsed * self.refill_rate
        self.last_update = now
        
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False
"""
                }
            },
            # 3. Reviewer approves (missed the math bug)
            {
                "sender": "reviewer",
                "event_type": "review_started",
                "message": "Reviewing changes in 'rate_limiter.py' (Reviewer Model: Claude 3.5 Sonnet)...",
                "payload": {}
            },
            {
                "sender": "reviewer",
                "event_type": "review_completed",
                "message": "Review finished: Approved.",
                "payload": {
                    "approved": True,
                    "reviewer_model": "claude-3-5-sonnet",
                    "comments": [
                        "Structure is fine. Thread lock not explicitly required for standard single process loop but recommended for multi-thread setups."
                    ]
                }
            },
            # 4. Tester runs tests and FAILS!
            {
                "sender": "tester",
                "event_type": "test_started",
                "message": "Generating and running tests in 'test_rate_limiter.py' to verify 'rate_limiter.py'...",
                "payload": {}
            },
            {
                "sender": "system",
                "event_type": "info",
                "message": "Wrote test suite to 'test_rate_limiter.py'. Executing tests...",
                "payload": {
                    "test_code": """import unittest
import time
from rate_limiter import TokenBucketLimiter

class TestRateLimiter(unittest.TestCase):
    def test_burst_capacity(self):
        limiter = TokenBucketLimiter(capacity=3.0, refill_rate=1.0)
        self.assertTrue(limiter.consume())
        self.assertTrue(limiter.consume())
        self.assertTrue(limiter.consume())
        self.assertFalse(limiter.consume()) # empty

    def test_refill_limits(self):
        limiter = TokenBucketLimiter(capacity=3.0, refill_rate=1.0)
        # Wait for refill (1.5 seconds)
        time.sleep(1.5)
        # Limiter shouldn't exceed max capacity of 3.0 tokens
        self.assertTrue(limiter.consume())
        self.assertTrue(limiter.consume())
        self.assertTrue(limiter.consume())
        # The 4th consumption should fail because capacity is capped at 3
        self.assertFalse(limiter.consume())

if __name__ == '__main__':
    unittest.main()
"""
                }
            },
            {
                "sender": "tester",
                "event_type": "test_completed",
                "message": "Test execution finished: Failed.",
                "payload": {
                    "success": False,
                    "test_file_path": "test_rate_limiter.py",
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": """FAIL: test_refill_limits (test_rate_limiter.TestRateLimiter)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "test_rate_limiter.py", line 24, in test_refill_limits
    self.assertFalse(limiter.consume())
AssertionError: True is not false : Limit exceeded capacity bounds! tokens computed = 4.5.
""",
                    "test_explanation": "Identified overflow bug where tokens accumulates past defined maximum capacity limit."
                }
            },
            # 5. Engineer fixes the bug
            {
                "sender": "engineer",
                "event_type": "code_started",
                "message": "Addressing Test Failures: Fixing token refill boundary cap in rate_limiter.py...",
                "payload": {}
            },
            {
                "sender": "engineer",
                "event_type": "code_written",
                "message": "Completed writing code for 'rate_limiter.py'.",
                "payload": {
                    "file_path": "rate_limiter.py",
                    "action": "MODIFY",
                    "explanation": "Capped the refilled tokens calculation using min(self.tokens, self.capacity) to avoid exceeding max capacity.",
                    "original_code": """import time

class TokenBucketLimiter:
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate # tokens per second
        self.tokens = capacity
        self.last_update = time.time()

    def consume(self, amount: float = 1.0) -> bool:
        now = time.time()
        elapsed = now - self.last_update
        self.tokens += elapsed * self.refill_rate
        self.last_update = now
        
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False
""",
                    "code": """import time

class TokenBucketLimiter:
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate # tokens per second
        self.tokens = capacity
        self.last_update = time.time()

    def consume(self, amount: float = 1.0) -> bool:
        now = time.time()
        elapsed = now - self.last_update
        # Capping tokens to capacity
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_update = now
        
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False
"""
                }
            },
            # 6. Tester runs tests again and PASSED
            {
                "sender": "tester",
                "event_type": "test_started",
                "message": "Re-running tests in 'test_rate_limiter.py' on updated code...",
                "payload": {}
            },
            {
                "sender": "tester",
                "event_type": "test_completed",
                "message": "Test execution finished: Passed.",
                "payload": {
                    "success": True,
                    "test_file_path": "test_rate_limiter.py",
                    "exit_code": 0,
                    "stdout": "..\n----------------------------------------------------------------------\nRan 2 tests in 1.503s\n\nOK\n",
                    "stderr": "",
                    "test_explanation": "Token overflow issue resolved. All capacity and delay assertions validated successfully."
                }
            },
            # 7. Documenter drafts PR
            {
                "sender": "documenter",
                "event_type": "pr_started",
                "message": "Compiling SDLC records and drafting Pull Request description...",
                "payload": {}
            },
            {
                "sender": "documenter",
                "event_type": "pr_drafted",
                "message": "Successfully compiled and created PR_DESCRIPTION.md.",
                "payload": {
                    "pr_markdown": """# PR: Token Bucket Rate Limiter

## Description
This pull request implements an in-memory rate limiter using the Token Bucket algorithm. It is configurable with maximum capacity and dynamic refill rates (tokens/second).

## Key Implementations
- `TokenBucketLimiter` class in `rate_limiter.py`.
- Dynamic token replenishment math capped properly at maximum capacity.

## Testing Cycle
- Automated verification completed with `test_rate_limiter.py`.
- *Cycle 1*: Test failed due to tokens exceeding max capacity (refilled tokens exceeded maximum cap).
- *Cycle 2*: Resolved by applying boundary capping `min(capacity, tokens)`. Re-run: **PASS**.
"""
                }
            }
        ]
    }
}
