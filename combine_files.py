#!/usr/bin/env python3
"""
Combine all group CSV/XLSX files into consolidated files

This script takes the individual CSV/XLSX files for each repository
and combines them into consolidated files for easier comparison.
"""

import os
import pandas as pd
import argparse
from pathlib import Path

def combine_csv_files(input_dir, output_dir):
    """
    Combine all CSV files of the same type into consolidated files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all CSV files and group them by type
    all_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
    commit_files = [f for f in all_files if 'commits' in f]
    issue_files = [f for f in all_files if 'issues' in f]
    pr_files = [f for f in all_files if 'prs' in f]
    
    # Combine commit files
    print(f"Combining {len(commit_files)} commit CSV files...")
    commit_dfs = []
    for file in commit_files:
        df = pd.read_csv(os.path.join(input_dir, file))
        # Add repository name as a column
        repo_name = file.split('_commits')[0]
        df['repo'] = repo_name
        commit_dfs.append(df)
    
    if commit_dfs:
        combined_commits = pd.concat(commit_dfs, ignore_index=True)
        combined_commits.to_csv(os.path.join(output_dir, 'all_commits.csv'), index=False)
        print(f"Created combined commits file with {len(combined_commits)} entries")
    
    # Combine issue files
    print(f"Combining {len(issue_files)} issue CSV files...")
    issue_dfs = []
    for file in issue_files:
        df = pd.read_csv(os.path.join(input_dir, file))
        # Add repository name as a column
        repo_name = file.split('_issues')[0]
        df['repo'] = repo_name
        issue_dfs.append(df)
    
    if issue_dfs:
        combined_issues = pd.concat(issue_dfs, ignore_index=True)
        combined_issues.to_csv(os.path.join(output_dir, 'all_issues.csv'), index=False)
        print(f"Created combined issues file with {len(combined_issues)} entries")
    
    # Combine PR files
    print(f"Combining {len(pr_files)} PR CSV files...")
    pr_dfs = []
    for file in pr_files:
        df = pd.read_csv(os.path.join(input_dir, file))
        # Add repository name as a column
        repo_name = file.split('_prs')[0]
        df['repo'] = repo_name
        pr_dfs.append(df)
    
    if pr_dfs:
        combined_prs = pd.concat(pr_dfs, ignore_index=True)
        combined_prs.to_csv(os.path.join(output_dir, 'all_prs.csv'), index=False)
        print(f"Created combined PRs file with {len(combined_prs)} entries")

def combine_excel_files(input_dir, output_dir):
    """
    Combine all Excel files into a consolidated file with multiple sheets
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all Excel files
    excel_files = [f for f in os.listdir(input_dir) if f.endswith('.xlsx')]
    print(f"Combining {len(excel_files)} Excel files...")
    
    # Initialize dataframes for combined data
    all_commits = []
    all_issues = []
    all_prs = []
    
    # Read each Excel file and extract data from each sheet
    for file in excel_files:
        file_path = os.path.join(input_dir, file)
        repo_name = file.split('.xlsx')[0]
        
        # Read each sheet
        commits_df = pd.read_excel(file_path, sheet_name='Commits')
        issues_df = pd.read_excel(file_path, sheet_name='Issues')
        prs_df = pd.read_excel(file_path, sheet_name='Pull Requests')
        
        # Add repository name as a column
        commits_df['repo'] = repo_name
        issues_df['repo'] = repo_name
        prs_df['repo'] = repo_name
        
        # Append to lists
        all_commits.append(commits_df)
        all_issues.append(issues_df)
        all_prs.append(prs_df)
    
    # Combine data
    if all_commits:
        combined_commits = pd.concat(all_commits, ignore_index=True)
        combined_issues = pd.concat(all_issues, ignore_index=True)
        combined_prs = pd.concat(all_prs, ignore_index=True)
        
        # Create combined Excel file with multiple sheets
        with pd.ExcelWriter(os.path.join(output_dir, 'all_repositories.xlsx'), engine='openpyxl') as writer:
            combined_commits.to_excel(writer, sheet_name='All Commits', index=False)
            combined_issues.to_excel(writer, sheet_name='All Issues', index=False)
            combined_prs.to_excel(writer, sheet_name='All Pull Requests', index=False)
        
        print(f"Created combined Excel file with:")
        print(f"  - {len(combined_commits)} commit entries")
        print(f"  - {len(combined_issues)} issue entries")
        print(f"  - {len(combined_prs)} PR entries")

def main():
    parser = argparse.ArgumentParser(description='Combine CSV/XLSX files into consolidated files')
    parser.add_argument('--csv-input', default='./csv_output',
                        help='Input directory containing CSV files (default: ./csv_output)')
    parser.add_argument('--csv-output', default='./consolidated_csv',
                        help='Output directory for consolidated CSV files (default: ./consolidated_csv)')
    parser.add_argument('--xlsx-input', default='./xlsx_output',
                        help='Input directory containing XLSX files (default: ./xlsx_output)')
    parser.add_argument('--xlsx-output', default='./consolidated_xlsx',
                        help='Output directory for consolidated XLSX file (default: ./consolidated_xlsx)')
    
    args = parser.parse_args()
    
    # Combine CSV files if the directory exists
    if os.path.exists(args.csv_input):
        combine_csv_files(args.csv_input, args.csv_output)
    else:
        print(f"CSV input directory {args.csv_input} not found.")
    
    # Combine Excel files if the directory exists
    if os.path.exists(args.xlsx_input):
        combine_excel_files(args.xlsx_input, args.xlsx_output)
    else:
        print(f"Excel input directory {args.xlsx_input} not found.")

if __name__ == "__main__":
    main()
