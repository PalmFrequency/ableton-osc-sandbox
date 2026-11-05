import threading
from typing import Any, Dict, Optional, Type, TypeVar, cast
from singleton import ThreadSafeSingletonMeta

# V represents the type of the value being extracted by the getter
V = TypeVar("V")

class GlobalStateManager(metaclass=ThreadSafeSingletonMeta):
    """
    Manages global application states cleanly and explicitly.
    """
    def __init__(self) -> None:
        self._data_lock: threading.Lock = threading.Lock()
        
        # Centralized system state
        self._state: Dict[str, Any] = {
            "environment": "production",
            "db_port": 3306,
            "metrics": {"total_requests": 0}
        }

    def get(self, key: str, expected_type: Type[V], default: Optional[V] = None) -> Optional[V]:
        """
        Safely fetches a typed global variable. 
        Mypy uses expected_type to provide full IDE autocomplete on the return value.
        """
        with self._data_lock:
            val = self._state.get(key, default)
            if val is None:
                return None
            return cast(V, val)

    def set(self, key: str, value: Any) -> None:
        """
        Safely updates a global variable.
        """
        with self._data_lock:
            self._state[key] = value

    def increment_metric(self, metric_name: str) -> None:
        """
        An atomic, thread-safe increment operation for telemetry counters.
        """
        with self._data_lock:
            metrics: Dict[str, int] = self._state["metrics"]
            if metric_name in metrics:
                metrics[metric_name] += 1



# # EXAMPLE CALL OF THE GLOBAL STATE MANAGER FROM A THIRD MAIN MODULE
# python
# import threading
# import time
# from state_manager import GlobalStateManager

# def concurrent_worker(worker_id: int) -> None:
#     # Resolves to the exact same global singleton instance
#     state = GlobalStateManager()
    
#     # 1. Fetch values with strict IDE type autocomplete
#     env = state.get("environment", expected_type=str)
#     port = state.get("db_port", expected_type=int)
    
#     print(f"[Worker {worker_id}] Reading global config: Env={env}, Port={port}")
    
#     # 2. Mutate global telemetry across concurrent threads
#     time.sleep(0.05)
#     state.increment_metric("total_requests")


# if __name__ == "__main__":
#     # Access the manager to set the initial state
#     app_state = GlobalStateManager()
#     print("Application bootstrapping complete. Instantiating threads...\n")

#     # Spawn independent threads acting simultaneously
#     threads = []
#     for i in range(1, 4):
#         t = threading.Thread(target=concurrent_worker, args=(i,))
#         threads.append(t)
#         t.start()

#     # Block main thread execution until all workers complete their loops
#     for t in threads:
#         t.join()

#     # Verify final atomic updates safely
#     final_metrics = app_state.get("metrics", expected_type=dict)
#     print(f"\nAll operations finished. Final Global Metrics: {final_metrics}")