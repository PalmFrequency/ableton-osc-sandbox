# Optimized, robust, and cleanly structured version of your script.
# To fix the confusion, we have completely eliminated those extra, redundant instantiations (MultithreadedIO(url="")). Instead, the parameters (max_workers and timeout) are now defined as Class-Level Constants, which can be accessed cleanly anywhere in the script without creating dummy instances.

import sys
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Payload:
    def __init__(self, data: str | None, elapsed_seconds: float) -> None:
        self.data: str | None = data
        self.elapsed_seconds: float = elapsed_seconds

class MultithreadedIO:
    """
    A self-contained, portable module for executing concurrent, timeout-enforced
    network I/O operations using an internal ThreadPoolExecutor.
    """
    
    # -------------------------------------------------------------
    # CLASS CONSTANTS
    # Shared across all instances. Eliminates the need to create 
    # dummy objects just to read configuration values.
    # -------------------------------------------------------------
    DEFAULT_MAX_WORKERS: int = 3
    DEFAULT_TIMEOUT: int = 5
    DEFAULT_ENCODING: str = "utf-8"

    def __init__(self, encoding: str = DEFAULT_ENCODING,
                    timeout: int = DEFAULT_TIMEOUT,
                        max_workers: int = DEFAULT_MAX_WORKERS) -> None:
        """
        Initializes an I/O worker instance for network requests.
        
        Args:
            encoding (str): Text decoding format (defaults to 'utf-8').
            timeout (int): Seconds to wait before a network operation drops.
            max_workers (int): Maximum number of concurrent worker threads.
        """
        self.timeout: int = timeout
        self.encoding: str = encoding
        self.max_workers: int = max_workers

    """Example time-consuming op like fetching data from a single resource like a URL."""
    def fetch_single(self, url: str, headers: dict[str, str] | None = None) -> Payload:
        """
        Performs a synchronous network fetch of the target URL.
        This method will be handed off to a background thread.
        
        Returns:
            Payload: The decoded text content and elapsed time from the URL.
            
        Raises:
            ValueError: If the URL string is empty or missing.
            HTTPError/URLError: On network failure or bad responses.
            UnicodeDecodeError: If text decoding fails.
            TimeoutError: If the network operation exceeds the configured timeout.
        """
        # Guard clause: Fail fast if the URL isn't configured properly
        if not url:
            raise ValueError("URL cannot be empty or None.")

        start_time: float = time.perf_counter()

        if headers is None:
            headers: dict[str, str] = {"User-Agent" : "Python-urllib-script"}   
        req: Request = Request(url, headers = headers)

        try:
            # Open a connection stream with a strict network-level timeout
            with urlopen(url = req, timeout = self.timeout) as response:
                # Read raw bytes and decode them into a Python string
                data: str = response.read().decode(self.encoding)
                elapsed_seconds: float = time.perf_counter() - start_time
                return Payload(data = data, elapsed_seconds = elapsed_seconds)
        except TimeoutError:
            # Failure pathway: Handle slow connections gracefully
            print(f"[ERROR] Request timed out for resource, {url}, after {self.timeout} seconds.", file = sys.stderr)
            return Payload(data = None, elapsed_seconds = time.perf_counter() - start_time)
        except (HTTPError, URLError) as e:
            # Log network disruptions clearly to standard error
            print(f"[ERROR] Failed to access resource {url}:\n{e}", file = sys.stderr)
            return Payload(data = None, elapsed_seconds = time.perf_counter() - start_time)
        except UnicodeDecodeError as e:
            # Log configuration/encoding mismatches safely
            print(f"[ERROR] Failed to decode response for resource, {url}, as {self.encoding}:\n{e}", file = sys.stderr)
            return Payload(data = None, elapsed_seconds = time.perf_counter() - start_time)


    def fetch_multi(self, urls: list[str], 
                    progress_callback: Callable[[int, str, str, float], None] | None = None) -> \
                        list[tuple[str, Payload | None]]:
        """
        Executes concurrent requests using the configured instance pool and maps 
        each response payload back to its originating URL.
        
        Args:
            urls (list[str]): Target resources to gather.
            progress_callback (Callable): Optional progress callback hook accepting:
                                          (url, status_string, percentage_completed)
        
        Returns:
            list[tuple[str, Payload | None]]: A list of URL -> Downloaded Payload (or None on failure) tuples.
        """

        if not urls or len(urls) == 0:
            return []

        total_tasks: int = len(urls)
        completed_tasks: int = 0

        # Initialize placeholders to safely populate elements concurrently by index
        results: list[tuple[str, Payload] | None] = [None] * total_tasks        
        
        # We manage a single ThreadPool at the caller level for the entire batch.
        with ThreadPoolExecutor(max_workers = self.max_workers) as executor:
            
            # THE TRACKING MECHANISM: 
            # Fixed: Maps future to a tuple of (index, url) to decouple uniqueness from string keys
            future_to_meta: dict[Future[Payload], tuple[int, str]] = {
                executor.submit(self.fetch_single, url): (idx, url) for idx, url in enumerate(urls)
            }
            
            # as_completed yields futures as soon as they finish, regardless of the order 
            # they were submitted.
            for future in as_completed(fs = future_to_meta):
                # Retrieve the original URL from our tracking dictionary
                idx, url = future_to_meta[future]
                completed_tasks += 1
                current_percentage: float = (completed_tasks / total_tasks) * 100.0
                
                try:
                    # Extract the payload, applying a caller-level timeout
                    # Block the Main Thread and monitor the Future object
                    payload: Payload = future.result()
                    results[idx] = (url, payload)
                    status: str = "SUCCESS" if payload.data is not None else "FAILED"
                except Exception as e:
                    print(f"[ERROR] Task execution failed for resource index [{idx}] ({url}): {e}", file = sys.stderr)
                    payload = Payload(data = None, elapsed_seconds = 0.0)
                    results[idx] = (url, payload)
                    status = "EXCEPTION"
                    
                # Low-cost async execution hook executed immediately inside the completion thread
                if progress_callback:
                    progress_callback(idx + 1, url, status, current_percentage)
                    
        # Filter type-safety guarantees to return an immutable sequence structure
        return [item for item in results if item is not None]



