import os
import praw
import markdown
import re
import asyncio
import json
import traceback
import numpy as np
import cv2
from datetime import datetime
from edge_tts import Communicate
from edge_tts.exceptions import NoAudioReceived
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import moviepy.editor as mpy

# Load environment variables
load_dotenv()

# --- Configuration ---
TEMPLATE_IMAGE = "template.png"
FONT_PATH = "arial.ttf"
FONT_SIZE = 32
TEXT_COLOR = (0, 0, 0)
TEXT_POSITION = (50, 200)
MAX_WIDTH = 700
BASE_OUTPUT_DIR = Path("output")
VIDEO_TEMPLATE = "template.mp4"
WORDS_PER_SECOND = 2.5
MIN_OVERLAY_DURATION = 3  # Minimum duration for title screen in seconds
VIDEO_WIDTH = 1080  # TikTok preferred width
VIDEO_HEIGHT = 1920  # TikTok preferred height
VIDEO_FPS = 30  # Standard frame rate for TikTok

# Create a timestamped output directory for this run
CURRENT_RUN_DIR = BASE_OUTPUT_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")

def setup_reddit():
    """Initialize Reddit API client"""
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="AITA_TTS_Bot/1.0",
    )

def clean_text(text):
    """Clean and format the Reddit post text"""
    # Convert markdown to plain text
    text = markdown.markdown(text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove URLs
    text = re.sub(r"http\S+", "", text)
    # Remove multiple newlines and spaces
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    # Replace AITA with full phrase
    text = re.sub(r"\bAITA\b", "Am I the Asshole?", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAITAH\b", "Am I the Asshole?", text, flags=re.IGNORECASE)
    return text.strip()

def fetch_aita_stories(reddit, limit=10):
    """Fetch top stories of today from r/AITA"""
    subreddit = reddit.subreddit("AmItheAsshole")
    stories = []

    for post in subreddit.top(time_filter="day", limit=limit):
        if not post.stickied:  # Skip stickied posts
            stories.append(
                {
                    "title": clean_text(post.title),  # Clean the title too
                    "text": clean_text(post.selftext),
                    "id": post.id,
                    "upvotes": post.score,  # Get upvotes
                    "comments": post.num_comments,  # Get comment count
                }
            )

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
                    "text": event["text"],
                }
                subtitles.append(subtitle_entry)

        # Then generate and save the audio
        await audio_comm.save(str(audio_path))

        # Save subtitles
        with open(subtitle_path, "w", encoding="utf-8") as f:
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
    title = re.sub(
        r"^Am I the Asshole\??\s+(?:for\s+)?", "", title, flags=re.IGNORECASE
    )
    # Replace special characters with underscores
    title = re.sub(r"[^\w\s-]", "", title)
    # Replace spaces with underscores
    title = re.sub(r"\s+", "_", title)
    # Limit length to prevent overly long filenames
    title = title[:50] if len(title) > 50 else title
    return title.strip("_").lower()

def text_wrap(text, font, max_width):
    """Wrap text to fit within a maximum width."""
    lines = []
    # If the text is wider than the max_width, then split it into lines that are no
    # wider than the max_width.
    if font.getlength(text) > max_width:
        # Get all the words in the text.
        words = text.split(" ")
        # Define the first line of text.
        line = ""
        # Cycle through each word.
        for word in words:
            # Define the test line of text.
            test_line = line + word + " "
            # If the test line is wider than the max_width, then add the line to
            # the lines array, set the line to equal the word, and continue to the
            # next word.
            if font.getlength(test_line) > max_width:
                lines.append(line)
                line = word + " "
            # If the test line is not wider than the max_width, then set the line
            # to equal the test line and continue to the next word.
            else:
                line = test_line
        # Add the last line to the lines array.
        lines.append(line)
    # If the text is not wider than the max_width, then just add the text to the
    # lines array.
    else:
        lines.append(text)
    return lines

def generate_image(title, upvotes, comments, output_path):
    """Generate the image for the AITA story."""
    try:
        img = Image.open(TEMPLATE_IMAGE)
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

        # Wrap the title text
        lines = text_wrap(title, font, MAX_WIDTH)
        y = TEXT_POSITION[1]

        for line in lines:
            # Use getbbox() instead of getsize()
            bbox = font.getbbox(line)
            height = bbox[3] - bbox[1]  # bottom - top
            draw.text((TEXT_POSITION[0], y), line, fill=TEXT_COLOR, font=font)
            y += height  # Move to the next line

        # Add upvotes and comments (example - adjust positions as needed)
        draw.text((50, 500), f"Upvotes: {upvotes}", fill=TEXT_COLOR, font=font)
        draw.text((300, 500), f"Comments: {comments}", fill=TEXT_COLOR, font=font)

        img.save(output_path)
        print(f"Generated image: {output_path}")

    except FileNotFoundError as e:
        print(f"Error: Template image or font not found: {e}")
    except Exception as e:
        print(f"Error generating image: {e}")

def ensure_tiktok_dimensions(clip, target_width=1080, target_height=1920):
    """Ensures the clip matches TikTok's preferred dimensions (9:16 ratio)"""
    current_ratio = clip.size[0] / clip.size[1]
    target_ratio = target_width / target_height
    
    if (current_ratio > target_ratio):  # Too wide
        new_width = int(clip.size[1] * target_ratio)
        new_height = clip.size[1]
    else:  # Too tall
        new_width = clip.size[0]
        new_height = int(clip.size[0] / target_ratio)
    
    return clip.resize(width=new_width, height=new_height)

def resize_image_for_tiktok(image_path):
    """Resize image to match TikTok dimensions while maintaining aspect ratio"""
    img = cv2.imread(str(image_path))
    height, width = img.shape[:2]
    
    # Calculate scaling factor to fit TikTok dimensions
    scale = max(VIDEO_WIDTH/width, VIDEO_HEIGHT/height)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    # Resize image
    resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    
    # Calculate cropping coordinates to center the image
    start_x = (new_width - VIDEO_WIDTH) // 2 if new_width > VIDEO_WIDTH else 0
    start_y = (new_height - VIDEO_HEIGHT) // 2 if new_height > VIDEO_HEIGHT else 0
    
    # Crop to TikTok dimensions
    cropped = resized[start_y:start_y+VIDEO_HEIGHT, start_x:start_x+VIDEO_WIDTH]
    
    return cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)

