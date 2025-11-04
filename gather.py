#!/usr/bin/env python3
# filepath: /Users/furkan1049/repos/furkanakkurt1335/gather-commits-issues-prs/gather.py
import requests, os, json, argparse, re, time, logging, sys, csv, tomllib
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm
from dotenv import load_dotenv

# Function declarations first
def get_args():
    parser = argparse.ArgumentParser(description='Gather commits and issues from GitHub repositories')
    parser.add_argument('-r', '--repos', help='Path to the JSON file with the repositories', type=str, default='repos.json')
    parser.add_argument('-d', '--dates', help='Path to the JSON file with the milestone dates (deprecated; prefer --config TOML)', type=str, default=None)
    parser.add_argument('-c', '--config', help='Path to the TOML config file (preferred). Default: config.toml if exists', type=str, default=None)
    parser.add_argument('-o', '--output', help='Path to the output directory', type=str, default='commits-issues-prs')
    parser.add_argument('-b', '--branch', help='Branch to gather data from', type=str)
    parser.add_argument('-s', '--since', help='Only gather data since this date (YYYY-MM-DD)', type=str)
    parser.add_argument('-u', '--usernames', help='Path to the JSON file mapping GitHub usernames to full names', type=str, default='github-usernames.json')
    parser.add_argument('-v', '--verbose', help='Verbose output (INFO level)', action='store_true')
    parser.add_argument('--debug', help='Debug output (DEBUG level)', action='store_true')
    # Category selection
    parser.add_argument('--only-commits', help='Gather only commits', action='store_true')
    parser.add_argument('--only-issues', help='Gather only issues', action='store_true')
    parser.add_argument('--only-prs', help='Gather only pull requests', action='store_true')
    return parser.parse_args()

def get_diff(url, headers, retry_count=3):
    """Get the diff information for a commit"""
    for attempt in range(retry_count):
        try:
            logging.debug(f"Fetching diff from {url} (attempt {attempt+1}/{retry_count})")
            commit_req = requests.get(url, headers=headers)
            commit_req.raise_for_status()
            commit_res = commit_req.json()
            filenames = {file['filename'] for file in commit_res['files']}
            total = commit_res['stats']['total']
            return {'filenames': filenames, 'total': total}
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            if attempt == retry_count - 1:
                logging.error(f"Error getting diff from {url}: {e}")
                return {'filenames': set(), 'total': 0}
            # Handle rate limiting
            if hasattr(e, 'response') and e.response and e.response.status_code == 403:
                reset_time = int(e.response.headers.get('X-RateLimit-Reset', 0))
                sleep_time = max(0, reset_time - time.time()) + 1
                if sleep_time > 0 and sleep_time < 300:  # Don't wait more than 5 minutes
                    logging.warning(f"Rate limit exceeded. Waiting for {sleep_time:.0f} seconds...")
                    time.sleep(sleep_time)
            logging.debug(f"Request failed: {e}. Retrying after exponential backoff.")
            time.sleep(2 ** attempt)  # Exponential backoff

def load_date_config(dates_file=None, since_date=None):
    """Load date configuration from file or use default/provided dates"""
    default_not_before_date = {'year': 2025, 'month': 2, 'day': 10, 'hour': 0, 'minute': 0, 'second': 0}
    default_ms_dates = [
        {'year': 2025, 'month': 5, 'day': 15, 'hour': 9, 'minute': 0, 'second': 0}
    ]

    not_before_date = default_not_before_date
    ms_dates = default_ms_dates

    if dates_file:
        path = Path(dates_file)
        if path.exists():
            logging.info(f"Loading date configuration from {dates_file}")
            with path.open() as f:
                date_config = json.load(f)
                if 'not_before_date' in date_config:
                    not_before_date = date_config['not_before_date']
                    logging.debug(f"Using custom not_before_date: {not_before_date}")
                if 'milestone_dates' in date_config:
                    ms_dates = date_config['milestone_dates']
                    logging.debug(f"Using custom milestone_dates: {ms_dates}")
        else:
            logging.warning(f"Date configuration file {dates_file} not found, using defaults")

    # Override with command line parameter if provided
    if since_date:
        try:
            date_parts = since_date.split('-')
            not_before_date = {
                'year': int(date_parts[0]),
                'month': int(date_parts[1]),
                'day': int(date_parts[2]),
                'hour': 0, 'minute': 0, 'second': 0
            }
            logging.info(f"Using since date from command line: {since_date}")
        except (ValueError, IndexError):
            logging.error(f"Invalid date format: {since_date}. Using default.")

    # Format dates
    not_before_d = {
        'year': f'{not_before_date["year"]:04d}',
        'month': f'{not_before_date["month"]:02d}',
        'day': f'{not_before_date["day"]:02d}',
        'hour': f'{not_before_date["hour"]:02d}',
        'minute': f'{not_before_date["minute"]:02d}',
        'second': f'{not_before_date["second"]:02d}'
    }

    formatted_ms_dates = []
    for date in ms_dates:
        formatted = {
            'year': f'{date["year"]:04d}',
            'month': f'{date["month"]:02d}',
            'day': f'{date["day"]:02d}',
            'hour': f'{date["hour"]:02d}',
            'minute': f'{date["minute"]:02d}',
            'second': f'{date["second"]:02d}'
        }
        formatted_ms_dates.append(formatted)

    return not_before_d, formatted_ms_dates

