import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Raw README source URL from the official repository
README_URL = "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/README.md"

def fetch_raw_readme(url=README_URL):
    """Fetches the latest raw Markdown text from the upstream repository."""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"[ERROR] Failed to fetch upstream documentation: {e}")
        return None

def parse_markdown_tables(md_content):
    """
    Slices the Markdown file into API sections, dynamically calculates column maps,
    and cleanly extracts structured data records.
    """
    registry_data = {
        "source": {
            "repository": "https://github.com/ideoforms/AbletonOSC",
            "author": "https://github.com/ideoforms",
            "license": "https://github.com/ideoforms/AbletonOSC?tab=MIT-1-ov-file",
            "description": "Control Ableton Live via Open Sound Control (OSC)",
            "notes": [
                {
                    "date": "2026-10-28",
                    "type": "info",
                    "note": "mode property vals are \"get\", \"set\", \"subscribe\", \"unsubscribe\""
                },
                {
                    "date": "2026-10-28",
                    "type": "info",
                    "note": "min ableton version is 11.0."
                }
            ],
            "parsed_markdown": "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/README.md",
            "schema_version": "1.0.0",
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        "registry": []
    }

    # Split documentation into blocks corresponding to major headings
    sections = re.findall(r'(##\s+.*?API.*?)\n(.*?)(?=\n##|$)', md_content, re.DOTALL)

    for sec_title, sec_body in sections:
        api_group = sec_title.replace("##", "").strip()
        
        # Track the active table columns dynamically within this section block
        current_col_map = {"query": None, "response": None, "desc": None}
        
        for line in sec_body.splitlines():
            line_str = line.strip()
            
            # Heuristic: Detect the table header line to build a dynamic column blueprint
            if "Address" in line_str and "|" in line_str:
                header_cols = [c.strip().lower() for c in line_str.strip("|").split("|")]
                current_col_map = {
                    "query": next((i for i, h in enumerate(header_cols) if "query" in h), None),
                    "response": next((i for i, h in enumerate(header_cols) if "response" in h), None),
                    "desc": next((i for i, h in enumerate(header_cols) if "desc" in h), None)
                }
                continue

            # Process valid OSC API string payload values
            if "/live/" in line_str and "|" in line_str:
                raw_cols = line_str.strip("|").split("|")
                cols = [c.strip() for c in raw_cols]
                
                address = cols[0]
                if address.startswith("-") or not address.startswith("/live/"):
                    continue
                
                # Run the aligned mapping through the edge case normalizer
                entry = handle_edge_cases(address, api_group, cols, current_col_map)
                registry_data["registry"].append(entry)
            
    return registry_data

def handle_edge_cases(address, api_group, cols, col_map):
    """
    Interceptor layer that aligns indices via headers and formats clean schemas.
    """
    today_str = datetime.today().strftime('%Y-%m-%d')
    
    # Safely align variables using the verified column map positions
    raw_query = cols[col_map["query"]] if col_map["query"] is not None and col_map["query"] < len(cols) else ""
    raw_resp = cols[col_map["response"]] if col_map["response"] is not None and col_map["response"] < len(cols) else ""
    description = cols[col_map["desc"]] if col_map["desc"] is not None and col_map["desc"] < len(cols) else ""

    # Mode type classifications
    if "/set/" in address:
        mode = "set"
    elif "/start_listen/" in address:
        mode = "subscribe"
    elif "/stop_listen/" in address:
        mode = "unsubscribe"
    else:
        mode = "get"

    entry = {
        "address": address,
        "mode": mode,
        "api": api_group,
        "description": description or "No description provided.",
        "args": [],
        "response": [],
        "notes": [],
        "last_updated": today_str
    }

    # Exception Case 1: Literal status string responses
    if address == "/live/test":
        entry["response"].append({
            "name": "status",
            "type": "string",
            "description": "Returns \"ok\" if connection successful"
        })
        return entry

    # Exception Case 2: Broad structural lookup tracking arrays
    if address == "/live/song/get/track_data":
        entry["args"].append({
            "name": "track_index_range",
            "type": "string",
            "optional": False,
            "description": "Interleaved values mapping target track and clip attributes"
        })
        entry["notes"].append({
            "type": "warning",
            "note": "Accepts formatting token parameters explicitly set as track.property_name or clip.property_name"
        })
        return entry

    # Argument Compilation Layout
    if raw_query and raw_query != "None" and not raw_query.startswith("'"):
        is_optional_block = "[" in raw_query and "]" in raw_query
        clean_args = raw_query.replace("[", "").replace("]", "")
        
        for param in clean_args.split(","):
            param_name = param.strip()
            if param_name:
                p_type = "int" if any(x in param_name for x in ["id", "index", "num", "channel", "cc"]) else "float"
                entry["args"].append({
                    "name": param_name,
                    "type": p_type,
                    "optional": is_optional_block or "index" not in param_name,
                    "description": f"Target {param_name} property"
                })

    # Response Compilation Layout
    if raw_resp and raw_resp != "None" and not raw_resp.startswith("'"):
        for param in raw_resp.split(","):
            resp_name = param.strip().replace("[", "").replace("]", "")
            if resp_name:
                r_type = "string" if any(x in resp_name for x in ["name", "path", "version"]) else "float"
                entry["response"].append({
                    "name": resp_name,
                    "type": r_type,
                    "description": f"Current status of {resp_name}"
                })

    return entry

if __name__ == "__main__":
    print("[INFO] Querying upstream data records from live repository...")
    md_content = fetch_raw_readme()
    
    if md_content:
        print("[INFO] Resolving tables using adaptive column header indexation...")
        structured_json = parse_markdown_tables(md_content)
        
        output_path = "ableton_osc_registry.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(structured_json, f, indent=4, ensure_ascii=False)
            
        print(f"[SUCCESS] Correctly mapped and outputted {len(structured_json['registry'])} robust schemas to '{output_path}'.")
