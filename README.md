# Comic Sorter

Comic Sorter is a Python-based desktop utility for organizing and enriching digital comic book collections (`.cbz` and `.cbr` formats).

It scans unstructured directories, parses file names and embedded metadata to extract Series, Publisher, Volume, and Issue information, then sorts files into a clean publisher/series/storyline hierarchy suitable for self-hosted reading applications like Kavita, Komga, or Ubooquity.

---

## Key Features

- **Heuristic Parsing Engine:** Extracts Publisher, Series (IP), Storyline, Volume, and Issue from standard and non-standard file naming conventions.
- **Metadata Injection:** Writes standard `ComicInfo.xml` tags directly into each `.cbz` archive during the sort operation.
- **Format Conversion:** Detects proprietary `.cbr` archives and converts them to `.cbz` using the local `unar` binary.
- **Deduplication:** Cross-references file signatures across multiple sort runs to prevent duplicates. Redundant files are moved to the system Trash.
- **Persistent Caching:** Stores resolved metadata in a `.comic_sorter_cache.json` file inside your library so repeated runs skip re-processing files that are already known. The cache is automatically sanitized on every load to remove any corrupted entries.
- **Concurrent Metadata Extraction:** Uses a `ThreadPoolExecutor` to parse archives in parallel, minimising I/O wait time on large libraries.
- **ComicVine Fallback:** Queries the ComicVine API for unknown titles, with a strict 1-second rate-limit guardrail.
- **Move or Copy Mode:** A toggle lets you move files out of the source folder (for sorting a staging/Unsorted folder) or copy them (to preserve the originals).
- **Automatic Empty Folder Cleanup:** After each run, any folders left empty in the source directory are automatically removed.
- **Dry-Run Simulation:** A simulation mode reports where each file would go without writing anything to disk.
- **Non-Fatal Error Handling:** If a file fails during processing, the app asks whether to skip it. A "Skip All Further" option suppresses all subsequent prompts for the remainder of the run.
- **Dual Interface:** A CustomTkinter GUI (`app.py`) and an interactive terminal interface (`main.py`) for headless environments.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/gts1117/comic-sorter.git
   cd comic-sorter
   ```

2. Install `unar`, required for `.cbr` extraction:
   ```bash
   # macOS
   brew install unar
   # Linux (Debian/Ubuntu)
   sudo apt-get install unar
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### Graphical Interface
```bash
./startapp.sh
# or
python app.py
```

### Command Line Interface
```bash
./startcli.sh
# or
python main.py
```

---

## Operation Modes

| Mode | Name | Description |
|------|------|-------------|
| 1 | Sort New Library | Processes files from a source folder and sorts them into a destination library. With "Move Files" checked, originals are removed from the source after sorting. |
| 2 | Resort Existing Library | Re-maps and reorganises archives in-place within an existing library directory. |
| 3 | Smart-Merge | Scans the destination library to learn its existing structure, then merges new unsorted files into the correct locations. |

> **Tip:** When sorting from an `Unsorted` staging folder into your main library, use Mode 1 or Mode 3 with "Move Files" checked. Set the **Source** to your `Unsorted` folder and the **Target** to the parent library folder (e.g. `.../Comics`). After sorting, empty subfolders inside the source are cleaned up automatically.

---

## Output Structure

Files are organised into the following hierarchy:

```
Library/
  Publisher/
    Series (IP)/
      Storyline/
        Issue.cbz
  Adult/
    Publisher/
      Series/
        Storyline/
          Issue.cbz
```

---

## Custom Regex Rules

File-parsing logic can be overridden by adding regex templates to `config.json`:

```json
{
    "custom_regexes": [
        "^(?P<publisher>DC)\\s*-\\s*(?P<ip>[A-Z\\s]+)\\s*v(?P<volume>\\d+)?\\s*#(?P<issue>\\d+)"
    ]
}
```

Named groups supported: `publisher`, `ip`, `storyline`, `volume`, `issue`.

---

## ComicVine API Key

To enable online metadata lookup for unrecognised titles, add your ComicVine API key to `config.json`:

```json
{
    "comicvine_api_key": "your_key_here"
}
```

A free API key can be obtained at [comicvine.gamespot.com/api](https://comicvine.gamespot.com/api/).