def load_date_config_toml(config_file=None, since_date=None):
    """Load date configuration from a TOML file. Expected structure:
    [dates.not_before_date]
    year=2025
    month=2
    day=10
    hour=0
    minute=0
    second=0

    [[dates.milestone_dates]]
    year=2025
    month=5
    day=15
    hour=9
    minute=0
    second=0
    """
    # Defaults
    default_not_before_date = {'year': 2025, 'month': 2, 'day': 10, 'hour': 0, 'minute': 0, 'second': 0}
    default_ms_dates = [
        {'year': 2025, 'month': 5, 'day': 15, 'hour': 9, 'minute': 0, 'second': 0}
    ]

    not_before_date = default_not_before_date
    ms_dates = default_ms_dates

    path = Path(config_file) if config_file else Path('config.toml')
    if path.exists():
        try:
            with path.open('rb') as f:
                cfg = tomllib.load(f)
            dates = cfg.get('dates', {})
            nb = dates.get('not_before_date') or dates.get('not_before')
            if isinstance(nb, dict):
                not_before_date = {
                    'year': int(nb.get('year', default_not_before_date['year'])),
                    'month': int(nb.get('month', default_not_before_date['month'])),
                    'day': int(nb.get('day', default_not_before_date['day'])),
                    'hour': int(nb.get('hour', default_not_before_date['hour'])),
                    'minute': int(nb.get('minute', default_not_before_date['minute'])),
                    'second': int(nb.get('second', default_not_before_date['second']))
                }
            ms = dates.get('milestone_dates') or dates.get('milestones') or []
            if isinstance(ms, list) and ms:
                ms_dates = []
                for m in ms:
                    if isinstance(m, dict):
                        ms_dates.append({
                            'year': int(m.get('year', default_ms_dates[0]['year'])),
                            'month': int(m.get('month', default_ms_dates[0]['month'])),
                            'day': int(m.get('day', default_ms_dates[0]['day'])),
                            'hour': int(m.get('hour', default_ms_dates[0]['hour'])),
                            'minute': int(m.get('minute', default_ms_dates[0]['minute'])),
                            'second': int(m.get('second', default_ms_dates[0]['second']))
                        })
            logging.info(f"Loaded date config from TOML: {path}")
        except Exception as e:
            logging.warning(f"Failed to read TOML config at {path}: {e}. Falling back to defaults.")

    # Override with --since
    if since_date:
        try:
            date_parts = since_date.split('-')
            not_before_date = {
                'year': int(date_parts[0]),
                'month': int(date_parts[1]),
                'day': int(date_parts[2]),
                'hour': 0, 'minute': 0, 'second': 0
            }
            logging.info(f"Using since date from command line: {since_date}")
        except (ValueError, IndexError):
            logging.error(f"Invalid date format: {since_date}. Using defaults from TOML or built-in.")

    # Format strings
    not_before_d = {
        'year': f'{not_before_date["year"]:04d}',
        'month': f'{not_before_date["month"]:02d}',
        'day': f'{not_before_date["day"]:02d}',
        'hour': f'{not_before_date["hour"]:02d}',
        'minute': f'{not_before_date["minute"]:02d}',
        'second': f'{not_before_date["second"]:02d}'
    }
    formatted_ms_dates = []
    for date in ms_dates:
        formatted = {
            'year': f'{date["year"]:04d}',
            'month': f'{date["month"]:02d}',
            'day': f'{date["day"]:02d}',
            'hour': f'{date["hour"]:02d}',
            'minute': f'{date["minute"]:02d}',
            'second': f'{date["second"]:02d}'
        }
        formatted_ms_dates.append(formatted)
    return not_before_d, formatted_ms_dates

