import os
from moviepy.config import change_settings

# ImageMagick 7+ uses magick.exe, so we'll force this path
IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"

if os.path.exists(IMAGEMAGICK_BINARY):
    change_settings({
        "IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY,
        # Force using the newer ImageMagick command syntax
        "IMAGEMAGICK_BINARY_PATH": os.path.dirname(IMAGEMAGICK_BINARY)
    })