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
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    concatenate_videoclips,
)  # Import moviepy modules

# Load environment variables
load_dotenv()

# --- Image Generation Configuration ---
TEMPLATE_IMAGE = "template.png"  # Path to your template image
FONT_PATH = "arial.ttf"  # Path to your font file
FONT_SIZE = 32
TEXT_COLOR = (0, 0, 0)  # Black
TEXT_POSITION = (50, 200)  # Top-left corner of the text area
MAX_WIDTH = 700  # Maximum width of the text area
OUTPUT_DIR = Path("output")
VIDEO_TEMPLATE = "template.mp4"  # Path to your video template
WORDS_PER_SECOND = 2.5  # Assumed reading speed (words per second)
MIN_OVERLAY_DURATION = 2  # Minimum overlay duration in seconds


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
    # Return the lines array.
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
            width, height = font.getsize(line)
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


def create_video_with_overlay(image_path, video_path, output_path, duration):
    """Overlays the image on the video for a specified duration."""
    try:
        # Load the video clip
        video_clip = VideoFileClip(video_path)

        # Load the image
        image_clip = ImageClip(image_path).set_duration(duration)

        # Composite the image on top of the video
        final_clip = concatenate_videoclips([image_clip, video_clip])

        # Write the final video to a file
        final_clip.write_videofile(
            output_path, fps=24, codec="libx264", audio_codec="aac"
        )  # Adjust fps and codec as needed

        print(f"Generated video with overlay: {output_path}")

    except Exception as e:
        print(f"Error creating video with overlay: {e}")


async def process_story(story, index):
    """Process a single story asynchronously"""
    print(f"Processing story {index}/10: {story['title'][:50]}...")

    # Combine title and text
    full_text = f"{story['title']}. {story['text']}"

    # Generate output filenames using the sanitized title
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = sanitize_filename(story["title"])
    base_name = f"{safe_title}_{timestamp}"
    audio_path = OUTPUT_DIR / f"{base_name}.mp3"
    subtitle_path = OUTPUT_DIR / f"{base_name}.txt"
    image_path = OUTPUT_DIR / f"{base_name}.png"
    video_path = OUTPUT_DIR / f"{base_name}.mp4"  # Output video path

    try:
        await generate_tts_with_subtitles(full_text, audio_path, subtitle_path)
        print(f"Generated audio: {audio_path}")
        print(f"Generated subtitles: {subtitle_path}")

        # Generate the image
        generate_image(
            story["title"], story["upvotes"], story["comments"], image_path
        )

        # Calculate overlay duration based on title length
        num_words = len(story["title"].split())
        overlay_duration = max(
            num_words / WORDS_PER_SECOND, MIN_OVERLAY_DURATION
        )  # Ensure a minimum duration

        # Create the video with the image overlay
        create_video_with_overlay(
            image_path, VIDEO_TEMPLATE, video_path, overlay_duration
        )

    except Exception as e:
        print(f"Error processing story {story['id']}: {e}")


async def main_async():
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

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
