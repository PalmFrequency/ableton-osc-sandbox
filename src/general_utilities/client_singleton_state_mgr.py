# Example client execution script of singleton.py and state_manager.py
#
# This script proves the architecture's thread safety by simulating 
# high-concurrency stress.
#
# Instance Resolution: When GlobalStateManager() is called inside 
# concurrent_worker, it does not create a new object. The metaclass 
# intercepts it and hands the worker a pointer to the exact same memory 
# address created during the bootstrap phase.
#
# Thread Joining (t.join()): The main thread spins up three workers 
# and then hits t.join(). This is a blocking command that forces the 
# main script to wait until all three spawned threads completely 
# finish their lifecycle before moving on to print the final metrics.

import threading
import time

from state_manager import GlobalStateManager


class MyCustomClass:
    _str_prop: str
    _int_prop: int
    _float_prop: float
    _bool_prop: bool
    _list_prop: list
    _dict_prop: dict
    _tuple_prop: tuple
    _set_prop: set
    _complex_prop: dict
    def __init__(self):
        self._str_prop = ""
        self._int_prop = 0
        self._float_prop = 0.0
        self._bool_prop = False
        self._list_prop = []
        self._dict_prop = {}
        self._tuple_prop = ()
        self._set_prop = set()
        self._complex_prop = {}

def concurrent_worker(worker_id: int) -> None:
    # Resolves to the exact same global singleton instance
    state = GlobalStateManager()
    
    # 1. Fetch values with strict IDE type autocomplete
    env: str | None = state.get(key="environment", expected_type=str)
    port: int | None = state.get(key="db_port", expected_type=int)
    flt: float | None = state.get(key="my_float_prop", expected_type=float)
    cmplx: dict | None = state.get(key="my_complex_prop", expected_type=dict)
    cstm_obj: MyCustomClass | None = state.get(key="my_custom_instance", expected_type=MyCustomClass)

    
    print(f"[Worker {worker_id}] Reading global config: \r\nEnv={env}, \r\nPort={port}, \r\nFloat={flt}, \r\nComplex={cmplx}, \r\nCustom Object={cstm_obj._str_prop if cstm_obj is not None else None}")
    #print(f"[Worker {worker_id}] Reading global config: Env={env}")
    
    # 2. Mutate global telemetry across concurrent threads
    time.sleep(0.05)
    state.increment_metric(metric_name="total_requests")



if __name__ == "__main__":
    # Access the manager to set the initial state
    app_state = GlobalStateManager()
    print("Application bootstrapping complete. Instantiating threads...\n")

    print("Dynamically added properties to GlobalStateManaer...\n")
    app_state.set(key="my_int_prop", value=2)
    app_state.set(key="my_float_prop", value=7.77)
    app_state.set(key="my_str_prop", value="example_string")
    app_state.set(key="my_bool_prop", value=True)
    app_state.set(key="my_list_prop", value=[1, 2, 3])
    app_state.set(key="my_dict_prop", value={"key1": "value1", "key2": "value2"})
    app_state.set(key="my_tuple_prop", value=(1, 2, 3))
    app_state.set(key="my_set_prop", value={1, 2, 3})
    app_state.set(key="my_complex_prop", value={"nested": {"key": "value"}})

    my_custom_instance = MyCustomClass()
    my_custom_instance._str_prop = "TEST_STRING"
    app_state.set(key="my_custom_instance", value=my_custom_instance)

    # Spawn independent threads acting simultaneously
    threads: list[threading.Thread] = []
    for i in range(1, 4):
        t = threading.Thread(target=concurrent_worker, args=(i,))
        threads.append(t)
        t.start()

    # Block main thread execution until all workers complete their loops
    for t in threads:
        t.join()

    # Verify final atomic updates safely
    final_metrics = app_state.get(key="metrics", expected_type=dict)
    print(f"\nAll operations finished. Final Global Metrics: {final_metrics}")

### AFTER RUN mypy main.py --strict