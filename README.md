# Comic Sorter

Comic Sorter is a Python-based utility for organizing and enriching digital comic book collections (.cbz and .cbr formats). 

It is designed to scan unstructured directories, parse comic file names to extract metadata (Series, Publisher, Volume, Issue), and sort the files into standard directory hierarchies for self-hosted reading applications like Kavita, Komga, or Ubooquity.

## Key Features

*   **Heuristic Parsing Engine:** Extracts Series (IPs), Publishers, Volume, and Issue numbers from standard and non-standard file nomenclature.
*   **Metadata Injection:** Writes standard `ComicInfo.xml` tags (including `<Number>` and `<Volume>`) directly into the `.cbz` archive during the sort operation.
*   **Format Conversion:** Detects proprietary `.cbr` archives and converts them into `.cbz` utilizing the local `unar` CLI dependency.
*   **Deduplication:** Hashes matching files across multiple sort runs to prevent duplicate overwrites. Redundant files are moved to the system Trash natively.
*   **Concurrent Execution:** Utilizes `ThreadPoolExecutor` to handle offline Zip/Rar parsing across multiple threads, minimizing I/O bottlenecks.
*   **ComicVine Fallback:** Queries the ComicVine API to infer unknown titles, implementing a strict 1-second rate limit guardrail per documentation standards.
*   **Dry-Run Mode:** Exposes a simulation mode that provides a textual report of predicted file trajectories without writing to disk.
*   **Dual UI Frameworks:** Offers a CustomTkinter Graphical UI (`app.py`), alongside a robust terminal interface (`main.py`) for headless environments.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/YourUsername/comic-sorter.git
   cd comic-sorter
   ```

2. Comic Sorter leverages the local `unar` binary to extract `.cbr` files safely. Ensure it is installed on your host system:
   ```bash
   # MacOS
   brew install unar
   # Linux (Debian/Ubuntu)
   sudo apt-get install unar
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Graphical Interface
```bash
./startapp.sh
# or native python
python app.py
```

### Command Line Interface
```bash
./startcli.sh
# or native python
python main.py
```

## Operation Modes

- **[1] Sort New Library:** Copies contents from an unorganized source folder into a structured destination folder. The source folder is left unmodified.
- **[2] Resort Existing Library:** Moves and re-maps comic archives natively within the destination directory in-place.
- **[3] Smart-Merge:** Scans a previously mapped destination library to train internal contextual aliases, then moves unstructured files directly into that ecosystem.

## Custom Regex Rules

You can override internal file-parsing logic natively by injecting expression templates into the `config.json` array (generated upon first execution).

```json
{
    "custom_regexes": [
        "^(?P<publisher>DC)\\s*-\\s*(?P<ip>[A-Z\\s]+)\\s*v(?P<volume>\\d+)?\\s*#(?P<issue>\\d+)"
    ]
}
```
