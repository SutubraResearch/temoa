#!/usr/bin/env python3
"""
strip_region_prefixes.py

Strips region prefixes from all technology names in a Temoa v4 SQLite database.
E.g.:
  TRE_onshore_wind_turbine_1 → onshore_wind_turbine_1
  water_import_TRE_conventional_hydroelectric_1 → water_import_conventional_hydroelectric_1

Usage:
  python strip_region_prefixes.py <input.sqlite> <output.sqlite>

Or to modify in-place:
  python strip_region_prefixes.py <input.sqlite>
"""

import shutil
import sqlite3
import sys
from pathlib import Path


def get_regions(conn):
    """Get all region names from the database."""
    cur = conn.execute('SELECT region FROM region ORDER BY LENGTH(region) DESC')
    return [row[0] for row in cur.fetchall()]


def build_tech_mapping(conn, regions):
    """Build old_tech -> new_tech mapping by stripping region prefixes."""
    cur = conn.execute('SELECT tech FROM technology ORDER BY tech')
    all_techs = [row[0] for row in cur.fetchall()]

    mapping = {}
    # Sort regions longest-first so TREW matches before TRE
    sorted_regions = sorted(regions, key=len, reverse=True)

    for tech in all_techs:
        new_name = tech

        # Check prefix: REGION_techname
        matched = False
        for r in sorted_regions:
            prefix = r + '_'
            if tech.startswith(prefix):
                new_name = tech[len(prefix) :]
                matched = True
                break

        # Check embedded region: something_REGION_something (water_import case)
        if not matched:
            for r in sorted_regions:
                pattern = '_' + r + '_'
                if pattern in tech:
                    new_name = tech.replace(pattern, '_', 1)
                    matched = True
                    break

        if new_name != tech:
            mapping[tech] = new_name

    return mapping


def get_tables_with_tech_columns(conn):
    """Find all tables that have tech-related columns."""
    cur = conn.execute("""
        SELECT m.name as table_name, p.name as col_name
        FROM sqlite_master m
        JOIN pragma_table_info(m.name) p
        WHERE m.type = 'table'
        AND (p.name = 'tech' OR p.name = 'tech_or_group'
             OR p.name = 'primary_tech' OR p.name = 'driven_tech'
             OR p.name = 'tech_group')
        ORDER BY m.name, p.name
    """)
    return cur.fetchall()


def apply_mapping(conn, mapping):
    """Apply the tech name mapping to all relevant tables using bulk updates."""
    tables_cols = get_tables_with_tech_columns(conn)

    # Group by table
    table_columns = {}
    for table, col in tables_cols:
        if table not in table_columns:
            table_columns[table] = []
        table_columns[table].append(col)

    print(f'\nApplying mapping to {len(table_columns)} tables...')

    # Create temp mapping table for bulk JOIN updates (much faster than row-by-row)
    conn.execute(
        'CREATE TEMP TABLE IF NOT EXISTS tech_mapping (old_tech TEXT PRIMARY KEY, new_tech TEXT)'
    )
    conn.execute('DELETE FROM tech_mapping')
    conn.executemany('INSERT INTO tech_mapping VALUES (?, ?)', mapping.items())

    # First: handle the technology table specially (need to dedup)
    if 'technology' in table_columns:
        print('\n--- technology table (dedup required) ---')
        dedup_technology_table(conn, mapping)
        del table_columns['technology']

    # Second: handle tech_group_member specially (can have duplicates after rename)
    if 'tech_group_member' in table_columns:
        print('\n--- tech_group_member table (dedup required) ---')
        dedup_tech_group_member(conn, mapping)
        del table_columns['tech_group_member']

    # Then: bulk update all other tables (single UPDATE per column)
    for table, cols in sorted(table_columns.items()):
        for col in cols:
            cur = conn.execute(f'SELECT COUNT(*) FROM [{table}]')
            if cur.fetchone()[0] == 0:
                print(f'  {table}.{col}: empty, skipping')
                continue

            cur = conn.execute(f"""
                UPDATE [{table}] SET [{col}] = (
                    SELECT new_tech FROM tech_mapping WHERE old_tech = [{table}].[{col}]
                ) WHERE [{col}] IN (SELECT old_tech FROM tech_mapping)
            """)
            updated = cur.rowcount
            print(f'  {table}.{col}: {updated} rows updated')

    conn.commit()


def dedup_technology_table(conn, mapping):
    """Handle the technology table: rename techs and remove duplicates."""
    # Get all current techs with their data
    cur = conn.execute('SELECT * FROM technology ORDER BY tech')
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]

    # Build new rows with stripped names
    seen = {}
    to_delete = []
    to_update = []

    for row in rows:
        row_dict = dict(zip(col_names, row))
        old_tech = row_dict['tech']
        new_tech = mapping.get(old_tech, old_tech)

        if new_tech in seen:
            # Duplicate - mark for deletion
            to_delete.append(old_tech)
        else:
            seen[new_tech] = old_tech
            if old_tech != new_tech:
                to_update.append((old_tech, new_tech))

    print(f'  Unique techs before: {len(rows)}')
    print(f'  Unique techs after: {len(seen)}')
    print(f'  Techs to rename: {len(to_update)}')
    print(f'  Duplicate techs to delete: {len(to_delete)}')

    # Delete duplicates first
    for old_tech in to_delete:
        conn.execute('DELETE FROM technology WHERE tech = ?', (old_tech,))

    # Then rename remaining
    for old_tech, new_tech in to_update:
        conn.execute('UPDATE technology SET tech = ? WHERE tech = ?', (new_tech, old_tech))

    conn.commit()


