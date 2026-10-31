import json
import urllib.request
from typing import Any
from datetime import datetime, timezone
from enum import Enum


##################################
# REMINDERS/TODO
# Run mypy to flag/catch issues before "releases" (10/31/2026)
##################################


# ------------------------------------------------------------------------------------
# Globals
# ------------------------------------------------------------------------------------

# [REQUIRED] Raw README markdown URL from the source repository for Ableton-OSC.
README_URL = "https://raw.githubusercontent.com/ideoforms/AbletonOSC/master/README.md"
# This is the primary source of truth for the OSC API registry which is parsed
# and is used to dynamically generate the structured JSON schema.

# ---------------------------------------

# [OPTIONAL]
SOURCE_REPOSITORY = "https://github.com/ideoforms/AbletonOSC"
SOURCE_AUTHOR = "https://github.com/ideoforms"
SOURCE_LICENSE = "https://github.com/ideoforms/AbletonOSC?tab=MIT-1-ov-file"
SOURCE_DESCRIPTION = "Control Ableton Live via Open Sound Control (OSC)"
SOURCE_MIN_ABLETON_VERSION = "11.0"



# ------------------------------------------------------------------------------------
# Enumerations
# ------------------------------------------------------------------------------------

class NoteType(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"

# ---------------------------------------

class APIEntryMode(Enum):
    GET = "get"
    SET = "set"
    OBSERVE = "observe"
    UNOBSERVE = "unobserve"



# ------------------------------------------------------------------------------------
# Data Model with custom two-way contracts to enable JSON-based de-/serialization.
# (serialize-to_dict(), deserialize-from_dict())
# ------------------------------------------------------------------------------------

# Class definitions for structured data representation of notes
# described throughout the API/regisry resource
class NoteEntry:
    # Default constructor for NoteEntry
    def __init__(self, note_type: NoteType, text: str, timestamp: datetime):
        self.note_type: NoteType = note_type
        self.text: str = text
        self.timestamp: datetime = timestamp

    # Alt constructor to create from a timestamp string with timezone (default is UTC).
    # timestamp_str format should be "YYYY-MM-DD" (e.g., "2026-10-28")
    @classmethod
    def from_timestamp_str(cls, note_type: NoteType, text: str, timestamp_str: str, timezone: timezone = timezone.utc):
        try:
            timestamp: datetime = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone)
            return cls(note_type, text, timestamp)
        except ValueError as e:
            print(f"[ERROR] Invalid timestamp format: {timestamp_str}. Expected 'YYYY-MM-DD'. Error: {e}")
            return cls(note_type, text, timestamp = datetime.now(tz = timezone))

    # SERIALIZE NoteEntry instance into standard JSON types.
    # Notes: Returns a dict object (enforced in Python as 
    # a "suggestion"). Not decorated with @classmethod because 
    # it requires access to instance properties.
    def to_dict(self) -> dict:
        return {
            "note_type" : self.note_type.value,
            "text" : self.text,
            "timestamp" : self.timestamp.isoformat()
        }

    # DESERIALIZE dict instance into native NoteEntry object
    # instance and properties. Notes: Returns a NoteEntry object 
    # (enforced in Python as a "suggestion"). Decorated with @classmethod because
    # it accesses the class definition
    @classmethod
    def from_dict(cls, data: dict) -> "NoteEntry":
        return cls(
            note_type = NoteType(value = data["note_type"]),
            text = data["text"],
            timestamp = datetime.fromisoformat(data["timestamp"])
        )

# Maintain static list of descriptive notes supporting users of the API 
# and this derived resource
SOURCE_NOTES: list[NoteEntry] = [
    NoteEntry.from_timestamp_str(note_type = NoteType.INFO, 
                                 text = "Ableton Live Object Model (LOM) reference: https://docs.cycling74.com/apiref/lom/",
                                 timestamp_str = "2026-10-28"),
    NoteEntry.from_timestamp_str(note_type = NoteType.INFO, 
                                     text = "Source code to create this registry: https://github.com/PalmFrequency/ableton-osc-sandbox/blob/main/src/api_utilities/osc_registry_parser.py",
                                     timestamp_str = "2026-10-30")
]

# ---------------------------------------