def get_full_name(username, username_mappings):
    """Get full name from GitHub username if available"""
    return username_mappings.get(username, username)

def setup_logger(args):
    """Configure the logger based on verbosity"""
    # Create logger
    logger = logging.getLogger('gather')
    logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter

    # Clear any existing handlers
    logger.handlers = []

    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Choose a writable log path
    env_log_path = os.getenv('LOG_PATH')
    log_path = None
    if env_log_path:
        # Allow special files like /dev/stdout
        if env_log_path.startswith('/dev/'):
            log_path = Path(env_log_path)
        else:
            log_path = Path(env_log_path)
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logging.getLogger().warning(f"Cannot create log directory {log_path.parent}: {e}. File logging disabled.")
                log_path = None
    else:
        # default to output directory to ensure host-writable when mounted
        out_dir = Path(getattr(args, 'output', 'commits-issues-prs'))
        candidate = out_dir / 'gather.log'
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            log_path = candidate
        except Exception as e:
            logging.getLogger().warning(f"Cannot create default log directory {candidate.parent}: {e}. File logging disabled.")
            log_path = None

    # File handler with absolute path
    file_handler = None
    try:
        if log_path is None:
            raise RuntimeError('No writable log path')
        file_handler = logging.FileHandler(str(log_path), mode='w', encoding='utf-8')
        if args.debug:
            file_handler.setLevel(logging.DEBUG)
        elif args.verbose:
            file_handler.setLevel(logging.INFO)
        else:
            file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(formatter)
    except Exception as e:
        logging.getLogger().warning(f"File logging disabled: {e}")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)  # Explicitly use stdout
    if args.debug:
        console_handler.setLevel(logging.DEBUG)
    elif args.verbose:
        console_handler.setLevel(logging.INFO)
    else:
        console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    if file_handler:
        logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Configure root logger as well
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    if file_handler:
        root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Disable propagation to avoid duplicate logs
    logger.propagate = False

    logger.info("Logging initialized at level: %s (console), %s (file)",
              logging.getLevelName(console_handler.level),
              logging.getLevelName(file_handler.level))
    
    return logger

def setup_github_auth(_):
    """Setup GitHub authentication headers"""
    headers = {'Accept': 'application/vnd.github.v3+json'}

    # Load .env file if it exists
    env_path = Path('.env')

    # Try to get token from environment variables (loads from .env if exists)
    load_dotenv()
    token = os.getenv('GITHUB_TOKEN')

    # If token not found, optionally prompt unless NON_INTERACTIVE is set
    if not token and os.getenv('NON_INTERACTIVE', '0') != '1':
        token_needed = input('Do you need to access private repositories? (y/N): ')
        if token_needed.lower() == 'y':
            token = input('Enter your GitHub token: ')
            with env_path.open('w') as env_file:
                env_file.write(f'GITHUB_TOKEN={token}\n')
            logging.info("Saved token to .env file")
            load_dotenv(override=True)

    if token:
        headers['Authorization'] = f'Bearer {token}'
        logging.info("Using GitHub token for authentication")
    else:
        logging.warning("No GitHub token provided, API rate limits may apply")

    return headers

