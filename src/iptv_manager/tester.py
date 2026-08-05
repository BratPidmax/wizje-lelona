"""
Channel tester module.
"""

import asyncio
import aiohttp
import time
from typing import Optional
from .channel import Channel
from .logger import IPTVLogger
import yaml
import os


class ChannelTester:
    """Tests a single channel and returns the result."""

    def __init__(self, config_path: str = "config/testing.yaml"):
        self.config = self._load_config(config_path)
        self.logger = IPTVLogger()

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        default_config = {
            "timeout": 10,
            "parallel_workers": 10,
            "retry_count": 3,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "verify_segments": True,
            "verify_ssl": True,
        }
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
        return default_config

    async def test_channel(self, channel: Channel) -> Channel:
        """Test a single channel and update its status."""
        start_time = time.time()
        session = None
        try:
            # Create a session with custom settings
            connector = aiohttp.TCPConnector(ssl=self.config["verify_ssl"])
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.config["timeout"]),
                headers={"User-Agent": self.config["user_agent"]}
            )

            # Try to fetch the channel URL
            for attempt in range(self.config["retry_count"]):
                try:
                    async with session.get(channel.url) as response:
                        channel.http_code = response.status
                        channel.response_time = time.time() - start_time

                        # Check if it's a M3U8 playlist
                        content_type = response.headers.get('Content-Type', '')
                        is_m3u8 = 'application/vnd.apple.mpegurl' in content_type or \
                                  'application/vnd.apple.mpegurl' in content_type or \
                                  channel.url.endswith('.m3u8') or \
                                  '.m3u8?' in channel.url

                        channel.is_m3u8 = is_m3u8

                        if is_m3u8 and self.config["verify_segments"]:
                            # Try to read the playlist and check for segments
                            text = await response.text()
                            lines = text.split('\n')
                            # Look for segment lines (not starting with #)
                            segment_lines = [line for line in lines if line and not line.startswith('#')]
                            channel.has_segments = len(segment_lines) > 0
                            channel.stream_type = "HLS"
                        else:
                            # For non-M3U8, we assume it's a stream if we get 200 and content length > 0
                            content_length = response.headers.get('Content-Length')
                            if content_length and int(content_length) > 0:
                                channel.has_segments = True
                                channel.stream_type = "Direct"
                            else:
                                # Try to read a small chunk to see if we get data
                                chunk = await response.content.read(1024)
                                channel.has_segments = len(chunk) > 0
                                channel.stream_type = "Direct" if channel.has_segments else "Unknown"

                        # Determine status and score
                        self._determine_status_and_score(channel)
                        break
                except asyncio.TimeoutError:
                    if attempt == self.config["retry_count"] - 1:
                        channel.http_code = 408
                        channel.response_time = time.time() - start_time
                        channel.reason = "Timeout"
                    else:
                        await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                except Exception as e:
                    if attempt == self.config["retry_count"] - 1:
                        channel.http_code = 0
                        channel.response_time = time.time() - start_time
                        channel.reason = f"Error: {str(e)[:100]}"
                    else:
                        await asyncio.sleep(1 * (attempt + 1))

        except Exception as e:
            channel.http_code = 0
            channel.response_time = time.time() - start_time
            channel.reason = f"Connection error: {str(e)[:100]}"
        finally:
            if session:
                await session.close()

        # Log the result
        self.logger.info(
            f"{channel.name} | {channel.url} | {channel.http_code} | {channel.response_time:.2f}s | "
            f"{channel.status} | {channel.reason}"
        )

        channel.tested_at = time.time()
        return channel

    def _determine_status_and_score(self, channel: Channel) -> None:
        """Determine the status and score of the channel based on test results."""
        score = 0
        reason_parts = []

        # HTTP status
        if channel.http_code == 200:
            score += 20
            reason_parts.append("HTTP OK")
        elif channel.http_code in [404, 410]:
            channel.status = "FAILED"
            reason_parts.append(f"HTTP {channel.http_code}")
            channel.reason = ", ".join(reason_parts)
            channel.score = score
            return
        elif channel.http_code == 403:
            # Might be blocked, but could be UNKNOWN
            reason_parts.append(f"HTTP {channel.http_code} (Forbidden)")
        elif channel.http_code != 0:
            reason_parts.append(f"HTTP {channel.http_code}")
        else:
            reason_parts.append("Connection failed")

        # M3U8 check
        if channel.is_m3u8:
            score += 20
            reason_parts.append("M3U8 valid")
        else:
            reason_parts.append("Not M3U8")

        # Segments check
        if channel.has_segments:
            score += 20
            reason_parts.append("Segments found")
        else:
            reason_parts.append("No segments")

        # Response time
        if channel.response_time is not None and channel.response_time < 1.0:
            score += 20
            reason_parts.append("Fast (<1s)")
        elif channel.response_time is not None and channel.response_time < 3.0:
            score += 10
            reason_parts.append("Medium (<3s)")
        else:
            reason_parts.append("Slow (>=3s)")

        # Stability (we don't have multiple tests, so we'll assume stable if we got here)
        # In a more advanced version, we could test multiple times.
        score += 20  # Assume stable for now
        reason_parts.append("Stable (assumed)")

        channel.score = score

        # Determine status
        if channel.http_code == 200 and channel.is_m3u8 and channel.has_segments and channel.response_time < 1.0:
            channel.status = "OK"
        elif channel.http_code in [404, 410]:
            channel.status = "FAILED"
        else:
            channel.status = "UNKNOWN"

        channel.reason = ", ".join(reason_parts)


async def test_channels(channels: list[Channel], config_path: str = "config/testing.yaml") -> list[Channel]:
    """Test a list of channels concurrently."""
    tester = ChannelTester(config_path)
    semaphore = asyncio.Semaphore(tester.config["parallel_workers"])

    async def test_with_semaphore(channel: Channel) -> Channel:
        async with semaphore:
            return await tester.test_channel(channel)

    tasks = [test_with_semaphore(channel) for channel in channels]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return results