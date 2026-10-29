import json
import urllib.request
from datetime import datetime, timezone

# Raw README markdown source URL from the official repository
README_URL = "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/README.md"

class ParsedAPISection:
    def __init__(self, api_name: str):
        self.api_name = api_name
        self.api_description = ""
        self.entries: list[ParsedAPIEntry] = []
        self.timestamp = datetime.now(timezone.utc)


class ParsedAPIEntry:
    def __init__(
        self, 
        api_name: str, 
        address: str, 
        query_params: str, 
        response: str, 
        description: str, 
        timestamp: datetime
    ):
        self.api_name = api_name
        self.address = address
        self.query_params = query_params
        self.response = response
        self.description = description
        self.timestamp = timestamp

    # TOSTRING() ?
    #def __str__(self):
    #    return f"{self.api_name} ({self.address}) - {self.description}"

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
                    "note": "mode property vals are \"get\", \"set\", \"observe\", \"unobserve\"."
                },
                {
                    "date": "2026-10-28",
                    "type": "info",
                    "note": "min ableton version is 11.0."
                },
                {
                    "date": "2026-10-28",
                    "type": "info",
                    "note": "Ableton Live Object Model (LOM) reference: https://docs.cycling74.com/apiref/lom/"
                }
            ],
            "parsed_markdown": README_URL,
            "schema_version": "1.0.0",
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        "registry": []
    }

    # Regex expression matches headers describing API groups (e.g. "## Application API")
    # and lines starting with the OSC address prefix (e.g. "| /live/..."). Each processed
    # address prefix will be associated with the last API group header encountered in the 
    # Markdown file.
    matching_lines:list[str] = extract_from_string(md_content).splitlines()

    # Iterate line0by-line to build a list of ParsedOSCEntry objects, dynamically tracking the current API group and table column indices
    api_sections: list[ParsedAPISection] = []
    current_api_section: ParsedAPISection | None = None
    for line in matching_lines:
        line_str = line.strip()
        if line_str.startswith("## "):
            api_name = line_str.replace("##", "").strip()
            current_api_section = ParsedAPISection(api_name)
            api_sections.append(current_api_section)
        elif line_str.strip() and line_str.strip()[0].isalpha():
            if not api_sections:
                continue  # Skip if no API section has been defined yet
            current_api_section = api_sections[-1]
            current_api_section.api_description += line_str + " "
        elif line_str.startswith("| /live/"):
            if not api_sections:
                continue  # Skip if no API section has been defined yet
            current_api_section = api_sections[-1]
            cols = [c.strip() for c in line_str.strip("|").split("|")]
            current_api_section.entries.append(ParsedAPIEntry(
                api_name=current_api_section.api_name,
                address=cols[0],
                query_params=cols[1:2][0] if len(cols[1:2]) > 0 else "",  # Assuming query params are in the second column
                response=cols[2:3][0] if len(cols[2:3]) > 0 else "",      # Assuming response is in the third column
                description=cols[3] if len(cols) > 3 else "",
                timestamp=current_api_section.timestamp
            ))

    # # Split documentation into blocks corresponding to major headings
    # #sections = re.findall(r'(##\s+.*?API.*?)\n(.*?)(?=\n##|$)', md_content, re.DOTALL)

    # for sec_title, sec_body in sections:
    #     api_group = sec_title.replace("##", "").strip()
        
    #     # Track the active table columns dynamically within this section block
    #     current_col_map = {"query": None, "response": None, "desc": None}
        
    #     for line in sec_body.splitlines():
    #         line_str = line.strip()
            
    #         # Heuristic: Detect the table header line to build a dynamic column blueprint
    #         if "Address" in line_str and "|" in line_str:
    #             header_cols = [c.strip().lower() for c in line_str.strip("|").split("|")]
    #             current_col_map = {
    #                 "query": next((i for i, h in enumerate(header_cols) if "query" in h), None),
    #                 "response": next((i for i, h in enumerate(header_cols) if "response" in h), None),
    #                 "desc": next((i for i, h in enumerate(header_cols) if "desc" in h), None)
    #             }
    #             continue

    #         # Process valid OSC API string payload values
    #         if "/live/" in line_str and "|" in line_str:
    #             raw_cols = line_str.strip("|").split("|")
    #             cols = [c.strip() for c in raw_cols]
                
    #             address = cols[0]
    #             if address.startswith("-") or not address.startswith("/live/"):
    #                 continue
                
    #             # Run the aligned mapping through the edge case normalizer
    #             entry = handle_edge_cases(address, api_group, cols, current_col_map)
    #             registry_data["registry"].append(entry)
            
    return registry_data