def process_repos(repo_entries, headers, args, not_before_d, ms_dates_formatted, username_mappings={}):
    """Process each repository to gather commits, issues, and PRs"""
    data_path = Path(args.output)
    data_path.mkdir(exist_ok=True)
    logging.info(f"Output directory: {data_path}")

    coauthor_pattern = re.compile(r'Co-authored-by: (.*) <.*>')
    gmt_str = '+03:00'

    not_before_date = datetime.fromisoformat(
        f'{not_before_d["year"]}-{not_before_d["month"]}-{not_before_d["day"]}T'
        f'{not_before_d["hour"]}:{not_before_d["minute"]}:{not_before_d["second"]}{gmt_str}'
    )
    logging.info(f"Not before date: {not_before_date}")

    ms_dates = [datetime.fromisoformat(
        f'{date["year"]}-{date["month"]}-{date["day"]}T'
        f'{date["hour"]}:{date["minute"]}:{date["second"]}{gmt_str}'
    ) for date in ms_dates_formatted]
    logging.info(f"Milestone dates: {', '.join(ms.strftime('%Y-%m-%d %H:%M:%S') for ms in ms_dates)}")

    for entry in tqdm(repo_entries, desc="Processing repositories"):
        repo_tuple = entry['repo']
        branch_override = entry.get('branch')
        logging.info(f'Gathering data for {repo_tuple}' + (f" on branch {branch_override}" if branch_override else ""))
        user_t, repo_t = repo_tuple.split('/')
        ms_l = [{'date': ms_date.strftime('%Y-%m-%d %H:%M:%S'), 'commits': {}, 'issues': {}, 'prs': {}} for ms_date in ms_dates]
        repo_url = f'https://api.github.com/repos/{user_t}/{repo_t}'

        # Verify repository exists and is accessible
        logging.debug(f"Verifying repository: {repo_url}")
        repo_req = requests.get(repo_url, headers=headers)
        if repo_req.status_code == 404:
            logging.error(f"Repository {repo_tuple} not found or inaccessible. Skipping.")
            continue
        repo_req.raise_for_status()
        repo_res = repo_req.json()

        repo_path = data_path / f'{user_t}-{repo_t}.json'
        prev_diffs = {}

        # Determine which categories to gather based on flags
        only_commits = args.only_commits
        only_issues = args.only_issues
        only_prs = args.only_prs
        gather_commits_flag = (only_commits and not (only_issues or only_prs)) or (not only_commits and not only_issues and not only_prs) or (only_commits)
        gather_issues_flag = (only_issues and not only_commits) or (not only_commits and not only_issues and not only_prs) or (only_issues)
        gather_prs_flag = (only_prs and not only_commits) or (not only_commits and not only_issues and not only_prs) or (only_prs)

        # Gather commits if enabled
        if gather_commits_flag:
            gather_commits(user_t, repo_t, headers, args, repo_path, not_before_date, ms_dates, ms_l,
                          coauthor_pattern, prev_diffs, username_mappings, branch_override=branch_override)

        # Gather issues and PRs
        if gather_issues_flag or gather_prs_flag:
            gather_issues_and_prs(user_t, repo_t, headers, repo_path, not_before_date, ms_dates, ms_l, prev_diffs, username_mappings,
                                  include_issues=gather_issues_flag, include_prs=gather_prs_flag)

        # Sort and finalize data
        finalize_repo_data(ms_l, ms_dates, repo_path)
        write_per_user_csvs(ms_l, data_path, f'{user_t}-{repo_t}',
                            write_commits=gather_commits_flag,
                            write_issues=gather_issues_flag,
                            write_prs=gather_prs_flag)
        logging.info(f'✓ Finished gathering all data for {repo_tuple}')

