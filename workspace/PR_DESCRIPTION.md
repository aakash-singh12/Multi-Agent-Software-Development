# PR: Thread-Safe LRU Cache Implementation

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