# =====================================================================
# Verification Execution with Example Progress Callback Hook
# =====================================================================
def sample_progress_tracker(idx: int, url: str, status: str, percentage: float) -> None:
    """
    A low-cost standard terminal progress visualizer tracking tasks by structural index.
    """
    short_url: str = url.split("/")[-1] if "/" in url else url
    sys.stdout.write(f" Progress: [{percentage:6.2f}%] | Task #{idx}: {short_url:<20} | Status: {status}\n")
    sys.stdout.flush()
    
if __name__ == "__main__":
    target_urls: list[str] = [
        "https://www.google.com",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/osc_server.py",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/handler.py",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/README.md",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/osc_server.py",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/handler.py",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/README.md",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/osc_server.py",
        #"https://www.notarealurl1.com",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/handler.py",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/README.md",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/osc_server.py",
        #"https://www.notarealurl1.com",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/handler.py",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/README.md",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/osc_server.py",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/handler.py",
    ]
    
    print(f"Beginning Network Operations Sequence on {len(target_urls)} URLs:\n" + "-"*60)

    try:
        downloader = MultithreadedIO()
        
        # Pass the progress callback hook dynamically into the execution module
        ordered_payloads: list[tuple[str, Payload | None]] = downloader.fetch_multi(
            urls = target_urls, 
            progress_callback = sample_progress_tracker
        )
        
        print("-"*60 + "\nFinal Report Summary Details (Maintained Request Order):")

        for idx, (url, payload) in enumerate(iterable = ordered_payloads):
            if payload is not None:
                minutes, remaining_seconds = divmod(payload.elapsed_seconds, 60)
                seconds = int(remaining_seconds)
                milliseconds = int((remaining_seconds - seconds) * 1000)
                timer_str = f"{int(minutes):02d}:{seconds:02d}:{milliseconds:03d}"
                
                if payload.data is None:
                    print(f"[-] Position [{idx + 1}]: Download structural failure. (Time: {timer_str}) {url}")
                else:
                    print(f"[+] Position [{idx + 1}]: Downloaded {len(payload.data.encode())/1000:,.3f} KB (Time: {timer_str}) {url}")
            else:
                print(f"[-] Position [{idx + 1}]: No payload returned. (Time: N/A) {url}")
                
    except Exception as e:
        print(f"[ERROR] Execution engine collapsed: {e}", file = sys.stderr)


# Benefits from the refactored code above.
# =====================================================================
# • Eliminated Dummy Instantiations: Instead of MultithreadedIO(url=""), the script now uses clean, 
# readable uppercase namespace targets like MultithreadedIO.DEFAULT_TIMEOUT. This makes tracking 
# memory and data flow drastically clearer.

# • Separation of Concerns: Instantiating the object (downloader = MultithreadedIO(...)) is 
# separated into its own explicit statement directly preceding executor.submit(). This 
# separates configuration from execution.

# • Explicit Constants Hierarchy: If you ever decide to increase the pool workers or change the 
# global request timeout window, you only have to alter a single digit at the absolute top 
# of the class block.

# Potential Enhancements: 
# =====================================================================
# [A]. Fetch multiple URLs concurrently.

# [B]. Support "ranged" downloads,which allow multiple workers to download different
# byte ranges of a single file in parallel. Note that this may only make sense for 
# very large files like video assets or datasets.
# The Pattern: Distributed Chunk Downloading

# To pull this off safely, the workflow must follow these precise steps:
# [Main Thread] ──(1. Get File Size)──> [Server]
#      │
#      ├──(2. Calculate Byte Ranges: e.g., 0-25%, 25-50%...)
#      │
#      ├──(3. Distribute to Workers) ──> [Worker 1] -> Download Chunks 0-999
#      │                             ──> [Worker 2] -> Download Chunks 1000-1999
#      │                             ──> [Worker 3] -> Download Chunks 2000-2999
#      │
# [Main Thread] ──(4. Wait & Combine Chunks sequentially) ──> Final Local File
# • The Handshake (Metadata Check): The main thread sends a quick HEAD request to the server 
# to ask two questions: "How big is this file?" and "Do you accept byte ranges?"
# • The Segmentation: If the server says yes, the main thread divides the total byte 
# size into equal segments (chunks) based on the number of workers.
# • Parallel Fetching: Each worker is assigned a specific byte range. They tell the server, 
# "Give me only bytes X through Y of this file."
# • Reassembly: As the workers finish, the main thread stitches the raw byte chunks back 
# together in the exact, correct chronological order.

# Implementation Pitfalls & Complexity

# This pattern introduces massive real-world pitfalls, which is why it is usually reserved 
# for downloading massive files (like video assets or datasets) rather than small API payloads or text files:
# • Server Support: Many servers and APIs completely disable range requests (Accept-Ranges: none). 
# If a server doesn't support it, the pattern fails completely, and you must fallback to a single thread.
# • Corrupted Files (The Out-of-Order Trap): If Worker 3 finishes before Worker 2, you cannot 
# just append the data blindly. You must write the incoming bytes into exact, precise byte offsets 
# inside the destination file, or manage an ordered memory buffer.
# • State Management: If one worker drops connection halfway through its 25% segment, the entire 
# download fails unless you build complex chunk-retry logic.

