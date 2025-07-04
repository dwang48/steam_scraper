#!/usr/bin/env python3
"""
Debug script to examine new Steam app details and filtering
"""
import json
from steam_daily import load_known_appids, fetch_full_applist, fetch_app_details

def debug_new_apps():
    print("=== Debugging New Steam Apps ===")
    
    # Get current state
    known_ids = load_known_appids()
    print(f"Known app count: {len(known_ids)}")
    
    applist = fetch_full_applist()
    latest_ids = {app["appid"] for app in applist}
    new_ids = latest_ids - known_ids
    
    print(f"Total apps in Steam: {len(latest_ids)}")
    print(f"New app_ids detected: {len(new_ids)}")
    
    if not new_ids:
        print("No new apps to debug")
        return
    
    # Examine first few new apps in detail
    sample_ids = list(sorted(new_ids))[:10]  # Look at first 10 new apps
    print(f"\nExamining first {len(sample_ids)} new app_ids:")
    
    for i, app_id in enumerate(sample_ids, 1):
        print(f"\n--- App {i}: ID {app_id} ---")
        details = fetch_app_details(app_id)
        
        if not details:
            print("❌ No details fetched (API error or app not found)")
            continue
            
        name = details.get("name", "Unknown")
        app_type = details.get("type", "Unknown")
        print(f"Name: {name}")
        print(f"Type: {app_type}")
        
        # Check release date info
        release_info = details.get("release_date", {})
        coming_soon = release_info.get("coming_soon", "Not specified")
        date_str = release_info.get("date", "No date")
        
        print(f"Coming soon: {coming_soon}")
        print(f"Release date: {date_str}")
        
        # Show why it might be filtered
        if not release_info.get("coming_soon", False):
            print("🚫 FILTERED: Not marked as 'coming soon'")
        else:
            print("✅ PASSES: Marked as 'coming soon'")
            
        # Show some additional fields
        developers = details.get("developers", [])
        if developers:
            print(f"Developers: {', '.join(developers[:2])}")
            
def main():
    debug_new_apps()

if __name__ == "__main__":
    main() 