def gather_commits(user_t, repo_t, headers, args, repo_path, not_before_date, ms_dates, ms_l,
                  coauthor_pattern, prev_diffs, username_mappings={}, branch_override=None):
    """Gather commits for a repository"""
    logging.info(f'  Gathering commits for {user_t}/{repo_t}...')
    page_n = 1

    with tqdm(desc=f"  {user_t}/{repo_t} - commits", unit="page") as progress:
        while True:
            effective_branch = branch_override or args.branch
            if effective_branch:
                commits_url = f'https://api.github.com/repos/{user_t}/{repo_t}/commits?sha={effective_branch}&page={page_n}'
            else:
                commits_url = f'https://api.github.com/repos/{user_t}/{repo_t}/commits?page={page_n}'

            try:
                logging.debug(f"Fetching commits from {commits_url}")
                commits_req = requests.get(commits_url, headers=headers)
                commits_req.raise_for_status()
                commits = commits_req.json()
            except requests.exceptions.RequestException as e:
                if hasattr(e, 'response') and e.response:
                    if e.response.status_code == 403 and 'API rate limit exceeded' in e.response.text:
                        logging.warning('API rate limit exceeded. Try adding a GitHub token or wait an hour.')
                        reset_time = int(e.response.headers.get('X-RateLimit-Reset', 0))
                        wait_time = max(0, reset_time - time.time()) + 1
                        if wait_time < 300:  # Don't wait more than 5 minutes
                            logging.info(f"Waiting for {wait_time:.0f} seconds...")
                            time.sleep(wait_time)
                            continue
                    elif e.response.status_code == 401:
                        logging.error('Bad credentials, please check your token.')
                logging.error(f"Error fetching commits: {e}")
                break

            if not commits or not isinstance(commits, list):
                break

            seen_before = False
            progress.update(1)

            for commit in commits:
                try:
                    commit_url = commit['url']
                    date_t = datetime.fromisoformat(commit['commit']['author']['date'].replace('Z', '+00:00'))

                    if date_t < not_before_date:
                        seen_before = True
                        break

                    date_str = (date_t + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')

                    # Determine the author
                    if ('author' in commit and commit['author'] and 'login' in commit['author']):
                        author_t = commit['author']['login']
                    elif 'commit' in commit and 'author' in commit['commit'] and 'name' in commit['commit']['author']:
                        author_t = commit['commit']['author']['name']
                    else:
                        author_t = 'unknown'

                    # Get co-authors from commit message
                    message_t = commit['commit']['message']
                    coauthors = coauthor_pattern.findall(message_t)
                    html_url = commit['html_url']

                    # Get diff information
                    diff = get_diff(commit_url, headers)
                    sha = commit['sha']
                    prev_diffs[sha] = diff
                    diff = {'files': len(diff['filenames']), 'total': diff['total']}

                    # Add commit data to milestone lists
                    for i, ms_date in enumerate(ms_dates):
                        if date_t < ms_date:
                            for author_name in coauthors + [author_t]:
                                # Try to get the full name from mappings
                                full_name = get_full_name(author_name, username_mappings)

                                if author_name not in ms_l[i]['commits']:
                                    ms_l[i]['commits'][author_name] = {
                                        'count': 0,
                                        'list': [],
                                        'full_name': full_name
                                    }
                                ms_l[i]['commits'][author_name]['list'].append({
                                    'message': message_t,
                                    'date': date_str,
                                    'link': html_url,
                                    'diff': diff
                                })
                                ms_l[i]['commits'][author_name]['count'] += 1
                            break
                except Exception as e:
                    logging.error(f"Error processing commit {commit.get('sha', 'unknown')}: {e}")
                    continue

            # Save progress after each page
            with repo_path.open('w') as f:
                json.dump(ms_l, f, ensure_ascii=False, indent=4)
            logging.debug(f"Saved commits progress after page {page_n}")

            if seen_before:
                logging.debug("Found commits before the cut-off date, stopping pagination")
                break

            page_n += 1
            logging.debug(f"Moving to commits page {page_n}")

def gather_issues_and_prs(user_t, repo_t, headers, repo_path, not_before_date, ms_dates, ms_l, prev_diffs, username_mappings={}, include_issues=True, include_prs=True):
    """Gather issues and PRs for a repository"""
    logging.info(f'  Gathering issues and PRs for {user_t}/{repo_t}...')
    page_n = 1

    with tqdm(desc=f"  {user_t}/{repo_t} - issues/PRs", unit="page") as progress:
        while True:
            issue_url = f'https://api.github.com/repos/{user_t}/{repo_t}/issues?state=all&page={page_n}'

            try:
                logging.debug(f"Fetching issues from {issue_url}")
                iss_req = requests.get(issue_url, headers=headers)
                iss_req.raise_for_status()
                issues = iss_req.json()
            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching issues: {e}")
                break

            if not issues or not isinstance(issues, list):
                break

            seen_before = False
            progress.update(1)

            for issue in issues:
                try:
                    is_pr = 'pull_request' in issue
                    key_t = 'prs' if is_pr else 'issues'
                    # Skip unwanted categories
                    if (is_pr and not include_prs) or ((not is_pr) and not include_issues):
                        continue
                    date_t = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))

                    if date_t < not_before_date:
                        seen_before = True
                        break

                    date_str = (date_t + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
                    title_t = issue['title']
                    desc_t = issue.get('body', '')
                    label_l = [label['name'] for label in issue.get('labels', [])]
                    assignee_l = [assignee['login'] for assignee in issue.get('assignees', [])]
                    author_t = issue['user']['login']

                    # Gather comments
                    comments = []
                    if issue.get('comments', 0) > 0:
                        try:
                            comments_url = issue['comments_url']
                            comments_req = requests.get(comments_url, headers=headers)
                            comments_req.raise_for_status()
                            comments_res = comments_req.json()
                            comments = []
                            for comment in comments_res:
                                comment_author = comment['user']['login']
                                comment_author_full_name = get_full_name(comment_author, username_mappings)
                                comments.append({
                                    'author': comment_author,
                                    'author_full_name': comment_author_full_name,
                                    'body': comment.get('body', '')
                                })
                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error fetching comments: {e}")

                    html_url = issue['html_url']

                    # For PRs, get commit information
                    if is_pr:
                        try:
                            commits_url = issue['pull_request']['url'] + '/commits'
                            commits_req = requests.get(commits_url, headers=headers)
                            commits_req.raise_for_status()
                            commits_res = commits_req.json()

                            urls = {commit['sha']: commit['url'] for commit in commits_res}
                            diffs = []
                            for sha, url in urls.items():
                                if sha not in prev_diffs:
                                    diff = get_diff(url, headers)
                                    prev_diffs[sha] = diff
                                else:
                                    diff = prev_diffs[sha]
                                diffs.append(diff)

                            diff_d = {'files': set(), 'total': sum(diff['total'] for diff in diffs)}
                            for diff in diffs:
                                diff_d['files'].update(diff['filenames'])
                            diff_d['files'] = len(diff_d['files'])
                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error fetching PR commits: {e}")
                            diff_d = {'files': 0, 'total': 0}

                    # Add issue/PR to milestone lists
                    for i, ms_date in enumerate(ms_dates):
                        if date_t < ms_date:
                            # Try to get the full name from mappings
                            full_name = get_full_name(author_t, username_mappings)

                            if author_t not in ms_l[i][key_t]:
                                ms_l[i][key_t][author_t] = {
                                    'count': 0,
                                    'list': [],
                                    'full_name': full_name
                                }

                            # Also map assignees to full names if possible
                            assignee_full_names = []
                            for assignee in assignee_l:
                                assignee_full_names.append(get_full_name(assignee, username_mappings))

                            d = {
                                'title': title_t,
                                'desc': desc_t,
                                'date': date_str,
                                'labels': label_l,
                                'assignees': assignee_l,
                                'assignee_full_names': assignee_full_names,
                                'link': html_url,
                                'state': issue['state'],
                                'comments': comments
                            }

                            if is_pr:
                                d['diff'] = diff_d

                            ms_l[i][key_t][author_t]['list'].append(d)
                            ms_l[i][key_t][author_t]['count'] += 1
                            break
                except Exception as e:
                    logging.error(f"Error processing issue/PR #{issue.get('number', 'unknown')}: {e}")
                    continue

            # Save progress after each page
            with repo_path.open('w') as f:
                json.dump(ms_l, f, ensure_ascii=False, indent=4)
            logging.debug(f"Saved issues/PRs progress after page {page_n}")

            if seen_before:
                logging.debug("Found issues/PRs before the cut-off date, stopping pagination")
                break

            page_n += 1
            logging.debug(f"Moving to issues/PRs page {page_n}")

def finalize_repo_data(ms_l, ms_dates, repo_path):
    """Sort and finalize repository data"""
    logging.info(f"Finalizing data for {repo_path.name}")

    # Calculate stats
    for i, _ in enumerate(ms_dates):
        commit_count = sum(author_data['count'] for author_data in ms_l[i]['commits'].values())
        issue_count = sum(author_data['count'] for author_data in ms_l[i]['issues'].values())
        pr_count = sum(author_data['count'] for author_data in ms_l[i]['prs'].values())
        logging.info(f"Milestone {i+1}: {commit_count} commits, {issue_count} issues, {pr_count} PRs")

    # Sort by date
    logging.debug("Sorting entries by date")
    for i, _ in enumerate(ms_dates):
        for key_t in ['commits', 'issues', 'prs']:
            for author_t in ms_l[i][key_t]:
                ms_l[i][key_t][author_t]['list'] = sorted(
                    ms_l[i][key_t][author_t]['list'],
                    key=lambda x: x['date']
                )

    # Sort keys alphabetically
    logging.debug("Sorting authors alphabetically")
    for i, _ in enumerate(ms_dates):
        for key_t in ['commits', 'issues', 'prs']:
            ms_l[i][key_t] = dict(sorted(ms_l[i][key_t].items()))

    # Save final data
    logging.debug(f"Saving final data to {repo_path}")
    with repo_path.open('w') as f:
        json.dump(ms_l, f, ensure_ascii=False, indent=4)

def write_per_user_csvs(ms_l, output_base_path, repo_slug, write_commits=True, write_issues=True, write_prs=True):
    logging.info(f"Writing per-user CSVs for {repo_slug}")
    repo_dir = output_base_path / repo_slug
    commits_dir = repo_dir / 'commits'
    issues_dir = repo_dir / 'issues'
    prs_dir = repo_dir / 'prs'
    if write_commits:
        commits_dir.mkdir(parents=True, exist_ok=True)
    if write_issues:
        issues_dir.mkdir(parents=True, exist_ok=True)
    if write_prs:
        prs_dir.mkdir(parents=True, exist_ok=True)

    def sanitize(name):
        return re.sub(r'[^A-Za-z0-9_.-]+', '_', name)

    def aggregate(category):
        agg = {}
        for idx, ms in enumerate(ms_l):
            ms_date = ms['date']
            for author, data in ms[category].items():
                lst = data.get('list', [])
                full_name = data.get('full_name', author)
                if author not in agg:
                    agg[author] = {'full_name': full_name, 'rows': []}
                for item in lst:
                    row = {
                        'repository': repo_slug,
                        'author': author,
                        'author_full_name': full_name,
                        'date': item.get('date', ''),
                        'milestone_index': idx + 1,
                        'milestone_date': ms_date,
                        'link': item.get('link', '')
                    }
                    if category == 'commits':
                        diff = item.get('diff', {})
                        row.update({
                            'message': item.get('message', ''),
                            'diff_files': diff.get('files', 0),
                            'diff_total': diff.get('total', 0)
                        })
                    else:
                        row.update({
                            'title': item.get('title', ''),
                            'desc': item.get('desc', ''),
                            'labels': ';'.join(item.get('labels', [])),
                            'assignees': ';'.join(item.get('assignees', [])),
                            'assignee_full_names': ';'.join(item.get('assignee_full_names', [])),
                            'state': item.get('state', ''),
                            'comments_count': len(item.get('comments', []))
                        })
                        if category == 'prs':
                            diff = item.get('diff', {})
                            row.update({
                                'diff_files': diff.get('files', 0),
                                'diff_total': diff.get('total', 0)
                            })
                    agg[author]['rows'].append(row)
        return agg

    commits_agg = aggregate('commits') if write_commits else {}
    issues_agg = aggregate('issues') if write_issues else {}
    prs_agg = aggregate('prs') if write_prs else {}

    def write_csv(dir_path, author, rows, headers):
        file_path = dir_path / f"{sanitize(author)}.csv"
        with file_path.open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)

    commit_headers = ['repository','author','author_full_name','date','milestone_index','milestone_date','link','message','diff_files','diff_total']
    issue_headers = ['repository','author','author_full_name','date','milestone_index','milestone_date','link','title','desc','labels','assignees','assignee_full_names','state','comments_count']
    pr_headers = ['repository','author','author_full_name','date','milestone_index','milestone_date','link','title','desc','labels','assignees','assignee_full_names','state','comments_count','diff_files','diff_total']

    for author, data in commits_agg.items():
        write_csv(commits_dir, author, data['rows'], commit_headers)
    for author, data in issues_agg.items():
        write_csv(issues_dir, author, data['rows'], issue_headers)
    for author, data in prs_agg.items():
        write_csv(prs_dir, author, data['rows'], pr_headers)

