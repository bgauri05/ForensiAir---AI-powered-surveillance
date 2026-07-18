import time
import asyncio
from datetime import datetime
from logger import logger
import database
import scraper

async def main_async():
    start_time = time.time()
    logger.info("Starting Inspection Schedule Collector module...")
    
    # 1. Initialize Database
    try:
        database.init_db()
    except Exception as e:
        logger.critical(f"Failed to initialize database. Aborting collection run: {e}")
        return
        
    # 2. Run Scraper Pipeline
    scraped_records, chunks_scraped, errors = await scraper.run_scraper_pipeline()
    
    # 3. Store Records in PostgreSQL
    new_records_inserted = 0
    duplicate_skipped = 0
    
    if scraped_records:
        logger.info(f"Saving {len(scraped_records)} scraped records to the database...")
        try:
            new_records_inserted, duplicate_skipped = database.save_inspection_records(scraped_records)
            logger.info(f"Saved records successfully: {new_records_inserted} inserted, {duplicate_skipped} duplicates skipped.")
        except Exception as e:
            err_msg = f"Database save failed: {e}"
            errors.append(err_msg)
            logger.error(err_msg)
    else:
        logger.warning("No records scraped during this run.")
        
    # 4. Finalize Statistics and Log Run
    elapsed_time = time.time() - start_time
    status = "SUCCESS" if chunks_scraped > 0 and not errors else "FAILURE"
    error_summary = "; ".join(errors) if errors else None
    
    log_entry = {
        "total_pages_scraped": chunks_scraped,
        "total_records_scraped": len(scraped_records),
        "new_records_inserted": new_records_inserted,
        "duplicate_records_skipped": duplicate_skipped,
        "execution_time": round(elapsed_time, 2),
        "status": status,
        "error_message": error_summary
    }
    
    database.save_download_log(log_entry)
    
    # 5. Print Requested Final Summary Output
    print("\n" + "=" * 50)
    print("Inspection Schedule Collector Completed")
    print(f"Pages Scraped: {chunks_scraped}")
    print(f"Records Found: {len(scraped_records)}")
    print(f"New Records Inserted: {new_records_inserted}")
    print(f"Duplicates Skipped: {duplicate_skipped}")
    print(f"Execution Time: {elapsed_time:.2f} seconds")
    print(f"Status: {status}")
    if error_summary:
        print(f"Errors encountered: {error_summary}")
    print("=" * 50 + "\n")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
