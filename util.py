import os
import csv
import sqlite3
import calendar
import argparse
from dotenv import load_dotenv
from discord_bot import send_fan_report

def get_sqlite_db(db_path='backup.db'):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def process_fan_data(month, fan_data_dir='fan_data', db_path='backup.db', include_missing=False):
    """
    Core function computing fan status. Returns (reqs, latest_day, fan_rows).
    """
    reqs = []
    days_in_month = 30
    
    # Ensure dir exists safely
    os.makedirs(fan_data_dir, exist_ok=True)
    
    conn = get_sqlite_db(db_path)
    members_rows = conn.execute('SELECT ingame_id, ingame_name, discord_id FROM members').fetchall()
    exempt_rows = conn.execute('SELECT ingame_id, reason FROM member_exemptions').fetchall()
    exemptions_dict = {row['ingame_id']: row['reason'] for row in exempt_rows}
    
    extras_rows = []
    if month:
        extras_rows = conn.execute('SELECT ingame_id, extra FROM member_extras WHERE month_year = ?', (month,)).fetchall()
        req_rows = conn.execute('SELECT * FROM fan_requirements WHERE month_year = ? ORDER BY day_start', (month,)).fetchall()
        reqs = [dict(row) for row in req_rows]
        
        try:
            year_val = int(month[:4])
            month_val = int(month[4:])
            days_in_month = calendar.monthrange(year_val, month_val)[1]
        except:
            pass

    extras_dict = {row['ingame_id']: row['extra'] for row in extras_rows}
    member_data = {row['ingame_id']: {'name': row['ingame_name'], 'discord_id': row['discord_id']} for row in members_rows}
    conn.close()

    daily_quota_map = {}
    for req in reqs:
        for d in range(req['day_start'], req['day_end'] + 1):
            daily_quota_map[d] = req['daily_fan']

    latest_day = 0
    fan_rows = []

    if month and f"{month}.csv" in os.listdir(fan_data_dir):
        filepath = os.path.join(fan_data_dir, f"{month}.csv")
        with open(filepath, 'r', encoding='utf-8') as csvfile:
            reader = list(csv.reader(csvfile))
            if len(reader) > 1:
                max_cols = 0
                for r in reader[1:]:
                    while r and (r[-1] == "" or r[-1] is None):
                        r.pop()
                    if len(r) > max_cols:
                        max_cols = len(r)
                
                latest_day = max(0, max_cols - 1)
                expected_total = sum(daily_quota_map.get(d, 0) for d in range(1, latest_day + 1))
                current_daily_req = daily_quota_map.get(latest_day, 0)

                raw_rows = []
                for r in reader[1:]:
                    if not r: continue
                    ingame_id = r[0]
                    if not include_missing and ingame_id not in member_data:
                        continue
                        
                    m_data = member_data.get(ingame_id, {'name': ingame_id, 'discord_id': None})
                    name = m_data['name']
                    discord_id = m_data['discord_id']
                    
                    fan_val = 0
                    if len(r) > 1:
                        try:
                            fan_val = int(r[-1])
                        except ValueError:
                            pass
                            
                    raw_rows.append({
                        'ingame_id': ingame_id,
                        'name': name,
                        'discord_id': discord_id,
                        'fan': fan_val,
                        'expected': expected_total,
                        'current_daily_req': current_daily_req,
                        'exempt': exemptions_dict.get(ingame_id)
                    })
                
                raw_rows.sort(key=lambda x: x['fan'], reverse=True)
                
                for row in raw_rows:
                    fan = row['fan']
                    base_expected = row['expected']
                    base_req_day = row['current_daily_req']
                    ingame_id = row['ingame_id']
                    
                    extra = extras_dict.get(ingame_id, 0)
                    
                    if extra > 0:
                        effective_expected = round(base_expected + (extra / float(days_in_month)) * latest_day)
                        effective_req_day = base_req_day + (extra / float(days_in_month))
                    else:
                        effective_expected = max(0, base_expected + extra)
                        effective_req_day = base_req_day
                    
                    deficit = effective_expected - fan
                    status = 'normal'
                    
                    if extra > 0:
                        if base_expected > 0 and (fan - extra) >= base_expected * 2:
                            status = 'great'
                        elif base_expected > 0 and (fan - extra) >= base_expected * 1.5:
                            status = 'good'
                        elif deficit > effective_req_day * 3:
                            status = 'awful'
                        elif 0 < deficit <= effective_req_day * 3:
                            status = 'bad'
                    else:
                        if base_expected > 0 and fan >= base_expected * 2:
                            status = 'great'
                        elif base_expected > 0 and fan >= base_expected * 1.5:
                            status = 'good'
                        elif deficit > effective_req_day * 3:
                            status = 'awful'
                        elif 0 < deficit <= effective_req_day * 3:
                            status = 'bad'
                        
                    fan_rows.append({
                        'ingame_id': row['ingame_id'],
                        'name': row['name'],
                        'discord_id': row['discord_id'],
                        'fan_fmt': f"{fan:,}",
                        'expected_fmt': f"{effective_expected:,}",
                        'status': status,
                        'exempt': row['exempt'],
                        'extra': extra
                    })
                    
    return reqs, latest_day, fan_rows

def get_most_recent_month(fan_data_dir='fan_data'):
    available_months = []
    if os.path.exists(fan_data_dir):
        for f in os.listdir(fan_data_dir):
            if f.endswith('.csv'):
                available_months.append(f.replace('.csv', ''))
    if available_months:
        available_months.sort(reverse=True)
        return available_months[0]
    return None

def main():
    parser = argparse.ArgumentParser(description="Uma Club Manager CLI Utilities")
    subparsers = parser.add_subparsers(dest='command', help='Subcommands')

    # parser report
    report_parser = subparsers.add_parser('report', help='Send fan progress report directly to Discord')
    report_parser.add_argument('-m', '--month', type=str, help='Month string, e.g. 03')
    report_parser.add_argument('-y', '--year', type=str, help='Year string, e.g. 2026')
    report_parser.add_argument('--missing', action='store_true', help='Include IDs that do not have a linked name in the database.')

    args = parser.parse_args()

    if args.command == 'report':
        load_dotenv()
        webhook_url = os.environ.get("DISCORD_WEBHOOK")
        if not webhook_url:
            print("Error: DISCORD_WEBHOOK environment variable is not set in .env")
            return
            
        target_month = None
        if args.year and args.month:
            month_str = str(args.month).zfill(2)
            target_month = f"{args.year}{month_str}"
        elif args.year or args.month:
            print("Error: You must provide BOTH --year and --month if you want to override the default.")
            return
        else:
            target_month = get_most_recent_month()
            if not target_month:
                print("Error: No fan_data CSV files found to report default latest month.")
                return
                
        print(f"Generating and sending report for month: {target_month}...")
        
        reqs, latest_day, fan_rows = process_fan_data(target_month, include_missing=args.missing)
        
        if not fan_rows:
            print("Error: No data rows found for this month.")
            return
            
        send_fan_report(fan_rows, webhook_url)
        print("Done!")

if __name__ == "__main__":
    main()
