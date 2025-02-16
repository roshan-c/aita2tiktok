import os
from moviepy.config import change_settings

IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
if os.path.exists(IMAGEMAGICK_BINARY):
    change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})