# Class describes metadata about the source repository and documentation,
# generated from manually entered values and the README URL. This info is 
# used to provide context for the API registry.
class SourceMetadata:
    def __init__(self, repository: str = README_URL, author: str = SOURCE_AUTHOR, license: str = SOURCE_LICENSE, 
                 description: str = SOURCE_DESCRIPTION, min_ableton_version: str = SOURCE_MIN_ABLETON_VERSION, 
                 parsed_markdown:str|None = README_URL, notes: list[NoteEntry] = SOURCE_NOTES, 
                 last_updated:datetime = datetime.now(tz = timezone.utc)):
        if parsed_markdown is None or not parsed_markdown.strip():
            raise ValueError("[ERROR] Initialization failed: 'parsed_markdown' (AKA README URL) cannot be None, empty, or blank.")
        
        self.repository:str = repository.strip()
        self.author:str = author.strip()
        self.license:str = license.strip()
        self.description:str = description.strip()
        self.min_ableton_version:str = min_ableton_version.strip()
        self.parsed_markdown:str = parsed_markdown.strip()
        self.notes:list[NoteEntry] = notes
        self.last_updated: datetime = last_updated

    # SERIALIZE SourceMetadata instance into standard JSON types.
    # Notes: Returns a dict object (enforced in Python as 
    # a "suggestion"). Not decorated with @classmethod because 
    # it requires access to instance properties.
    def to_dict(self) -> dict:
        return {
            "repository": self.repository,
            "author": self.author,
            "license": self.license,
            "description": self.description,
            "min_ableton_version": self.min_ableton_version,
            "parsed_markdown": self.parsed_markdown,
            "notes": [note.to_dict() for note in self.notes],
            "last_updated": self.last_updated.isoformat()
        }

    # DESERIALIZE dict instance into native SourceMetadata object
    # instance and properties. Notes: Returns a SourceMetadata object 
    # (enforced in Python as a "suggestion"). Decorated with @classmethod because
    # it accesses the class definition
    @classmethod
    def from_dict(cls, data: dict) -> "SourceMetadata":
        return cls(
            repository = data["repository"],
            author = data["author"],
            license = data["license"],
            description = data["description"],
            min_ableton_version = data["min_ableton_version"],
            parsed_markdown = data["parsed_markdown"],
            notes = [NoteEntry.from_dict(data = d) for d in data["notes"]],
            last_updated = datetime.fromisoformat(data["last_updated"])
        )

# ---------------------------------------

# Class describes each individual Ableton-OSC API methods
# under each API section as described by the parsed source documentation
class APIEntry:
    def __init__(self, address: str, mode: str, description: str, query_params: str, response: str, notes:list[NoteEntry]):
        self.address: str = address
        self.mode: str = mode
        self.description: str = description
        self.query_params: str = query_params
        self.response: str = response
        self.notes: list[NoteEntry] = notes
    
    # SERIALIZE APIEntry instance into standard JSON types.
    # Notes: Returns a dict object (enforced in Python as 
    # a "suggestion"). Not decorated with @classmethod because 
    # it requires access to instance properties.
    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "mode": self.mode,
            "description": self.description,
            "query_params": self.query_params,
            "response": self.response,
            "notes": [note.to_dict() for note in self.notes]
        }

    # DESERIALIZE dict instance into native APIEntry object
    # instance and properties. Notes: Returns an APIEntry object 
    # (enforced in Python as a "suggestion"). Decorated with @classmethod because
    # it accesses the class definition
    @classmethod
    def from_dict(cls, data: dict) -> "APIEntry":
        return cls(
            address = data["address"],
            mode = data["mode"],
            description = data["description"],
            query_params = data["query_params"],
            response = data["response"],
            notes = [NoteEntry.from_dict(data = d) for d in data.get("notes", [])]
        )

# ---------------------------------------

# Class describes each individual Ableton-OSC API group/type
# and serves as a container for all methods that fall under
# each of them.
class APISection:
    def __init__(self, api_name: str, api_description: str = "" ):
        self.api_name: str = api_name.strip()
        self.api_description:str = api_description.strip()
        self.api_entries: list[APIEntry] = []
    @classmethod
    def as_empty_obj(cls):
        return cls(api_name = "")

    # SERIALIZE APISection instance into standard JSON types.
    # Notes: Returns a dict object (enforced in Python as 
    # a "suggestion"). Not decorated with @classmethod because 
    # it requires access to instance properties.
    def to_dict(self) -> dict:
        return {
            "api_name": self.api_name,
            "api_description": self.api_description,
            "api_entries": [entry.to_dict() for entry in self.api_entries]
        }

    # DESERIALIZE dict instance into native APISection object
    # instance and properties. Notes: Returns a APISection object 
    # (enforced in Python as a "suggestion"). Decorated with @classmethod because
    # it accesses the class definition
    @classmethod
    def from_dict(cls, data: dict) -> "APISection":
        section = cls(
            api_name = data["api_name"],
            api_description = data["api_description"]
        )
        section.api_entries= [APIEntry.from_dict(data = d) for d in data.get("api_entries", [])]
        return section


# ---------------------------------------

# Class describes outermost data structure encapsulating all info 
# describing Ableton-OSC API metadata, sections, and methods
class APIRegistry:
    def __init__(self, source_metadata:SourceMetadata):
        self.api_source:SourceMetadata = source_metadata
        self.api_sections:list[APISection] = []

    # SERIALIZE APIRegistry instance into standard JSON types.
    # Notes: Returns a dict object (enforced in Python as 
    # a "suggestion"). Not decorated with @classmethod because 
    # it requires access to instance properties.
    def to_dict(self) -> dict:
        return {
            "api_source": self.api_source.to_dict(),
            "api_sections": [section.to_dict() for section in self.api_sections]
        }

    # DESERIALIZE dict instance into native APIRegistry object
    # instance and properties. Notes: Returns a APIRegistry object 
    # (enforced in Python as a "suggestion"). Decorated with @classmethod because
    # it accesses the class definition
    @classmethod
    def from_dict(cls, data: dict) -> "APIRegistry":
        registry = cls(source_metadata = SourceMetadata.from_dict(data["api_source"]))
        registry.api_sections = [APISection.from_dict(data = d) for d in data.get("api_sections", [])]
        return registry





