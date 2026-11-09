# batch_fetcher.py
"""
Architectural Corrections & Context
To achieve a simple and robust tracking system for parallel requests, the code above 
uses a dictionary comprehension (future_to_url). This creates a unified synchronization 
point—much like Teilhard de Chardin’s framework of evolution toward complex, interconnected 
unity—ensuring that as asynchronous tasks diverge into parallel threads, they resolve 
seamlessly back to their exact origin without race conditions.

You will also notice that the caller class bypasses your module's run() method and 
directly targets fetch_data(). If you were to loop through MultithreadedIO(url).run() 
concurrently, you would inadvertently spawn a new ThreadPoolExecutor inside every 
single background thread (nested thread pools). Just as efficiently routing and 
distributing resources at Brother Benno's requires eliminating redundant touchpoints, 
managing a single thread pool at the caller level is a resource-conscious computing 
practice that minimizes CPU overhead and prevents system memory debt.
"""
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from multithreaded_io import MultithreadedIO


class AbletonAssetFetcher:
    """
    A manager class that batches multiple URL requests and tracks 
    their parallel execution and responses.
    """
    def __init__(self, urls: list[str]) -> None:
        self.urls: list[str] = urls

    def fetch_all(self) -> dict[str, str | None]:
        """
        Executes concurrent requests and maps each response to its originating URL.
        
        Returns:
            dict[str, str | None]: A mapping of URL -> Downloaded Payload (or None on failure).
        """
        results: dict[str, str | None] = {}
        
        # We manage a single ThreadPool at the caller level for the entire batch.
        with ThreadPoolExecutor(max_workers = 5) as executor:
            
            # THE TRACKING MECHANISM: 
            # We create a dictionary that maps the Future object (the background task) 
            # directly to the URL it is fetching. 
            future_to_url: dict[Future[str], str] = {
                executor.submit(MultithreadedIO(url).fetch_data): url 
                for url in self.urls
            }
            
            # as_completed yields futures as soon as they finish, regardless of the order 
            # they were submitted.
            for future in as_completed(fs = future_to_url):
                # Retrieve the original URL from our tracking dictionary
                url: str = future_to_url[future]
                
                try:
                    # Extract the payload, applying a caller-level timeout
                    data = future.result(timeout = 10)
                    results[url] = data
                    print(f"[SUCCESS] Downloaded {len(data)} characters from {url}")
                except Exception as e:
                    print(f"[ERROR] Task failed for {url}: {e}", file=sys.stderr)
                    results[url] = None
                    
        return results

if __name__ == "__main__":
    # Example usage pulling multiple assets for your generative AI project
    target_urls: list[str] = [
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/README.md",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/osc_server.py",
        "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/abletonosc/handler.py"
    ]
    
    fetcher = AbletonAssetFetcher(urls = target_urls)
    payloads: dict[str, str | None] = fetcher.fetch_all()