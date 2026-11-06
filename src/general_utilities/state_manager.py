# Locked data store
#
# While the metaclass ensures only one manager exists, the GlobalStateManager
# ensures that the data inside that manager is safely accessed by multiple
# threads.
#
#   The Dedicated Data Lock (self._data_lock): Notice that this class has its own
#   entirely separate threading.Lock(). The metaclass lock is only used once to
#   create the object; this data lock is used thousands of times to safely read
#   and write the dictionary values (self._state).
#
#   Generic Type Hinting (TypeVar and cast): The get method requires an
#   expected_type argument (e.g., expected_type=str). At runtime, Python ignores
#   this, but during a mypy scan or when coding in an IDE like VS Code, the
#   cast(V, val) explicitly tells the intellisense engine exactly what type of
#   object is being returned, providing perfect autocomplete for your workers.
#
#   Atomic Operations (increment_metric): Instead of a worker thread calling get
#   to find the total requests, adding 1, and calling set to save it (which
#   creates a gap where another thread could overwrite the data), the
#   increment_metric method locks the dictionary, adds 1, and unlocks it in a
#   single, uninterrupted motion.

import copy
import threading
from typing import Any, TypeVar, cast

from singleton import ThreadSafeSingletonMeta

# V represents the type of the value being extracted by the getter
V = TypeVar("V")

class GlobalStateManager(metaclass=ThreadSafeSingletonMeta):
    """
    Manages global application states cleanly and explicitly.
    """
    def __init__(self) -> None:
        self._data_lock: threading.Lock = threading.Lock()
        
        # [EXAMPLE] Centralized system state. Can also add properties of any type dynamically.
        self._state: dict[str, Any] = {
            "environment": "production",
            "db_port": 3306,
            "metrics": {"total_requests": 0}
            # ...
        }

    def get(self, key: str, expected_type: type[V], default: V | None = None) -> V | None:
        """
        Safely fetches a typed global variable. 
        Mypy uses expected_type to provide full IDE autocomplete on the return value,
        and isinstance() guarantees runtime safety.
        """
        with self._data_lock:
            val: Any = self._state.get(key, default)
            if val is None:
                return None
            
            #  Strict runtime type enforcement
            if not isinstance(val, expected_type):
                raise TypeError(
                    f"State mismatch for '{key}': Expected {expected_type.__name__}, "
                    f"got {type(val).__name__}."
                )
                
            return cast(V, copy.deepcopy(val))
    
    def set(self, key: str, value: Any) -> None:
        """
        Safely updates a global variable.
        """
        with self._data_lock:
            self._state[key] = value

    # [EXAMPLE] Atomic operation (metric increment)
    def increment_metric(self, metric_name: str) -> None:
        """
        An atomic, thread-safe increment operation for telemetry counters.
        """
        with self._data_lock:
            metrics: dict[str, int] = self._state["metrics"]
            if metric_name in metrics:
                metrics[metric_name] += 1