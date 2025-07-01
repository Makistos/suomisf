#!/usr/bin/env python3
"""
API Documentation Generator for SuomiSF
This script analyzes the API route files and generates documentation.
"""

import os
import re
import json
from typing import Dict, List, Any
from pathlib import Path


def extract_routes_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Extract route information from a Python file."""
    routes = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all @app.route decorators
    route_pattern = (r"@app\.route\s*\(\s*['\"]([^'\"]+)['\"]"
                     r"(?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?\s*\)")
    function_pattern = r"def\s+(\w+)\s*\([^)]*\)\s*->\s*[^:]*:"

    lines = content.split('\n')

    for i, line in enumerate(lines):
        route_match = re.search(route_pattern, line)
        if route_match:
            path = route_match.group(1)
            methods_str = route_match.group(2)
            methods = []

            if methods_str:
                # Extract method names from the list
                method_matches = re.findall(r"['\"](\w+)['\"]", methods_str)
                methods = [m.upper() for m in method_matches]
            else:
                methods = ['GET']  # Default method

            # Find the function name on the next few lines
            function_name = None
            for j in range(i + 1, min(i + 5, len(lines))):
                func_match = re.search(function_pattern, lines[j])
                if func_match:
                    function_name = func_match.group(1)
                    break

            # Extract docstring if available
            docstring = ""
            if function_name:
                func_start = None
                for j in range(i + 1, len(lines)):
                    if f"def {function_name}" in lines[j]:
                        func_start = j
                        break

                if func_start:
                    # Look for docstring in the next few lines
                    max_line = min(func_start + 20, len(lines))
                    for j in range(func_start + 1, max_line):
                        line_stripped = lines[j].strip()
                        starts_triple = (line_stripped.startswith('"""') or
                                         line_stripped.startswith("'''"))
                        if starts_triple:
                            # Found docstring start
                            doc_lines = [line_stripped]
                            for k in range(j + 1, len(lines)):
                                doc_lines.append(lines[k])
                                if '"""' in lines[k] or "'''" in lines[k]:
                                    break
                            docstring = '\n'.join(doc_lines)
                            break

            routes.append({
                'path': path,
                'methods': methods,
                'function': function_name,
                'docstring': docstring,
                'file': os.path.basename(file_path)
            })

    return routes


def generate_documentation():
    """Generate API documentation from all api_ files."""

    # Find all api_ files
    api_files = []
    app_dir = Path('./app')

    if app_dir.exists():
        for file_path in app_dir.glob('api_*.py'):
            api_files.append(str(file_path))

    # Also check the main api.py file
    main_api_path = app_dir / 'api.py'
    if main_api_path.exists():
        api_files.append(str(main_api_path))

    all_routes = []

    # Extract routes from each file
    for file_path in sorted(api_files):
        print(f"Processing {file_path}...")
        routes = extract_routes_from_file(file_path)
        all_routes.extend(routes)

    # Group routes by category
    categorized_routes = {}

    for route in all_routes:
        # Determine category from path
        path_parts = route['path'].split('/')
        if len(path_parts) >= 3 and path_parts[1] == 'api':
            # Take first part after /api/
            category = path_parts[2].split('/')[0]
            category = category.split('<')[0]  # Remove parameter parts

            if category not in categorized_routes:
                categorized_routes[category] = []
            categorized_routes[category].append(route)
        else:
            # Fallback category
            if 'misc' not in categorized_routes:
                categorized_routes['misc'] = []
            categorized_routes['misc'].append(route)

    # Generate markdown documentation
    markdown_content = []
    markdown_content.append("# SuomiSF API Routes Documentation")
    markdown_content.append("")
    markdown_content.append("Auto-generated documentation from API routes.")
    markdown_content.append("")
    markdown_content.append("## Table of Contents")
    markdown_content.append("")

    # Add table of contents
    for category in sorted(categorized_routes.keys()):
        markdown_content.append(f"- [{category.title()}](#{category.lower()})")

    markdown_content.append("")

    # Add detailed documentation for each category
    for category in sorted(categorized_routes.keys()):
        markdown_content.append(f"## {category.title()}")
        markdown_content.append("")

        routes = categorized_routes[category]
        for route in sorted(routes, key=lambda x: x['path']):
            methods_str = ' '.join(route['methods'])
            markdown_content.append(f"### {methods_str} {route['path']}")
            markdown_content.append("")

            if route['function']:
                markdown_content.append(f"**Function:** `{route['function']}`")
                markdown_content.append("")

            markdown_content.append(f"**File:** `{route['file']}`")
            markdown_content.append("")

            if route['docstring']:
                markdown_content.append("**Description:**")
                # Clean up docstring
                docstring_clean = route['docstring'].replace('"""', '')
                docstring_clean = docstring_clean.replace("'''", "")
                docstring = docstring_clean.strip()
                if docstring:
                    markdown_content.append("```")
                    markdown_content.append(docstring)
                    markdown_content.append("```")
                markdown_content.append("")

            markdown_content.append("---")
            markdown_content.append("")

    # Write documentation to file
    with open('API_ROUTES_GENERATED.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(markdown_content))

    route_count = len(all_routes)
    file_count = len(api_files)
    print(f"Documentation generated! Found {route_count} routes in "
          f"{file_count} files.")
    print(f"Categories: {', '.join(sorted(categorized_routes.keys()))}")

    # Also generate a JSON summary
    categories_dict = {}
    for category, routes in categorized_routes.items():
        categories_dict[category] = len(routes)

    summary = {
        'total_routes': len(all_routes),
        'files_processed': len(api_files),
        'categories': categories_dict,
        'routes': all_routes
    }

    with open('api_routes_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return all_routes, categorized_routes


if __name__ == '__main__':
    generate_documentation()
