import unittest
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
