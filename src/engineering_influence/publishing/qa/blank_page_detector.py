"""Finds visually blank pages."""

import numpy as np
from PIL import Image


class BlankPageDetector:
    """A page is blank when nothing on it is darker than light gray."""

    def is_blank(self, image: Image.Image) -> bool:
        """True for a white page; a nearly white page with a tiny mark is not blank."""
        gray = image.convert("L")
        if int(np.asarray(gray).min()) < 245:
            return False
        # Count dark pixels after downsampling to keep this cheap on long books.
        sample = gray.copy()
        sample.thumbnail((160, 240))
        return bool(int(np.asarray(sample).min()) >= 245)
