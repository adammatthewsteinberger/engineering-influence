"""Amazon KDP cover dimensions and limits."""


class KdpCoverSpec:
    """Constants from KDP's published cover guidelines, checked on every build."""

    PPI = 300
    TRIM_W, TRIM_H = 6.0, 9.0
    BLEED = 0.125
    PAPER_WHITE = 0.002252  # inches per page, KDP white paper with black ink
    MM = 1 / 25.4
    HC_SPINE_EXTRA = 4.8 * MM  # case laminate spine allowance (0.189 in)
    HC_BOARD_W, HC_BOARD_H = 5 * MM, 6 * MM  # boards are 5 mm wider and 6 mm taller than trim
    HC_WRAP = 15 * MM  # wrap around the boards (0.591 in)
    HC_HINGE = 10 * MM  # hinge beside the spine, kept free of text (0.394 in)
    BARCODE_W, BARCODE_H = 2.0, 1.2
    EBOOK_PX = (1600, 2560)
    DPI_TAG = 300  # resolution written into every image file
    MIN_TEXT_PT = 7.0  # print covers: smallest text KDP allows
    TEXT_FLOOR_IN = 7.5 / 72  # smallest text the engine sets on print covers
    PDF_MAX_MB = 40  # KDP's recommended ceiling for a cover PDF
    EBOOK_MAX_MB = 50
    EBOOK_MIN_PX = (625, 1000)
    EBOOK_MAX_PX = 10000
    SPINE_TEXT_MIN_PAGES = 79
    EBOOK_BORDER_PX = 4
    EBOOK_BORDER_RGB = (128, 128, 128)
