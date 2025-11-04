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

## Requirements

- Docker (recommended way to run)
- Optionally, Python 3 if you want to run locally without Docker

## Installation (Docker)

Clone and build the Docker image:

```bash
git clone https://github.com/yourusername/gather-commits-issues-prs.git
cd gather-commits-issues-prs
docker build -t gather-cip .
```

## Usage

### 1. Configure Repositories (repos.json)

Supported formats:

- Flat list (strings)
```json
[
  "owner/repo1",
  "owner/repo2"
]
```

- Flat list (objects with optional branch override)
```json
[
  { "repo": "owner/repo1", "branch": "dev" },
  { "repo": "owner/repo2" }
]
```

- Organization-grouped
```json
{
  "orgs": {
    "owner": [
      { "repo": "repo1", "branch": "dev" },
      "repo2"
    ]
  }
}
```

### 2. Gather Data (Docker)

Recommended run command (mount current folder as /data):

```bash
docker run --rm \
  -v $(pwd):/data \
  --env-file ./.env \
  -e NON_INTERACTIVE=1 \
  gather-cip
```

Common flags (append to the command):
- `-r /data/repos.json` path to repos config (default baked in)
- `-d /data/dates.json` optional milestone/cutoff dates (default baked in)
- `-u /data/github-usernames.json` optional username→full name map (default baked in)
- `-o /data/commits-issues-prs` output directory (default baked in)
- `--since YYYY-MM-DD` overrides the not-before date
- `--branch <name>` global branch (per-repo `branch` in repos.json overrides this)
- `--only-issues` or `--only-commits` or `--only-prs` to limit categories

### GitHub Authentication

Create a `.env` file alongside your `repos.json` with:

```bash
GITHUB_TOKEN=your_personal_access_token_here
```

Pass it to Docker with `--env-file ./.env` (as shown above). For public repos you can omit it but you may hit rate limits.

### GitHub Username Mapping

To map GitHub usernames to full names, convert your CSV to JSON using the included script.

- Run with Docker (recommended):

  ```bash
  docker run --rm \
    --user $(id -u):$(id -g) \
    -v $(pwd):/data \
    --entrypoint python \
    gather-cip csv_to_usernames_json.py /data/path/to/student_data.csv -o /data/github-usernames.json
  ```

  Then pass `-u /data/github-usernames.json` to the main gather run.

- Optional: run locally without Docker

  ```bash
  python csv_to_usernames_json.py path/to/student_data.csv -o github-usernames.json
  ```

CSV columns expected (case-insensitive): `First name`, `Last name`, `GitHub username`.
This creates a JSON file mapping GitHub usernames to full names. `gather.py` will use this mapping to include full names alongside GitHub usernames in the output data.

The resulting JSON structure looks like this:

```json
{
    "github-username": "Full Name", 
    "another-username": "Another Person"
}
```

### Background runs with gather.sh

A helper script is provided to run the gatherer in the background and resume later.

Basic usage:

```bash
# Start in background (container name: gather-cip-job)
./gather.sh start --only-issues

# Follow logs
./gather.sh logs -f

# Resume a previously stopped job
./gather.sh resume

# Stop and remove the background container
./gather.sh stop

# Run attached (foreground)
./gather.sh run --since 2025-03-01

# Rebuild the Docker image
./gather.sh rebuild
```

Environment overrides:

- `DATA_DIR`: host directory to mount at `/data` (default: current directory)
- `ENV_FILE`: path to `.env` file (default: `./.env` if present)

Output persists under your host directory (e.g., `./commits-issues-prs`), so re-running continues from prior progress when possible.

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

- Gather only issues using your current folder as /data:
```bash
docker run --rm -v $(pwd):/data --env-file ./.env -e NON_INTERACTIVE=1 gather-cip --only-issues
```

- Gather with a custom output directory:
```bash
docker run --rm -v $(pwd):/data --env-file ./.env -e NON_INTERACTIVE=1 gather-cip -o /data/out --only-prs
```

## Output Format

Outputs under your chosen output directory (default `./commits-issues-prs` when mounting `-v $(pwd):/data`):

- JSON per repo: `commits-issues-prs/<owner-repo>.json`
- Per-user CSVs per repo:
  - `commits-issues-prs/<owner-repo>/commits/<username>.csv`
  - `commits-issues-prs/<owner-repo>/issues/<username>.csv`
  - `commits-issues-prs/<owner-repo>/prs/<username>.csv`

When GitHub username mappings are provided, the output includes both the GitHub username and the full name for each contributor.

Tip: on Linux, to ensure files are owned by your user, run the container with `--user $(id -u):$(id -g)`. If you previously created files as root, fix with `sudo chown -R $(id -u):$(id -g) commits-issues-prs`.

## License

This project is licensed under the terms included in the LICENSE file.
