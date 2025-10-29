import sqlite3
import os

# Check if database exists and has data
db_path = 'C:/Users/user/Downloads/IT management/instance/site.db'
if os.path.exists(db_path):
    print(f'Database found at: {db_path}')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f'Tables in database: {[table[0] for table in tables]}')

    # Check asset data
    try:
        cursor.execute('SELECT COUNT(*) FROM asset')
        asset_count = cursor.fetchone()[0]
        print(f'Assets in database: {asset_count}')

        if asset_count > 0:
            cursor.execute('SELECT asset_type, COUNT(*) FROM asset GROUP BY asset_type')
            asset_types = cursor.fetchall()
            print(f'Asset types: {asset_types}')
    except Exception as e:
        print(f'Asset table error: {e}')

    # Check maintenance data
    try:
        cursor.execute('SELECT COUNT(*) FROM maintenance')
        maintenance_count = cursor.fetchone()[0]
        print(f'Maintenance records: {maintenance_count}')

        if maintenance_count > 0:
            cursor.execute('SELECT SUM(cost) FROM maintenance WHERE cost IS NOT NULL')
            total_cost = cursor.fetchone()[0]
            print(f'Total maintenance cost: {total_cost or 0}')
    except Exception as e:
        print(f'Maintenance table error: {e}')

    conn.close()
else:
    print('Database file not found!')
