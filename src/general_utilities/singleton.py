# Thread-safe meta class
#
# A metaclass in Python defines how a class behaves. By inheriting from type, 
# ThreadSafeSingletonMeta intercepts the creation of any class that uses it, 
# ensuring only one instance of that class is ever spawned in memory.
#
# The Double-Checked Locking Pattern: The __call__ method implements a famous 
# concurrency pattern called "Double-Checked Locking."
#
#   Check 1 (Unlocked): if cls not in cls._instances: checks if the instance 
#   already exists. If it does, it returns it immediately. This skips the 
#   heavy performance cost of acquiring a thread lock for the 99.9% of calls 
#   that happen after initialization.
#
#   The Lock: with cls._locks: pauses all other threads trying to reach this 
#   block. If three threads ask for the state manager at the exact same 
#   microsecond during startup, one gets the lock, and the other two wait.
#
#   Check 2 (Locked): if cls not in cls._instances: checks again once the lock 
#   is acquired. This prevents the two waiting threads from overwriting the 
#   instance once the first thread finishes building it.
import threading


class ThreadSafeSingletonMeta(type):
    """A thread-safe metaclass for creating Singletons.

    Uses a double-checked locking optimization to ensure performance
    remains fast after the initial instance creation.
    """
    _instances = {}
    _locks = {} # Dictionary of locks per class

    def __call__(cls, *args, **kwargs):
        # First check (Unlocking): Avoids lock overhead for all subsequent calls
        if cls not in cls._locks:
            cls._locks[cls] = threading.Lock()
        # Proceed with double-checked locking using cls._locks[cls]
        if cls not in cls._instances:
            with cls._locks[cls]:
                # Second check (Locked): Ensures no other thread built it while waiting
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]