def main():
    args = get_args()

    try:
        # Setup logger first, before any other operations
        logger = setup_logger(args)

        # Add virtual environment to path if it exists
        venv_path = Path(__file__).parent / '.venv'
        if venv_path.exists():
            venv_site_packages = list(venv_path.glob('lib/python*/site-packages'))
            if venv_site_packages:
                sys.path.insert(0, str(venv_site_packages[0]))
                logger.info(f"Using Python packages from virtual environment: {venv_site_packages[0]}")

        # Setup authentication
        headers = setup_github_auth(None)

        # Load date configuration (prefer TOML config)
        use_toml = False
        cfg_path = None
        if args.config:
            cfg_path = args.config
            use_toml = True
        else:
            # default to config.toml if present
            if Path('config.toml').exists():
                cfg_path = 'config.toml'
                use_toml = True
        if use_toml:
            not_before_d, ms_dates_formatted = load_date_config_toml(cfg_path, args.since)
            logging.info(f"Using TOML config: not before date: {not_before_d} and milestone dates: {ms_dates_formatted}")
        else:
            not_before_d, ms_dates_formatted = load_date_config(args.dates, args.since)
            logging.info(f"Using JSON dates config: not before date: {not_before_d} and milestone dates: {ms_dates_formatted}")
    except Exception as e:
        logging.error(f"Error during setup: {e}")
        sys.exit(1)
    # Ensure output directory exists
    data_path = Path(args.output)
    data_path.mkdir(exist_ok=True)
    logging.info(f"Output directory: {data_path}")
    logging.info("Starting data gathering...")

    # Load repositories list
    repos_path = Path(args.repos)
    if not repos_path.exists():
        with repos_path.open('w') as f:
            json.dump([], f)
        logging.error(f'Please add your repositories to the file `{args.repos}` in the format: ["username/repo"]')
        return

    with repos_path.open() as f:
        raw_repos_config = json.load(f)

    if not raw_repos_config:
        logging.error(f'No repositories found in {args.repos}. Please add repositories in the format: ["owner/repo"] or with org groups.')
        return

    def normalize_repo_entries(cfg):
        entries = []
        # Case 1: flat list
        if isinstance(cfg, list):
            for item in cfg:
                if isinstance(item, str):
                    entries.append({'repo': item, 'branch': None})
                elif isinstance(item, dict):
                    full = item.get('repo') or item.get('full') or item.get('name')
                    branch = item.get('branch')
                    if full and '/' in full:
                        entries.append({'repo': full, 'branch': branch})
                    else:
                        logging.warning(f"Skipping invalid repo entry (expecting 'owner/repo'): {item}")
                else:
                    logging.warning(f"Skipping unsupported repo entry type: {item}")
            return entries
        # Case 2: dict with org groups: { "orgs": { "org": [ ... ] } }
        if isinstance(cfg, dict):
            orgs = None
            if 'orgs' in cfg and isinstance(cfg['orgs'], dict):
                orgs = cfg['orgs']
            elif 'organizations' in cfg and isinstance(cfg['organizations'], dict):
                orgs = cfg['organizations']
            if orgs is not None:
                for owner, items in orgs.items():
                    if not isinstance(items, list):
                        logging.warning(f"Skipping invalid list for org {owner}: {items}")
                        continue
                    for item in items:
                        if isinstance(item, str):
                            # item is repo name without owner
                            entries.append({'repo': f"{owner}/{item}", 'branch': None})
                        elif isinstance(item, dict):
                            # allow {'repo':'name' or 'owner/repo', 'branch': 'dev'}
                            raw = item.get('repo') or item.get('name') or item.get('full')
                            branch = item.get('branch')
                            if raw and '/' in raw:
                                entries.append({'repo': raw, 'branch': branch})
                            elif raw:
                                entries.append({'repo': f"{owner}/{raw}", 'branch': branch})
                            else:
                                logging.warning(f"Skipping invalid repo entry under org {owner}: {item}")
                        else:
                            logging.warning(f"Skipping unsupported repo entry under org {owner}: {item}")
                return entries
            # Fallback: if dict but not recognized, try if it directly encodes a single repo
            full = cfg.get('repo') or cfg.get('full') or cfg.get('name')
            if full and '/' in full:
                entries.append({'repo': full, 'branch': cfg.get('branch')})
                return entries
        logging.error("Unsupported repos.json format. Please provide a flat array or an object with 'orgs'.")
        return entries

    repo_entries = normalize_repo_entries(raw_repos_config)
    if not repo_entries:
        logging.error('No valid repositories parsed from repos.json')
        return


    # Load GitHub username to full name mappings if available
    username_mappings = {}
    username_path = Path(args.usernames)
    if username_path.exists():
        try:
            with username_path.open('r', encoding='utf-8') as f:
                username_mappings = json.load(f)
            logging.info(f"Loaded {len(username_mappings)} username mappings from {args.usernames}")
        except Exception as e:
            logging.error(f"Error loading username mappings: {e}")
    else:
        logging.warning(f"Username mapping file {args.usernames} not found. Using GitHub usernames as is.")
        # Try to create an example username mapping in the output directory; ignore permission errors
        try:
            out_dir = Path(args.output)
            out_dir.mkdir(parents=True, exist_ok=True)
            example_path = out_dir / "github-usernames.example.json"
            if not example_path.exists():
                example = {
                    "github-username": "Full Name",
                    "another-username": "Another Person"
                }
                with example_path.open('w', encoding='utf-8') as f:
                    json.dump(example, f, ensure_ascii=False, indent=4)
                logging.info(f"Created example mapping file at {example_path} for reference")
        except Exception as e:
            logging.warning(f"Could not create example username mapping file: {e}")

    # Process repositories
    process_repos(repo_entries, headers, args, not_before_d, ms_dates_formatted, username_mappings)

    logging.info("Data gathering complete!")

if __name__ == '__main__':
    main()