def create_video_with_overlay(image_path, video_path, output_path, duration):
    """Overlays the image on the video for a specified duration."""
    try:
        if not os.path.exists(video_path):
            print(f"Warning: Template video {video_path} not found. Skipping video creation.")
            return False
            
        # Load the video clip
        video = mpy.VideoFileClip(video_path)
        print(f"Original video dimensions: {video.w}x{video.h}")
        
        # Load and prepare the image
        img = Image.open(image_path)
        img = img.convert('RGB')
        img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
        img_array = np.array(img)
        image = mpy.ImageClip(img_array).set_duration(duration)
        
        # First resize video to match target width
        video = video.resize(width=VIDEO_WIDTH)
        
        # Then crop height if needed
        if video.h > VIDEO_HEIGHT:
            y1 = (video.h - VIDEO_HEIGHT) // 2
            video = video.crop(y1=y1, y2=y1 + VIDEO_HEIGHT)
            
        print(f"Final video dimensions: {video.w}x{video.h}")
        
        # Create the final clip
        final = mpy.concatenate_videoclips([image, video])
        
        # Write the final video
        final.write_videofile(
            str(output_path),
            fps=VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            preset='ultrafast'  # Speed up encoding
        )
        
        # Clean up
        video.close()
        image.close()
        final.close()
        img.close()
        
        print(f"Generated video with overlay: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error creating video with overlay: {e}")
        traceback.print_exc()
        return False

async def process_story(story, index):
    """Process a single story asynchronously"""
    print(f"Processing story {index}/10: {story['title'][:50]}...")

    # Combine title and text
    full_text = f"{story['title']}. {story['text']}"

    # Generate output filenames using the sanitized title
    safe_title = sanitize_filename(story["title"])
    base_name = safe_title  # No need for timestamp in filename since we have timestamped folder
    audio_path = CURRENT_RUN_DIR / f"{base_name}.mp3"
    subtitle_path = CURRENT_RUN_DIR / f"{base_name}.txt"
    image_path = CURRENT_RUN_DIR / f"{base_name}.png"
    video_path = CURRENT_RUN_DIR / f"{base_name}.mp4"

    try:
        await generate_tts_with_subtitles(full_text, audio_path, subtitle_path)
        print(f"Generated audio: {audio_path}")
        print(f"Generated subtitles: {subtitle_path}")

        # Generate the image
        generate_image(
            story["title"], story["upvotes"], story["comments"], image_path
        )

        # Only attempt video creation if template.mp4 exists
        if os.path.exists(VIDEO_TEMPLATE):
            # Calculate overlay duration based on title length
            num_words = len(story["title"].split())
            overlay_duration = max(
                num_words / WORDS_PER_SECOND, MIN_OVERLAY_DURATION
            )

            # Create the video with the image overlay
            if not create_video_with_overlay(image_path, VIDEO_TEMPLATE, video_path, overlay_duration):
                print(f"Warning: Video creation failed for {safe_title}")
        else:
            print(f"Warning: Template video {VIDEO_TEMPLATE} not found. Skipping video creation.")

    except Exception as e:
        print(f"Error processing story {story['id']}: {e}")

async def main_async():
    # Create base output directory if it doesn't exist
    BASE_OUTPUT_DIR.mkdir(exist_ok=True)
    # Create timestamped directory for this run
    CURRENT_RUN_DIR.mkdir(exist_ok=True)
    
    print(f"Output directory for this run: {CURRENT_RUN_DIR}")

    # Setup Reddit client
    reddit = setup_reddit()

    # Fetch stories
    print("Fetching AITA stories...")
    stories = fetch_aita_stories(reddit)

    # Process stories concurrently
    tasks = []
    for i, story in enumerate(stories, 1):
        tasks.append(process_story(story, i))

    await asyncio.gather(*tasks)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
