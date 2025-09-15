#!/usr/bin/env python3
"""
JSON to CSV/XLSX Converter for gather-commits-issues-prs repository data

This script takes JSON files from the commits-issues-prs directory and converts them
to CSV or XLSX format for easier readability and analysis.
"""

import json
import os
import pandas as pd
import argparse
from datetime import datetime
from pathlib import Path

def flatten_commits(data):
    """
    Flatten the commits data from the JSON structure
    """
    commits_data = []
    
    for entry in data:
        date_snapshot = entry.get('date', '')
        commits_dict = entry.get('commits', {})
        
        for username, user_commits in commits_dict.items():
            for commit in user_commits.get('list', []):
                flat_commit = {
                    'snapshot_date': date_snapshot,
                    'username': username,
                    'author_full_name': user_commits.get('full_name', ''),
                    'message': commit.get('message', ''),
                    'date': commit.get('date', ''),
                    'link': commit.get('link', ''),
                    'files_changed': commit.get('diff', {}).get('files', 0),
                    'total_changes': commit.get('diff', {}).get('total', 0)
                }
                commits_data.append(flat_commit)
    
    return commits_data

def flatten_issues(data):
    """
    Flatten the issues data from the JSON structure
    """
    issues_data = []
    
    for entry in data:
        date_snapshot = entry.get('date', '')
        issues_dict = entry.get('issues', {})
        
        for username, user_issues in issues_dict.items():
            for issue in user_issues.get('list', []):
                flat_issue = {
                    'snapshot_date': date_snapshot,
                    'username': username,
                    'author_full_name': user_issues.get('full_name', ''),
                    'title': issue.get('title', ''),
                    'description': issue.get('desc', ''),
                    'date': issue.get('date', ''),
                    'state': issue.get('state', ''),
                    'link': issue.get('link', ''),
                    'labels': ', '.join(issue.get('labels', [])),
                    'assignees': ', '.join(issue.get('assignees', [])),
                    'assignee_full_names': ', '.join(issue.get('assignee_full_names', [])),
                    'comment_count': len(issue.get('comments', []))
                }
                issues_data.append(flat_issue)
    
    return issues_data

def flatten_prs(data):
    """
    Flatten the pull requests data from the JSON structure
    """
    prs_data = []
    
    for entry in data:
        date_snapshot = entry.get('date', '')
        prs_dict = entry.get('prs', {})
        
        for username, user_prs in prs_dict.items():
            for pr in user_prs.get('list', []):
                flat_pr = {
                    'snapshot_date': date_snapshot,
                    'username': username,
                    'author_full_name': user_prs.get('full_name', ''),
                    'title': pr.get('title', ''),
                    'description': pr.get('desc', ''),
                    'date': pr.get('date', ''),
                    'state': pr.get('state', ''),
                    'link': pr.get('link', ''),
                    'labels': ', '.join(pr.get('labels', [])),
                    'assignees': ', '.join(pr.get('assignees', [])),
                    'assignee_full_names': ', '.join(pr.get('assignee_full_names', [])),
                    'files_changed': pr.get('diff', {}).get('files', 0),
                    'total_changes': pr.get('diff', {}).get('total', 0),
                    'comment_count': len(pr.get('comments', []))
                }
                prs_data.append(flat_pr)
    
    return prs_data

def process_file(json_file_path, output_dir, output_format):
    """
    Process a single JSON file and convert to CSV/XLSX
    """
    try:
        # Extract repo name from filename
        repo_name = Path(json_file_path).stem
        print(f"Processing {repo_name}...")
        
        # Load JSON data
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Get flattened data
        commits_data = flatten_commits(data)
        issues_data = flatten_issues(data)
        prs_data = flatten_prs(data)
        
        # Convert to DataFrames
        commits_df = pd.DataFrame(commits_data)
        issues_df = pd.DataFrame(issues_data)
        prs_df = pd.DataFrame(prs_data)
        
        # Save to CSV or XLSX
        if output_format == 'csv':
            commits_df.to_csv(f"{output_dir}/{repo_name}_commits.csv", index=False)
            issues_df.to_csv(f"{output_dir}/{repo_name}_issues.csv", index=False)
            prs_df.to_csv(f"{output_dir}/{repo_name}_prs.csv", index=False)
            print(f"CSV files saved to {output_dir}/{repo_name}_*.csv")
        else:
            # Create Excel writer with multiple sheets
            with pd.ExcelWriter(f"{output_dir}/{repo_name}.xlsx", engine='openpyxl') as writer:
                commits_df.to_excel(writer, sheet_name='Commits', index=False)
                issues_df.to_excel(writer, sheet_name='Issues', index=False)
                prs_df.to_excel(writer, sheet_name='Pull Requests', index=False)
            print(f"Excel file saved to {output_dir}/{repo_name}.xlsx")
            
        return len(commits_data), len(issues_data), len(prs_data)
        
    except Exception as e:
        print(f"Error processing {json_file_path}: {e}")
        return 0, 0, 0

def process_directory(json_dir, output_dir, output_format='xlsx', specific_file=None):
    """
    Process all JSON files in a directory
    """
    total_commits = 0
    total_issues = 0
    total_prs = 0
    
    # Get list of JSON files to process
    if specific_file:
        if Path(specific_file).exists():
            json_files = [specific_file]
        else:
            file_path = os.path.join(json_dir, specific_file)
            if Path(file_path).exists():
                json_files = [file_path]
            else:
                print(f"File not found: {specific_file}")
                return
    else:
        json_files = [os.path.join(json_dir, f) for f in os.listdir(json_dir) if f.endswith('.json')]
    
    # Process each file
    for json_file in json_files:
        commits, issues, prs = process_file(json_file, output_dir, output_format)
        total_commits += commits
        total_issues += issues
        total_prs += prs
    
    print(f"\nConversion complete!")
    print(f"Total commits processed: {total_commits}")
    print(f"Total issues processed: {total_issues}")
    print(f"Total PRs processed: {total_prs}")

def main():
    parser = argparse.ArgumentParser(description='Convert JSON data to CSV/XLSX format')
    parser.add_argument('--input', '-i', default='./commits-issues-prs', 
                        help='Input directory containing JSON files (default: ./commits-issues-prs)')
    parser.add_argument('--output', '-o', default='./csv_output',
                        help='Output directory for CSV/XLSX files (default: ./csv_output)')
    parser.add_argument('--format', '-f', choices=['csv', 'xlsx'], default='xlsx',
                        help='Output format (csv or xlsx, default: xlsx)')
    parser.add_argument('--file', help='Process specific file instead of entire directory')
    
    args = parser.parse_args()
    
    process_directory(args.input, args.output, args.format, args.file)

if __name__ == "__main__":
    main()