# ------------------------------------------------------------------------------------
# Extraction methods
# ------------------------------------------------------------------------------------

# Download the latest raw markdown text from the upstream repository for processing.
def fetch_raw_readme(url:str = README_URL):
    try:
        with urllib.request.urlopen(url, timeout = 10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"[ERROR] Failed to fetch upstream documentation which is the source of the API: {e}")
        return None

# ---------------------------------------

# Parse the markdow content to extract only the relevant lines for processing
def extract_from_string(text_content: str) -> str:
    selected_lines: list [str | Any] = []
    capture_block = False
    block_buffer: list[Any] = []

    # splitlines() handles \n, \r\n, and keeps line formatting clean
    for line in text_content.splitlines(keepends=True):
        if line.startswith("| /live/"):
            selected_lines.append(line)

        elif line.startswith("## "):
            capture_block = True
            block_buffer: list[Any] = [line]

        elif capture_block:
            if "<details>" in line:
                selected_lines.extend(block_buffer)
                block_buffer: list[Any] = []
                capture_block = False
            else:
                block_buffer.append(line)

    return "".join(selected_lines)

# ---------------------------------------

# Slices the Markdown file into API sections, dynamically calculates column maps,
# and cleanly extracts structured data records.
def parse_markdown_tables(md_content):
    # Create registry container and add the API source/metadata section
    api_registry:APIRegistry = APIRegistry(source_metadata = SourceMetadata())
    
    # Intermediate parsing/processing of the API doc markdown.
    matching_lines:list[str] = extract_from_string(text_content = md_content).splitlines()

    # Iterate line-by-line to build a list of APIEntry objects, dynamically 
    # tracking the current API group and metadata
    api_sections:list[APISection] = api_registry.api_sections

    for line in matching_lines:
        line_str: str = line.strip()
        if line_str.startswith("## "):
            api_name: str = line_str.replace("##", "").strip()
            current_api_section = APISection(api_name)
            api_sections.append(current_api_section)
        elif line_str.strip() and line_str.strip()[0].isalpha():
            if not api_sections:
                continue  # Skip if no API section has been defined yet
            # Access last (current) API Section and associate the description info
            current_api_section: APISection = api_sections[-1]
            current_api_section.api_description += line_str + " "
        elif line_str.startswith("| /live/"):
            if not api_sections:
                continue  # Skip if no API section has been defined yet
            # Access last (current) API Section and associate the address/path info (the method)
            current_api_section: APISection = api_sections[-1]
            cols: list[str] = [c.strip() for c in line_str.strip("|").split(sep = "|")]
            current_api_section.api_entries.append(APIEntry(
                address = cols[0],
                mode = "get" if "/get/" in cols[0] 
                    else "set" if "/set/" in cols[0] 
                    else "observe" if "/start_listen/" in cols[0] 
                    else "unobserve" if "/stop_listen/" in cols[0] 
                    else "get",
                description = cols[3] if len(cols) > 3 
                    else "",
                query_params = cols[1:2][0] if len(cols[1:2]) > 0 
                    else "",  # Assuming query params are in the second column
                response = cols[2:3][0] if len(cols[2:3]) > 0 
                    else "",      # Assuming response is in the third column
                notes = [] # For possible future use
            ))

    return api_registry


# def handle_edge_cases(address, api_group, cols, col_map):
#     """
#     Interceptor layer that aligns indices via headers and formats clean schemas.
#     """
    
#     # Safely align variables using the verified column map positions
#     raw_query = cols[col_map["query"]] if col_map["query"] is not None and col_map["query"] < len(cols) else ""
#     raw_resp = cols[col_map["response"]] if col_map["response"] is not None and col_map["response"] < len(cols) else ""
#     description = cols[col_map["desc"]] if col_map["desc"] is not None and col_map["desc"] < len(cols) else ""

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


############################################# STOP HERE 10/31/2026 12:10PM

if __name__ == "__main__":
    print("[INFO] Querying upstream data records from live repository...")
    md_content: Any = fetch_raw_readme()
    
    if md_content:
        print("[INFO] Extracting API from markdown docs as structured data...")
        structured_json: Any = parse_markdown_tables(md_content)

        # Format and save as local JSON file
        output_path = "ableton_osc_registry.json"
        with open(file = output_path, mode = "w", encoding = "utf-8") as f:
            json.dump(obj = structured_json, fp = f, indent = 4, ensure_ascii = False)
            
        print(f"[SUCCESS] Correctly mapped and outputted {len(structured_json['registry'])} robust schemas to '{output_path}'.")
