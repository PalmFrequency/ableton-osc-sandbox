import threading
from typing import Any, TypeVar

# T represents the generic class instance type being managed
T = TypeVar("T")

class ThreadSafeSingletonMeta(type):
    """
    A reusable, thread-safe metaclass for implementing the Singleton pattern.
    """
    _instances: Dict[Type[Any], Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance: T = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]



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