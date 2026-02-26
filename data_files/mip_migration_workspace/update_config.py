#!/usr/bin/env python3
"""
Update the Temoa config_sample file for a specific SQLite database.
Usage: python3 update_config.py <filename.sqlite>
"""

import sys


def update_config(filename):
    """Update config_sample with the specified filename."""

    config_path = 'temoa_model/config_sample'
    group_dir = '/trace/group/adams/cwade2/MIP/Dec2025'

    # Read the current config
    with open(config_path) as f:
        lines = f.readlines()

    # Update the relevant lines
    updated_lines = []
    for line in lines:
        if line.strip().startswith('--input='):
            updated_lines.append(f'--input=data_files/{filename}\n')
        elif line.strip().startswith('--output='):
            updated_lines.append(f'--output={group_dir}/{filename}\n')
        else:
            updated_lines.append(line)

    # Write back to the config file
    with open(config_path, 'w') as f:
        f.writelines(updated_lines)

    print(f'Config updated for: {filename}')
    print(f'  Input:  data_files/{filename}')
    print(f'  Output: {group_dir}/{filename}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 update_config.py <filename.sqlite>')
        sys.exit(1)

    filename = sys.argv[1]

    if not filename.endswith('.sqlite'):
        print('Error: Filename must end with .sqlite')
        sys.exit(1)

    update_config(filename)
