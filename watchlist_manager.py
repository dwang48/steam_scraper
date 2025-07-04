#!/usr/bin/env python3
"""
Watchlist Manager - View and manage early-stage Steam apps
"""
import json
import argparse
from pathlib import Path
from datetime import datetime
from steam_daily import load_watchlist, save_watchlist, WATCHLIST_FILE

def show_stats():
    """Show watchlist statistics"""
    watchlist = load_watchlist()
    
    if not watchlist:
        print("📝 Watchlist is empty")
        return
    
    total_apps = len(watchlist)
    
    # Count by status
    status_counts = {}
    check_counts = {}
    ages = []
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    for app_id, entry in watchlist.items():
        status = entry.get("current_status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        
        check_count = entry.get("check_count", 0)
        check_counts[check_count] = check_counts.get(check_count, 0) + 1
        
        first_detected = entry.get("first_detected", current_date)
        try:
            first_date = datetime.strptime(first_detected, "%Y-%m-%d")
            current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
            age_days = (current_date_obj - first_date).days
            ages.append(age_days)
        except:
            ages.append(0)
    
    print(f"📊 Watchlist Statistics")
    print(f"Total apps: {total_apps}")
    print(f"Average age: {sum(ages) / len(ages):.1f} days" if ages else "N/A")
    
    print(f"\n📈 Status Breakdown:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    
    print(f"\n🔍 Check Frequency:")
    for checks, count in sorted(check_counts.items()):
        print(f"  {checks} checks: {count} apps")

def list_apps(limit=None, status_filter=None, sort_by="age"):
    """List watchlist apps with optional filtering"""
    watchlist = load_watchlist()
    
    if not watchlist:
        print("📝 Watchlist is empty")
        return
    
    apps = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    for app_id, entry in watchlist.items():
        if status_filter and entry.get("current_status") != status_filter:
            continue
            
        first_detected = entry.get("first_detected", current_date)
        try:
            first_date = datetime.strptime(first_detected, "%Y-%m-%d")
            current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
            age_days = (current_date_obj - first_date).days
        except:
            age_days = 0
        
        apps.append({
            "app_id": app_id,
            "age_days": age_days,
            "check_count": entry.get("check_count", 0),
            "status": entry.get("current_status", "unknown"),
            "name": entry.get("latest_name", f"App {app_id}"),
            "first_detected": first_detected,
            "last_checked": entry.get("last_checked", "unknown")
        })
    
    # Sort apps
    if sort_by == "age":
        apps.sort(key=lambda x: x["age_days"], reverse=True)
    elif sort_by == "checks":
        apps.sort(key=lambda x: x["check_count"], reverse=True)
    elif sort_by == "id":
        apps.sort(key=lambda x: int(x["app_id"]))
    
    # Apply limit
    if limit:
        apps = apps[:limit]
    
    print(f"📋 Watchlist Apps (showing {len(apps)} apps)")
    print(f"{'App ID':<10} {'Name':<30} {'Age':<6} {'Checks':<7} {'Status':<12} {'First Detected'}")
    print("-" * 90)
    
    for app in apps:
        name = app["name"][:28] + ".." if len(app["name"]) > 30 else app["name"]
        print(f"{app['app_id']:<10} {name:<30} {app['age_days']:>4}d {app['check_count']:>5}x {app['status']:<12} {app['first_detected']}")

def show_history(app_id):
    """Show status history for a specific app"""
    watchlist = load_watchlist()
    app_id_str = str(app_id)
    
    if app_id_str not in watchlist:
        print(f"❌ App {app_id} not found in watchlist")
        return
    
    entry = watchlist[app_id_str]
    print(f"📖 History for App {app_id}")
    print(f"Name: {entry.get('latest_name', 'Unknown')}")
    print(f"Type: {entry.get('latest_type', 'Unknown')}")
    print(f"First detected: {entry.get('first_detected')}")
    print(f"Last checked: {entry.get('last_checked')}")
    print(f"Total checks: {entry.get('check_count', 0)}")
    print(f"Current status: {entry.get('current_status')}")
    
    history = entry.get("status_history", [])
    if history:
        print(f"\n📅 Status History:")
        for event in history:
            print(f"  {event['date']}: {event['status']}")

def remove_app(app_id):
    """Remove an app from the watchlist"""
    watchlist = load_watchlist()
    app_id_str = str(app_id)
    
    if app_id_str not in watchlist:
        print(f"❌ App {app_id} not found in watchlist")
        return
    
    app_name = watchlist[app_id_str].get('latest_name', f'App {app_id}')
    del watchlist[app_id_str]
    save_watchlist(watchlist)
    print(f"✅ Removed {app_name} (ID: {app_id}) from watchlist")

def main():
    parser = argparse.ArgumentParser(description="Manage Steam early-stage app watchlist")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Stats command
    subparsers.add_parser("stats", help="Show watchlist statistics")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List watchlist apps")
    list_parser.add_argument("--limit", type=int, help="Limit number of results")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--sort", choices=["age", "checks", "id"], default="age", help="Sort by field")
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show app history")
    history_parser.add_argument("app_id", type=int, help="Steam app ID")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove app from watchlist")
    remove_parser.add_argument("app_id", type=int, help="Steam app ID")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if not WATCHLIST_FILE.exists():
        print(f"📝 No watchlist file found at {WATCHLIST_FILE}")
        return
    
    if args.command == "stats":
        show_stats()
    elif args.command == "list":
        list_apps(limit=args.limit, status_filter=args.status, sort_by=args.sort)
    elif args.command == "history":
        show_history(args.app_id)
    elif args.command == "remove":
        remove_app(args.app_id)

if __name__ == "__main__":
    main() 