def dedup_tech_group_member(conn, mapping):
    """Handle tech_group_member table: rename techs and remove duplicates.

    PK is (group_name, tech), so after stripping prefixes we may have duplicates
    like (ESR_8, TRE_wind) and (ESR_8, TREW_wind) both mapping to (ESR_8, wind).
    """
    cur = conn.execute('SELECT group_name, tech FROM tech_group_member ORDER BY group_name, tech')
    rows = cur.fetchall()

    if not rows:
        print('  Empty table, skipping')
        return

    # Build new rows with stripped names
    seen = set()
    to_delete = []
    to_update = []

    for group_name, old_tech in rows:
        new_tech = mapping.get(old_tech, old_tech)
        key = (group_name, new_tech)

        if key in seen:
            # Duplicate - mark for deletion
            to_delete.append((group_name, old_tech))
        else:
            seen.add(key)
            if old_tech != new_tech:
                to_update.append((group_name, old_tech, new_tech))

    print(f'  Unique memberships before: {len(rows)}')
    print(f'  Unique memberships after: {len(seen)}')
    print(f'  Memberships to rename: {len(to_update)}')
    print(f'  Duplicate memberships to delete: {len(to_delete)}')

    # Delete duplicates first
    for group_name, old_tech in to_delete:
        conn.execute(
            'DELETE FROM tech_group_member WHERE group_name = ? AND tech = ?',
            (group_name, old_tech),
        )

    # Then rename remaining
    for group_name, old_tech, new_tech in to_update:
        conn.execute(
            'UPDATE tech_group_member SET tech = ? WHERE group_name = ? AND tech = ?',
            (new_tech, group_name, old_tech),
        )

    conn.commit()


def verify_no_pk_violations(conn):
    """Quick check that no primary key violations exist after renaming."""
    print('\n--- Verifying no PK violations ---')

    # Check technology table
    cur = conn.execute("""
        SELECT tech, COUNT(*) as cnt FROM technology
        GROUP BY tech HAVING cnt > 1
    """)
    dupes = cur.fetchall()
    if dupes:
        print(f'  ERROR: {len(dupes)} duplicate techs in technology table!')
        for d in dupes:
            print(f'    {d[0]}: {d[1]} entries')
        return False
    else:
        print('  technology: OK (no duplicates)')

    # Check a few key tables for PK violations
    key_tables = [
        ('efficiency', 'region, input_comm, tech, vintage, output_comm'),
        ('existing_capacity', 'region, tech, vintage'),
        ('capacity_to_activity', 'region, tech'),
        ('cost_variable', 'region, period, tech, vintage'),
        ('tech_group_member', 'group_name, tech'),
    ]
    for table, pk_cols in key_tables:
        cur = conn.execute(f"""
            SELECT {pk_cols}, COUNT(*) as cnt
            FROM [{table}]
            GROUP BY {pk_cols}
            HAVING cnt > 1
        """)
        dupes = cur.fetchall()
        if dupes:
            print(f'  ERROR: {len(dupes)} PK violations in {table}!')
            return False
        else:
            print(f'  {table}: OK')

    return True


def print_summary(conn, mapping):
    """Print summary of changes."""
    print('\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)

    cur = conn.execute('SELECT COUNT(*) FROM technology')
    print(f'  Technologies: {cur.fetchone()[0]}')

    cur = conn.execute('SELECT tech FROM technology ORDER BY tech')
    techs = [row[0] for row in cur.fetchall()]
    print('\n  Sample tech names (first 15):')
    for t in techs[:15]:
        print(f'    {t}')
    print(f'    ... ({len(techs)} total)')

    print(f'\n  Mapping applied ({len(mapping)} renames):')
    for old, new in sorted(mapping.items())[:10]:
        print(f'    {old} → {new}')
    if len(mapping) > 10:
        print(f'    ... ({len(mapping)} total)')


def main():
    if len(sys.argv) < 2:
        print('Usage: python strip_region_prefixes.py <input.sqlite> [output.sqlite]')
        sys.exit(1)

    input_db = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        output_db = Path(sys.argv[2])
        print(f'Copying {input_db} → {output_db}')
        shutil.copy2(input_db, output_db)
        db_path = output_db
    else:
        db_path = input_db
        print(f'Modifying in-place: {db_path}')

    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = OFF')  # Disable FK checks during rename

    # Step 1: Get regions
    regions = get_regions(conn)
    print(f'Regions found: {regions}')

    # Step 2: Build mapping
    mapping = build_tech_mapping(conn, regions)
    print(f'\nTech name mapping ({len(mapping)} renames):')
    for old, new in sorted(mapping.items())[:10]:
        print(f'  {old} → {new}')
    if len(mapping) > 10:
        print(f'  ... ({len(mapping)} total)')

    # Step 3: Apply mapping
    apply_mapping(conn, mapping)

    # Step 4: Verify
    ok = verify_no_pk_violations(conn)

    # Step 5: Summary
    print_summary(conn, mapping)

    conn.close()

    if ok:
        print(f'\n✓ Successfully stripped region prefixes from {db_path}')
    else:
        print('\n✗ ERRORS found - check output above')
        sys.exit(1)


if __name__ == '__main__':
    main()
