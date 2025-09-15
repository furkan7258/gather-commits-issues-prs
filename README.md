# gather-commits-issues-prs

A tool for gathering and presenting contributions (commits, issues, and pull requests) from GitHub repositories.

## Features

- Collects all commits, issues, and pull requests from specified GitHub repositories
- Filters contributions by date ranges
- Handles co-authored commits properly
- Calculates statistics for each contribution (e.g., lines changed, files modified)
- Generates detailed Markdown summaries of contributions by author
- Supports private repositories via GitHub tokens
- Customizable filters and thresholds
- Converts JSON data to CSV/XLSX formats for easier analysis

## Requirements

This project requires Python 3 and has the following dependencies:

- `bs4` (BeautifulSoup4): For HTML parsing
- `python-dotenv`: For managing environment variables (e.g., GitHub token)
- `requests`: For making API calls to GitHub
- `pandas`: For data manipulation and conversion to CSV/XLSX
- `openpyxl`: For Excel file support
- `tqdm`: For progress bars in the terminal

## Installation

1. Clone the repository:

```bash
git clone https://github.com/furkanakkurt1335/gather-commits-issues-prs.git
cd gather-commits-issues-prs
```

2. Set up a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Add your GitHub token (optional, required for private repositories):

```bash
cp .env.example .env
```

Then edit the `.env` file and add your GitHub token.

## Usage

### 1. Configure Repositories

Create or edit `repos.json` with the repositories you want to analyze:

```json
[
  "username/repository",
  "organization/repository"
]
```

### 2. Gather Data

Run the gather script to collect data from the specified repositories:

```bash
python gather.py
```

Options:
- `-r, --repos`: Path to JSON file listing repositories (default: `repos.json`)
- `-o, --output`: Directory for output data (default: `commits-issues-prs`)
- `-b, --branch`: Branch to analyze (default: main/default branch)
- `-s, --since`: Only gather data since this date in YYYY-MM-DD format
- `-u, --usernames`: Path to JSON file mapping GitHub usernames to full names (default: `github-usernames.json`)

### 3. Convert JSON to CSV/XLSX

After gathering data, you can convert the JSON files to CSV or XLSX format for easier analysis:

```bash
python json_to_csv_converter.py [options]
```

Options:
- `--input` or `-i`: Input directory containing JSON files (default: ./commits-issues-prs)
- `--output` or `-o`: Output directory for CSV/XLSX files (default: ./csv_output or ./xlsx_output)
- `--format` or `-f`: Output format, either 'csv' or 'xlsx' (default: xlsx)
- `--file`: Process a specific file instead of all files in the directory

Examples:

```bash
# Convert all JSON files to XLSX format
python json_to_csv_converter.py

# Convert all JSON files to CSV format
python json_to_csv_converter.py --format csv

# Convert a specific JSON file
python json_to_csv_converter.py --file commits-issues-prs/repo-name.json
```

### 4. Combine Data Files

To combine all individual CSV or XLSX files into consolidated files:

```bash
python combine_files.py [options]
```

Options:
- `--csv-input`: Input directory containing CSV files (default: ./csv_output)
- `--csv-output`: Output directory for consolidated CSV files (default: ./consolidated_csv)
- `--xlsx-input`: Input directory containing XLSX files (default: ./xlsx_output)
- `--xlsx-output`: Output directory for consolidated XLSX file (default: ./consolidated_xlsx)

This will create:
- CSV files: `all_commits.csv`, `all_issues.csv`, `all_prs.csv` in the `consolidated_csv` directory
- XLSX file: `all_repositories.xlsx` with three sheets in the `consolidated_xlsx` directory

### GitHub Authentication

For private repositories, you'll need a GitHub token stored in a `.env` file:

1. Create a file named `.env` in the root directory of the project
2. Add your GitHub token in the following format:

    ```bash
    GITHUB_TOKEN=your_personal_access_token_here
    ```

3. If you don't have a `.env` file, the script will prompt you to enter a token if needed
4. The token will be automatically saved to the `.env` file for future use

The `.env` file is included in `.gitignore` to prevent accidentally committing your token.

### GitHub Username Mapping

To map GitHub usernames to full names, the tool supports CSV data import:

1. Use the included `csv_to_usernames_json.py` script to convert CSV data to JSON:

   ```bash
   python csv_to_usernames_json.py path/to/student_data.csv -o github-usernames.json
   ```

2. The CSV should have columns for `First name`, `Last name`, and `GitHub username`
3. This creates a JSON file mapping GitHub usernames to full names
4. `gather.py` will use this mapping to include full names alongside GitHub usernames in the output data

The resulting JSON structure looks like this:

```json
{
    "github-username": "Full Name", 
    "another-username": "Another Person"
}
```

For convenience, a simple script is provided that converts CSV data and gathers repository data:

```bash
# Convert CSV to username mappings and gather data
./run_with_usernames.sh path/to/student_data.csv
```

This script will:

1. Convert the CSV data to GitHub username mappings
2. Use those mappings when gathering repository data

#### Creating a GitHub Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token" (classic)
3. Add a note (e.g., "gather-commits-issues-prs")
4. Select the following scopes:
   - `repo` (for accessing private repositories)
   - `read:user` (for user information)
5. Click "Generate token" and copy the token immediately
6. Add this token to your `.env` file as shown above

## Examples

### Gathering data for a specific repository

```bash
python gather.py -r custom-repos.json -o output-data
```

### Gathering data with username mappings

```bash
python gather.py -r repos.json -u github-usernames.json
```

## Output Formats

### JSON Format

The gathered data is saved as JSON files with the following structure:

- Commits: author (with full name if available), message, date, link, and statistics (files changed, lines modified)
- Issues: author (with full name if available), title, description, labels, assignees, comments, and state
- Pull Requests: same as issues plus commit information

When GitHub username mappings are provided, the output includes both the GitHub username and the full name for each contributor, making the data more readable and easier to identify contributors.

### CSV Format

When using CSV output, three files are created for each repository:
- `{repo_name}_commits.csv`: Contains all commit data
- `{repo_name}_issues.csv`: Contains all issues data
- `{repo_name}_prs.csv`: Contains all pull requests data

The consolidated CSV files combine data from all repositories with an additional `repo` column.

### XLSX Format

When using XLSX output:
- Individual repository files have three sheets: Commits, Issues, and Pull Requests
- The consolidated file (`all_repositories.xlsx`) has three sheets that combine data from all repositories

For more details on the JSON to CSV/XLSX conversion, see [CONVERTER_README.md](CONVERTER_README.md).

## License

This project is licensed under the terms included in the LICENSE file.
