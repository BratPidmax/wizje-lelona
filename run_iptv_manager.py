#!/usr/bin/env python3
"""
Wizje Lełona - Main script for testing IPTV channels and generating playlists.
"""

import asyncio
import os
from pathlib import Path
from src.iptv_manager.playlist import read_m3u, write_m3u
from src.iptv_manager.tester import test_channels
from src.iptv_manager.config import Config
import json
import csv
from datetime import datetime


async def main():
    """Main function to run the IPTV manager."""
    print("Starting Wizje Lełona...")

    # Initialize configuration
    config = Config()
    print(f"Configuration loaded: {config.config_path}")

    # Define paths
    source_playlist = Path("/home/mx/polska-iptv-rozszerzona.m3u")
    playlists_dir = Path("playlists")
    reports_dir = Path("reports")
    logs_dir = Path("logs")

    # Ensure directories exist
    playlists_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    # Read the source playlist
    print(f"Reading source playlist: {source_playlist}")
    if not source_playlist.exists():
        print(f"Error: Source playlist not found at {source_playlist}")
        return

    channels = read_m3u(str(source_playlist))
    print(f"Loaded {len(channels)} channels from the source playlist.")

    # Test all channels
    print("Testing channels...")
    tested_channels = await test_channels(channels, str(config.config_path))

    # Categorize channels by status
    ok_channels = [ch for ch in tested_channels if ch.status == "OK"]
    unknown_channels = [ch for ch in tested_channels if ch.status == "UNKNOWN"]
    failed_channels = [ch for ch in tested_channels if ch.status == "FAILED"]

    print(f"Results: {len(ok_channels)} OK, {len(unknown_channels)} UNKNOWN, {len(failed_channels)} FAILED")

    # Generate playlists
    # wizje-lelona-full.m3u: all channels
    write_m3u(tested_channels, playlists_dir / "wizje-lelona-full.m3u")
    print(f"Generated {playlists_dir / 'wizje-lelona-full.m3u'} with {len(tested_channels)} channels.")

    # wizje-lelona-stable.m3u: only OK channels
    write_m3u(ok_channels, playlists_dir / "wizje-lelona-stable.m3u")
    print(f"Generated {playlists_dir / 'wizje-lelona-stable.m3u'} with {len(ok_channels)} channels.")

    # wizje-lelona-testing.m3u: OK + UNKNOWN
    testing_channels = ok_channels + unknown_channels
    write_m3u(testing_channels, playlists_dir / "wizje-lelona-testing.m3u")
    print(f"Generated {playlists_dir / 'wizje-lelona-testing.m3u'} with {len(testing_channels)} channels.")

    # wizje-lelona-verification.m3u: only UNKNOWN
    write_m3u(unknown_channels, playlists_dir / "wizje-lelona-verification.m3u")
    print(f"Generated {playlists_dir / 'wizje-lelona-verification.m3u'} with {len(unknown_channels)} channels.")

    # Generate reports
    generate_reports(tested_channels, reports_dir)

    print("Wizje Lełona finished.")


def generate_reports(channels, reports_dir: Path):
    """Generate the required reports."""
    # 1. reports/stable_report.md
    stable_report_path = reports_dir / "stable_report.md"
    with open(stable_report_path, 'w', encoding='utf-8') as f:
        f.write("# Stable Playlist Report\n\n")
        f.write(f"**Generated at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total channels:** {len(channels)}\n\n")

        ok_count = len([c for c in channels if c.status == "OK"])
        unknown_count = len([c for c in channels if c.status == "UNKNOWN"])
        failed_count = len([c for c in channels if c.status == "FAILED"])
        failed_channels = [c for c in channels if c.status == "FAILED"]

        f.write(f"**OK channels:** {ok_count}\n")
        f.write(f"**UNKNOWN channels:** {unknown_count}\n")
        f.write(f"**FAILED channels:** {failed_count}\n\n")

        # Average response time (only for those that have a response time)
        response_times = [c.response_time for c in channels if c.response_time > 0]
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            f.write(f"**Average response time:** {avg_response:.2f} seconds\n\n")
        else:
            f.write("**Average response time:** N/A (no successful connections)\n\n")

        # Top 10 channels by score (highest score first)
        sorted_by_score = sorted(channels, key=lambda x: x.score, reverse=True)
        f.write("## Top 10 Channels by Score\n\n")
        f.write("| Rank | Channel Name | Score | Status | Response Time (s) | Reason |\n")
        f.write("|------|--------------|-------|--------|-------------------|--------|\n")
        for i, ch in enumerate(sorted_by_score[:10], 1):
            f.write(f"| {i} | {ch.name} | {ch.score} | {ch.status} | {ch.response_time:.2f} | {ch.reason} |\n")
        f.write("\n")

        # Bottom 10 channels by score (lowest score first)
        f.write("## Bottom 10 Channels by Score\n\n")
        f.write("| Rank | Channel Name | Score | Status | Response Time (s) | Reason |\n")
        f.write("|------|--------------|-------|--------|-------------------|--------|\n")
        for i, ch in enumerate(sorted_by_score[-10:], 1):
            f.write(f"| {i} | {ch.name} | {ch.score} | {ch.status} | {ch.response_time:.2f} | {ch.reason} |\n")
        f.write("\n")

        # List of FAILED channels with reason
        f.write("## FAILED Channels\n\n")
        if failed_channels:
            f.write("| Channel Name | URL | HTTP Code | Reason |\n")
            f.write("|--------------|-----|-----------|--------|\n")
            for ch in failed_channels:
                f.write(f"| {ch.name} | {ch.url} | {ch.http_code} | {ch.reason} |\n")
        else:
            f.write("No failed channels.\n")
        f.write("\n")

    print(f"Generated stable report: {stable_report_path}")

    # 2. reports/status.json
    status_report = {
        "timestamp": datetime.now().isoformat(),
        "total_channels": len(channels),
        "ok": ok_count,
        "unknown": unknown_count,
        "failed": failed_count,
        "average_response_time": sum(response_times) / len(response_times) if response_times else 0,
        "channels": [ch.to_dict() for ch in channels]
    }
    status_json_path = reports_dir / "status.json"
    with open(status_json_path, 'w', encoding='utf-8') as f:
        json.dump(status_report, f, indent=2, ensure_ascii=False)
    print(f"Generated status JSON: {status_json_path}")

    # 3. reports/channel_report.csv
    csv_path = reports_dir / "channel_report.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Header
        writer.writerow([
            "Channel Name", "URL", "EPG ID", "Logo", "Group Title",
            "HTTP Code", "Response Time (s)", "Is M3U8", "Has Segments",
            "Stream Type", "Status", "Reason", "Score", "Tested At"
        ])
        for ch in channels:
            writer.writerow([
                ch.name, ch.url, ch.epg_id or "", ch.logo or "", ch.group_title or "",
                ch.http_code, f"{ch.response_time:.3f}", ch.is_m3u8, ch.has_segments,
                ch.stream_type, ch.status, ch.reason, ch.score,
                datetime.fromtimestamp(ch.tested_at).isoformat() if ch.tested_at else ""
            ])
    print(f"Generated channel report CSV: {csv_path}")


if __name__ == "__main__":
    asyncio.run(main())