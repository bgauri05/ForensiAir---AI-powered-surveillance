import os
import csv
from collections import defaultdict
import psycopg2
from dotenv import load_dotenv

def main():
    # 1. Load backend env to get DATABASE_URL
    dotenv_path = "c:/Users/gauri/OneDrive/Desktop/forensiair/backend/.env"
    load_dotenv(dotenv_path=dotenv_path, override=True)
    database_url = os.getenv("DATABASE_URL")
    
    # Connect to database
    if database_url and not database_url.endswith('/forensiair') and '/' in database_url:
        forensiair_url = database_url.rsplit('/', 1)[0] + '/forensiair'
    else:
        forensiair_url = database_url
    print("Connecting to database:", forensiair_url)
    
    conn = psycopg2.connect(forensiair_url)
    cur = conn.cursor()
    
    # 2. Get list of all factories
    cur.execute("SELECT site_id, name FROM factories ORDER BY site_id;")
    factories = cur.fetchall()
    print(f"Retrieved {len(factories)} factories to process.")
    
    # Create output directory
    output_dir = "c:/Users/gauri/OneDrive/Desktop/mpcb_scraper/clean_factory_data"
    os.makedirs(output_dir, exist_ok=True)
    print("Output directory created:", output_dir)
    
    # 3. For each factory, query and pivot data
    for site_id, name in factories:
        print(f"Processing factory: {site_id} - {name}...")
        
        # Query parameters and values ordered by timestamp
        cur.execute("""
            SELECT timestamp, parameter_id, value 
            FROM monitoring_data 
            WHERE factory_id = %s 
            ORDER BY timestamp, parameter_id;
        """, (site_id,))
        rows = cur.fetchall()
        
        if not rows:
            print(f"  No data records found for {site_id} - skipping CSV generation.")
            continue
            
        # Pivot the data
        # structure: pivoted[timestamp_str][parameter_id] = value
        pivoted = defaultdict(dict)
        parameters = set()
        
        for ts, param, val in rows:
            ts_str = ts.strftime('%Y-%m-%d %H:%M')
            pivoted[ts_str][param] = float(val)
            parameters.add(param)
            
        sorted_params = sorted(list(parameters))
        
        # Write to pivoted CSV file
        csv_file = os.path.join(output_dir, f"{site_id}.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Header: Time, Parameter 1, Parameter 2...
            writer.writerow(['Time'] + sorted_params)
            
            # Rows sorted by timestamp
            for ts_str in sorted(list(pivoted.keys())):
                row = [ts_str]
                for param in sorted_params:
                    # Write blank cell if parameter data is not available at this timestep
                    row.append(pivoted[ts_str].get(param, ''))
                writer.writerow(row)
                
        print(f"  Saved {len(pivoted)} rows to {csv_file}")
        
    print("\nData export and pivoting complete!")
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
