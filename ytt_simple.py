#!/usr/bin/env python3
"""
Simple YouTube Transcript Extractor
Uses the official youtube-transcript-api library for reliable transcript extraction
"""

import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter


def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        r'youtube\.com/v/([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_youtube_transcript(video_url, language_codes=['en']):
    """
    Get transcript for a YouTube video using the official API
    
    Args:
        video_url (str): YouTube video URL
        language_codes (list): List of language codes to try (default: ['en'])
    
    Returns:
        list: List of transcript segments with text and timing info
        None: If transcript not available
    """
    # Extract video ID
    video_id = extract_video_id(video_url)
    if not video_id:
        print("Could not extract video ID from URL")
        return None
    
    print(f"Extracting transcript for video ID: {video_id}")
    
    try:
        # Create API instance
        api = YouTubeTranscriptApi()
        
        # Try to get transcript in the specified languages
        transcript = api.fetch(video_id, languages=language_codes)
        return transcript
        
    except Exception as e:
        print(f"Error getting transcript: {e}")
        
        # Try to get any available transcript
        try:
            print("Trying to get any available transcript...")
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id)
            return transcript
        except Exception as e2:
            print(f"Error getting any transcript: {e2}")
            return None


def format_transcript_as_text(transcript):
    """Format transcript as plain text"""
    if not transcript:
        return None
    
    # Simple text formatting
    return " ".join(segment.text for segment in transcript.snippets)


def format_transcript_as_list(transcript):
    """Format transcript as a list of text segments"""
    if not transcript:
        return None
    
    return [segment.text for segment in transcript.snippets]


# Example usage
if __name__ == "__main__":
    # Test with different URLs
    test_urls = [
        'https://www.youtube.com/watch?v=C1CP3ZSXDJo',
        'https://www.youtube.com/watch?v=W9pKMPV8wNU',
        'https://youtu.be/dQw4w9WgXcQ',  # Rick Roll for testing
    ]
    
    for video_url in test_urls:
        print(f"\n{'='*60}")
        print(f"Getting transcript for: {video_url}")
        print('='*60)
        
        # Get transcript
        transcript = get_youtube_transcript(video_url)
        
        if transcript:
            print(f"✅ Successfully retrieved transcript with {len(transcript.snippets)} segments")
            
            # Show first few segments
            print("\nFirst 3 transcript segments:")
            for i, segment in enumerate(transcript.snippets[:3]):
                print(f"{i+1}. [{segment.start:.1f}s] {segment.text}")
            
            # Show formatted text (first 500 characters)
            text_formatted = format_transcript_as_text(transcript)
            if text_formatted:
                print(f"\nFormatted text (first 500 chars):")
                print(text_formatted[:500] + "..." if len(text_formatted) > 500 else text_formatted)
        else:
            print("❌ Failed to get transcript")
        
        print()