# Parse the README content to extract only the relevant lines for processing
def extract_from_string(text_content: str) -> str:
    selected_lines = []
    capture_block = False
    block_buffer = []

    # splitlines() handles \n, \r\n, and keeps line formatting clean
    for line in text_content.splitlines(keepends=True):
        if line.startswith("| /live/"):
            selected_lines.append(line)

        elif line.startswith("## "):
            capture_block = True
            block_buffer = [line]

        elif capture_block:
            if "<details>" in line:
                selected_lines.extend(block_buffer)
                block_buffer = []
                capture_block = False
            else:
                block_buffer.append(line)

    return "".join(selected_lines)


# def handle_edge_cases(address, api_group, cols, col_map):
#     """
#     Interceptor layer that aligns indices via headers and formats clean schemas.
#     """
#     today_str = datetime.today().strftime('%Y-%m-%d')
    
#     # Safely align variables using the verified column map positions
#     raw_query = cols[col_map["query"]] if col_map["query"] is not None and col_map["query"] < len(cols) else ""
#     raw_resp = cols[col_map["response"]] if col_map["response"] is not None and col_map["response"] < len(cols) else ""
#     description = cols[col_map["desc"]] if col_map["desc"] is not None and col_map["desc"] < len(cols) else ""

#     # Mode type classifications
#     if "/set/" in address:
#         mode = "set"
#     elif "/start_listen/" in address:
#         mode = "observe"
#     elif "/stop_listen/" in address:
#         mode = "unobserve"
#     else:
#         mode = "get"

#     entry = {
#         "address": address,
#         "mode": mode,
#         "api": api_group,
#         "description": description or "No description provided.",
#         "args": [],
#         "response": [],
#         "notes": [],
#         "last_updated": today_str
#     }

#     # Exception Case 1: Literal status string responses
#     if address == "/live/test":
#         entry["response"].append({
#             "name": "status",
#             "type": "string",
#             "description": "Returns \"ok\" if connection successful"
#         })
#         return entry

#     # Exception Case 2: Broad structural lookup tracking arrays
#     if address == "/live/song/get/track_data":
#         entry["args"].append({
#             "name": "track_index_range",
#             "type": "string",
#             "optional": False,
#             "description": "Interleaved values mapping target track and clip attributes"
#         })
#         entry["notes"].append({
#             "type": "warning",
#             "note": "Accepts formatting token parameters explicitly set as track.property_name or clip.property_name"
#         })
#         return entry

#     # Argument Compilation Layout
#     if raw_query and raw_query != "None" and not raw_query.startswith("'"):
#         is_optional_block = "[" in raw_query and "]" in raw_query
#         clean_args = raw_query.replace("[", "").replace("]", "")
        
#         for param in clean_args.split(","):
#             param_name = param.strip()
#             if param_name:
#                 p_type = "int" if any(x in param_name for x in ["id", "index", "num", "channel", "cc"]) else "float"
#                 entry["args"].append({
#                     "name": param_name,
#                     "type": p_type,
#                     "optional": is_optional_block or "index" not in param_name,
#                     "description": f"Target {param_name} property"
#                 })

#     # Response Compilation Layout
#     if raw_resp and raw_resp != "None" and not raw_resp.startswith("'"):
#         for param in raw_resp.split(","):
#             resp_name = param.strip().replace("[", "").replace("]", "")
#             if resp_name:
#                 r_type = "string" if any(x in resp_name for x in ["name", "path", "version"]) else "float"
#                 entry["response"].append({
#                     "name": resp_name,
#                     "type": r_type,
#                     "description": f"Current status of {resp_name}"
#                 })

#     return entry


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
