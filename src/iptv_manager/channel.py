"""
Channel model for IPTV tester.
"""

from dataclasses import dataclass, field
from typing import Optional
import time
import re


@dataclass
class Channel:
    """Represents a TV channel."""

    name: str
    url: str
    epg_id: Optional[str] = None
    logo: Optional[str] = None
    group_title: Optional[str] = None

    # Test results
    http_code: int = 0
    response_time: float = 0.0
    is_m3u8: bool = False
    has_segments: bool = False
    stream_type: str = ""
    status: str = "UNKNOWN"  # OK, UNKNOWN, FAILED
    reason: str = ""
    score: int = 0
    tested_at: float = field(default_factory=time.time)

    @classmethod
    def from_m3u_line(cls, line: str) -> "Channel":
        """Create a Channel from an #EXTINF line."""
        # Example: #EXTINF:-1 tvg-id="1tv.pl" tvg-logo="http://example.com/logo.png" group-title="News",TVP Info
        # We'll parse the attributes and the channel name.
        if not line.startswith('#EXTINF:'):
            raise ValueError("Line does not start with #EXTINF:")

        # Remove the #EXTINF:-1 part
        parts = line[len('#EXTINF:-1'):].strip().split(',', 1)
        if len(parts) < 2:
            raise ValueError("Invalid EXTINF line: no channel name")

        attributes_str, name = parts
        name = name.strip()

        # Parse attributes
        epg_id = None
        logo = None
        group_title = None

        # Simple attribute parsing: look for tvg-id="...", tvg-logo="...", group-title="..."
        tvg_id_match = re.search(r'tvg-id="([^"]*)"', attributes_str)
        if tvg_id_match:
            epg_id = tvg_id_match.group(1)

        tvg_logo_match = re.search(r'tvg-logo="([^"]*)"', attributes_str)
        if tvg_logo_match:
            logo = tvg_logo_match.group(1)

        group_title_match = re.search(r'group-title="([^"]*)"', attributes_str)
        if group_title_match:
            group_title = group_title_match.group(1)

        return cls(
            name=name,
            url="",  # URL will be set from the next line
            epg_id=epg_id,
            logo=logo,
            group_title=group_title
        )

    def to_dict(self) -> dict:
        """Convert the channel to a dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "epg_id": self.epg_id,
            "logo": self.logo,
            "group_title": self.group_title,
            "http_code": self.http_code,
            "response_time": self.response_time,
            "is_m3u8": self.is_m3u8,
            "has_segments": self.has_segments,
            "stream_type": self.stream_type,
            "status": self.status,
            "reason": self.reason,
            "score": self.score,
            "tested_at": self.tested_at
        }