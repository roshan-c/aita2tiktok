# Reddit AITA to TikTok TTS Generator

This project automates the process of converting Reddit AITA (Am I The Asshole?) stories into TTS (Text-to-Speech) audio files and story images for creating TikTok storytime videos. It fetches top stories from r/AmItheAsshole, generates high-quality TTS using Microsoft Edge's voice synthesis, creates corresponding subtitle files, and generates story images with titles and stats.

## Features

- Fetches top stories from r/AmItheAsshole subreddit
- Converts text to speech using Microsoft Edge's natural-sounding voices
- Generates synchronized subtitles for video creation
- Processes multiple stories concurrently
- Cleans and formats Reddit markdown text
- Creates organized output with audio and subtitle files
- Generates story images with titles, upvotes, and comment counts
- Uses customizable template for consistent branding

## Prerequisites

- Python 3.7 or higher
- A Reddit API account (for PRAW)
- Arial.ttf font file (or another font of your choice)
- template.png image file for story backgrounds

## Required Files

Before running the script, ensure you have:

1. A font file (such as: Arial.ttf) in the project root directory
2. A template.png file in the project root directory for the story image background
   - Recommended dimensions: 1080x1920 pixels (9:16 ratio for TikTok)
   - If you watch any TikTok AITA video, you will see they all use a similar image for their introduction. I took that and made my template using it.

## Setup

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root with your Reddit API credentials:
   ```
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   ```

## Usage

1. Run the script:
   ```
   python aita_to_speech.py
   ```

2. The script will:
   - Create a new timestamped output folder (format: YYYYMMDD_HHMMSS)
   - Fetch the top 10 AITA stories of the day
   - Generate MP3 audio files using TTS
   - Create corresponding subtitle files
   - Generate story images with titles and stats
   - Save everything in the newly created output directory

3. Output files will be organized in: `output/YYYYMMDD_HHMMSS/`
   - Audio: `story_title.mp3`
   - Subtitles: `story_title.txt`
   - Images: `story_title.png`
   - Videos (if template.mp4 exists): `story_title.mp4`

The generated files can be used with video editing software to create TikTok storytime content.

## Note

Please ensure you comply with Reddit's content usage policies and TikTok's guidelines when creating and publishing content.