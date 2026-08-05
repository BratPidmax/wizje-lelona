"""
Playlist module for reading and writing M3U playlists.
"""

from typing import List
from .channel import Channel


def read_m3u(file_path: str) -> List[Channel]:
    """Read an M3U file and return a list of Channel objects."""
    channels = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            try:
                channel = Channel.from_m3u_line(line)
                # Check if there's a URL on the next line
                if i + 1 < len(lines):
                    url = lines[i + 1].strip()
                    if not url.startswith('#'):
                        channel.url = url
                        i += 1  # Skip the URL line
                channels.append(channel)
            except ValueError:
                # If we can't parse the line, just skip it
                pass
        i += 1

    return channels


def write_m3u(channels: List[Channel], file_path: str) -> None:
    """Write a list of Channel objects to an M3U file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for channel in channels:
            # Build the EXTINF line
            extinf = '#EXTINF:-1'
            if channel.epg_id:
                extinf += f' tvg-id="{channel.epg_id}"'
            if channel.logo:
                extinf += f' tvg-logo="{channel.logo}"'
            if channel.group_title:
                extinf += f' group-title="{channel.group_title}"'
            extinf += f',' + channel.name
            f.write(extinf + '\n')
            f.write(channel.url + '\n')