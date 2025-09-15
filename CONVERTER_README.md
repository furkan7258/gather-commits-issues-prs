# JSON to CSV/XLSX Converter for gather-commits-issues-prs

This tool converts the JSON data from the `gather-commits-issues-prs` repository into CSV or XLSX format for better human readability and analysis.

## Features

- Converts commits, issues, and pull requests data from JSON to CSV or XLSX
- Creates separate CSV files for each data type or a single XLSX with multiple sheets
- Can process a single JSON file or all files in a directory
- Flattens nested JSON structure to make data analysis easier

## Prerequisites

- Python 3.6 or higher
- Required packages:
  - pandas
  - openpyxl (for XLSX output)

## Installation

1. Clone or download this repository
2. Install required packages:

```bash
pip install pandas openpyxl
```

## Usage

Run the script with the following command:

```bash
python json_to_csv_converter.py [options]
```

### Options

- `--input` or `-i`: Input directory containing JSON files (default: ./commits-issues-prs)
- `--output` or `-o`: Output directory for CSV/XLSX files (default: ./csv_output)
- `--format` or `-f`: Output format, either 'csv' or 'xlsx' (default: xlsx)
- `--file`: Process a specific file instead of all files in the directory

### Examples

Convert all JSON files to XLSX format:
```bash
python json_to_csv_converter.py
```

Convert all JSON files to CSV format:
```bash
python json_to_csv_converter.py --format csv
```

Convert a specific JSON file to XLSX:
```bash
python json_to_csv_converter.py --file commits-issues-prs/bounswe-bounswe2025group1.json
```

Specify custom input and output directories:
```bash
python json_to_csv_converter.py --input /path/to/json/files --output /path/to/output
```

## Output Format

### CSV Output

When using CSV format, three files are created for each input JSON file:
- `{repo_name}_commits.csv`: Contains all commit data
- `{repo_name}_issues.csv`: Contains all issues data
- `{repo_name}_prs.csv`: Contains all pull requests data

### XLSX Output

When using XLSX format, a single Excel file is created with three sheets:
- `Commits`: Contains all commit data
- `Issues`: Contains all issues data
- `Pull Requests`: Contains all pull requests data

## Data Fields

### Commits Sheet/CSV
- snapshot_date: Date of the snapshot
- username: GitHub username of the author
- author_full_name: Full name of the author
- message: Commit message
- date: Date of the commit
- link: Link to the commit on GitHub
- files_changed: Number of files changed in the commit
- total_changes: Total number of lines changed in the commit

### Issues Sheet/CSV
- snapshot_date: Date of the snapshot
- username: GitHub username of the creator
- author_full_name: Full name of the creator
- title: Issue title
- description: Issue description
- date: Creation date of the issue
- state: Issue state (open/closed)
- link: Link to the issue on GitHub
- labels: Comma-separated list of labels
- assignees: Comma-separated list of assignees' usernames
- assignee_full_names: Comma-separated list of assignees' full names
- comment_count: Number of comments on the issue

### Pull Requests Sheet/CSV
- snapshot_date: Date of the snapshot
- username: GitHub username of the creator
- author_full_name: Full name of the creator
- title: Pull request title
- description: Pull request description
- date: Creation date of the pull request
- state: Pull request state (open/closed/merged)
- link: Link to the pull request on GitHub
- labels: Comma-separated list of labels
- assignees: Comma-separated list of assignees' usernames
- assignee_full_names: Comma-separated list of assignees' full names
- files_changed: Number of files changed in the pull request
- total_changes: Total number of lines changed in the pull request
- comment_count: Number of comments on the pull request
