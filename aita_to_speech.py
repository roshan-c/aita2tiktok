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
from PIL import Image, ImageDraw, ImageFont  # Re-added PIL
import moviepy_config  # Import the MoviePy configuration

try:
    from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, \
        CompositeVideoClip
except ImportError:
    print("Trying alternative import...")
    import moviepy.editor as mpy

    VideoFileClip = mpy.VideoFileClip
    AudioFileClip = mpy.AudioFileClip
    TextClip = mpy.TextClip
    CompositeVideoClip = mpy.CompositeVideoClip
import subprocess

# Load environment variables
load_dotenv()

# --- Image Generation Configuration ---
TEMPLATE_IMAGE = "template.png"  # Path to your template image
FONT_PATH = "Arial.ttf"  # Path to your font file
FONT_SIZE = 32  # Font size for image
TEXT_COLOR = (0, 0, 0)  # Black
TEXT_POSITION = (50, 200)  # Top-left corner of the text area
MAX_WIDTH = 700  # Maximum width of the text area

# --- Video Generation Configuration ---
FONT_SIZE_VIDEO = 72  # Increased font size for video
TEXT_COLOR_VIDEO = "white"  # Changed to string
BG_COLOR = "yellow"  # Background color for text
BASE_OUTPUT_DIR = Path("output")
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
FRAME_RATE = 24
TEMPLATE_VIDEO = "template.mp4"  # Background video


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
            json.dump(subtitles, f, indent=4)  # Save as JSON

    except NoAudioReceived as e:
        print(f"Error: No audio received - {str(e)}")
        raise
    except Exception as e:
        print(f"Error during TTS generation: {str(e)}")
        raise


def format_timestamp(seconds):
    """Convert seconds to HH:MM:SS.mmm format"""
    return f"{seconds:.3f}"  # Returns just the seconds as a float string


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
    # Use getlength instead of font.getsize
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
            # Use getlength instead of font.getsize
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
            # Use getbbox instead of getsize
            bbox = font.getbbox(line)
            width = bbox[2] - bbox[0]  # Calculate width
            height = bbox[3] - bbox[1]  # Calculate height

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


async def process_story(story, index, base_output_dir):
    """Process a single story asynchronously"""
    print(f"Processing story {index}/10: {story['title'][:50]}...")

    # Sanitize the title for use as a folder name
    safe_title = sanitize_filename(story["title"])

    # Create the story-specific output directory
    story_output_dir = base_output_dir / safe_title
    story_output_dir.mkdir(parents=True, exist_ok=True)

    # Combine title and text
    full_text = f"{story['title']}. {story['text']}"

    # Generate output filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{safe_title}_{timestamp}"
    audio_path = story_output_dir / f"{base_name}.mp3"
    subtitle_path = story_output_dir / f"{base_name}.json"
    image_path = story_output_dir / f"{base_name}.png"
    video_path = story_output_dir / f"{base_name}.mp4"

    try:
        await generate_tts_with_subtitles(full_text, audio_path, subtitle_path)
        print(f"Generated audio: {audio_path}")
        print(f"Generated subtitles: {subtitle_path}")

        # Generate the image
        generate_image(
            story["title"], story["upvotes"], story["comments"], image_path
        )

        # Process video
        background_video = VideoFileClip(TEMPLATE_VIDEO,
                                         audio=False).resize(
                                             (VIDEO_WIDTH, VIDEO_HEIGHT)
                                         )  # Load background

        audio = AudioFileClip(str(audio_path))

        # Get the duration of the audio
        audio_duration = audio.duration

        # Trim the background video to match audio duration (plus 1 second)
        final_duration = audio_duration + 1
        video = background_video.subclip(0, final_duration)

        # Load subtitles from JSON
        with open(subtitle_path, "r", encoding="utf-8") as f:
            subtitles = json.load(f)

        # Create word clips
        word_clips = []
        for sub in subtitles:
            start_time = float(sub['start'])
            end_time = float(sub['end'])
            word = sub['text']

            word_clip = (
                TextClip(
                    word,
                    fontsize=FONT_SIZE_VIDEO,
                    color=TEXT_COLOR_VIDEO,
                    bg_color=BG_COLOR,
                    font=FONT_PATH,
                )
                .set_start(start_time)
                .set_end(end_time)
                .set_pos("center")
                .set_duration(end_time - start_time)  # Explicit duration
            )
            word_clips.append(word_clip)

        # Combine video with audio and word clips
        final_video = CompositeVideoClip([video] + word_clips,
                                         use_mask=True)  # Use mask
        final_video = final_video.set_audio(audio)

        # Write the final video
        final_video.write_videofile(
            str(video_path),
            codec='libx264',
            audio_codec='aac',
            fps=FRAME_RATE,
            threads=4,  # Limit threads
            logger=None,  # Suppress logs
        )

        # Clean up
        background_video.close()
        audio.close()
        final_video.close()
        del background_video, audio, final_video, word_clips, subtitles  # Explicitly delete

    except Exception as e:
        print(f"Error processing story {story['id']}: {e}")


async def main_async():
    # Create a new output directory based on timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output_dir = BASE_OUTPUT_DIR / timestamp
    base_output_dir.mkdir(parents=True, exist_ok=True)

    # Setup Reddit client
    reddit = setup_reddit()

    # Fetch stories
    print("Fetching AITA stories...")
    stories = fetch_aita_stories(reddit)

    # Process stories sequentially
    for i, story in enumerate(stories, 1):
        await process_story(story, i, base_output_dir)  # Process one at a time


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
