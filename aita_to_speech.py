import os
import praw
import markdown
import re
import asyncio
import json
from datetime import datetime
from edge_tts import Communicate
from edge_tts.exceptions import NoAudioReceived
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_reddit():
    """Initialize Reddit API client"""
    return praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        user_agent="AITA_TTS_Bot/1.0"
    )

def clean_text(text):
    """Clean and format the Reddit post text"""
    # Convert markdown to plain text
    text = markdown.markdown(text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove multiple newlines and spaces
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    # Replace AITA with full phrase
    text = re.sub(r'\bAITA\b', 'Am I the Asshole?', text, flags=re.IGNORECASE)
    text = re.sub(r'\bAITAH\b', 'Am I the Asshole?', text, flags=re.IGNORECASE)
    return text.strip()

def fetch_aita_stories(reddit, limit=10):
    """Fetch top stories of today from r/AITA"""
    subreddit = reddit.subreddit('AmItheAsshole')
    stories = []
    
    for post in subreddit.top(time_filter='day', limit=limit):
        if not post.stickied:  # Skip stickied posts
            stories.append({
                'title': clean_text(post.title),  # Clean the title too
                'text': clean_text(post.selftext),
                'id': post.id
            })
    
    return stories

async def generate_tts_with_subtitles(text, audio_path, subtitle_path):
    """Generate TTS audio and subtitles using Microsoft Edge's TTS"""
    # Create two separate communicators for audio and subtitles
    audio_comm = Communicate(text, "en-US-JennyNeural", rate="+0%", volume="+0%")
    subtitle_comm = Communicate(text, "en-US-JennyNeural", rate="+0%", volume="+0%")
    
    try:
        # First, collect all word boundaries for subtitles
        subtitles = []
        async for event in subtitle_comm.stream():
            if event["type"] == "WordBoundary":
                # Convert time from 100-nanosecond units to seconds
                start_time = event["offset"] / 10_000_000
                duration = event["duration"] / 10_000_000
                
                subtitle_entry = {
                    "start": format_timestamp(start_time),
                    "end": format_timestamp(start_time + duration),
                    "text": event["text"]
                }
                subtitles.append(subtitle_entry)
        
        # Then generate and save the audio
        await audio_comm.save(str(audio_path))
        
        # Save subtitles
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            for sub in subtitles:
                f.write(f"[{sub['start']} --> {sub['end']}] {sub['text']}\n")
                
    except NoAudioReceived as e:
        print(f"Error: No audio received - {str(e)}")
        raise
    except Exception as e:
        print(f"Error during TTS generation: {str(e)}")
        raise

def format_timestamp(seconds):
    """Convert seconds to HH:MM:SS.mmm format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_remainder = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds_remainder:06.3f}"

def sanitize_filename(title):
    """Convert a title into a safe filename"""
    # Remove 'Am I the Asshole?' since we don't need it in filename
    title = re.sub(r'^Am I the Asshole\??\s+(?:for\s+)?', '', title, flags=re.IGNORECASE)
    # Replace special characters with underscores
    title = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces with underscores
    title = re.sub(r'\s+', '_', title)
    # Limit length to prevent overly long filenames
    title = title[:50] if len(title) > 50 else title
    return title.strip('_').lower()

async def process_story(story, output_dir, index):
    """Process a single story asynchronously"""
    print(f"Processing story {index}/10: {story['title'][:50]}...")
    
    # Combine title and text
    full_text = f"{story['title']}. {story['text']}"
    
    # Generate output filenames using the sanitized title
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = sanitize_filename(story['title'])
    base_name = f"{safe_title}_{timestamp}"
    audio_path = output_dir / f"{base_name}.mp3"
    subtitle_path = output_dir / f"{base_name}.txt"
    
    try:
        await generate_tts_with_subtitles(full_text, audio_path, subtitle_path)
        print(f"Generated audio: {audio_path}")
        print(f"Generated subtitles: {subtitle_path}")
    except Exception as e:
        print(f"Error processing story {story['id']}: {e}")

async def main_async():
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Setup Reddit client
    reddit = setup_reddit()
    
    # Fetch stories
    print("Fetching AITA stories...")
    stories = fetch_aita_stories(reddit)
    
    # Process stories concurrently
    tasks = []
    for i, story in enumerate(stories, 1):
        tasks.append(process_story(story, output_dir, i))
    
    await asyncio.gather(*tasks)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()