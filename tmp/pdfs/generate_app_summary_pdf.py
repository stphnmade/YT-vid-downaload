import os
import sys
from textwrap import wrap

sys.path.insert(0, os.path.abspath(r"c:\Users\Steph\YT-viddowloader\tmp\pdfs\deps"))

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
import pdfplumber
import pypdfium2 as pdfium


ROOT = os.path.abspath(r"c:\Users\Steph\YT-viddowloader")
OUTPUT_DIR = os.path.join(ROOT, "output", "pdf")
TMP_DIR = os.path.join(ROOT, "tmp", "pdfs")
PDF_PATH = os.path.join(OUTPUT_DIR, "yt-download-app-summary.pdf")
PNG_PATH = os.path.join(TMP_DIR, "yt-download-app-summary-page-1.png")

PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN_X = 38
TOP_Y = PAGE_HEIGHT - 42
BOTTOM_Y = 38
GUTTER = 20
COLUMN_WIDTH = (PAGE_WIDTH - (MARGIN_X * 2) - GUTTER) / 2

TITLE_COLOR = HexColor("#23211d")
SUBTITLE_COLOR = HexColor("#5e584d")
SECTION_COLOR = HexColor("#3d372d")
BODY_COLOR = HexColor("#27231d")
RULE_COLOR = HexColor("#c8c1b5")
ACCENT_COLOR = HexColor("#9a7b4f")
PANEL_COLOR = HexColor("#f5f1ea")


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)


def wrap_lines(text, font_name, font_size, width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if stringWidth(candidate, font_name, font_size) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def draw_wrapped_text(c, x, y, text, *, width, font_name="Helvetica", font_size=10, color=BODY_COLOR, leading=13):
    c.setFillColor(color)
    c.setFont(font_name, font_size)
    lines = wrap_lines(text, font_name, font_size, width)
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def draw_bullets(c, x, y, items, *, width, font_size=10, leading=12.5, bullet_indent=9, text_indent=16):
    c.setFont("Helvetica", font_size)
    c.setFillColor(BODY_COLOR)
    text_width = width - text_indent
    for item in items:
        lines = wrap_lines(item, "Helvetica", font_size, text_width)
        c.drawString(x + bullet_indent - 7, y, "-")
        c.drawString(x + text_indent, y, lines[0])
        y -= leading
        for line in lines[1:]:
            c.drawString(x + text_indent, y, line)
            y -= leading
        y -= 2
    return y


def draw_section(c, x, y, heading, body_lines=None, bullets=None, width=COLUMN_WIDTH):
    c.setFillColor(SECTION_COLOR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, heading)
    y -= 7
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(0.8)
    c.line(x, y, x + width, y)
    y -= 14
    if body_lines:
        for paragraph in body_lines:
            y = draw_wrapped_text(
                c,
                x,
                y,
                paragraph,
                width=width,
                font_name="Helvetica",
                font_size=10,
                color=BODY_COLOR,
                leading=13,
            )
            y -= 3
    if bullets:
        y = draw_bullets(c, x, y, bullets, width=width, font_size=10, leading=12.5)
    return y - 4


def build_pdf():
    ensure_dirs()

    c = canvas.Canvas(PDF_PATH, pagesize=letter)
    c.setTitle("YT Download App Summary")

    c.setFillColor(PANEL_COLOR)
    c.roundRect(26, PAGE_HEIGHT - 128, PAGE_WIDTH - 52, 90, 14, fill=1, stroke=0)

    c.setFillColor(ACCENT_COLOR)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(MARGIN_X, TOP_Y, "YT Download App")

    c.setFillColor(SUBTITLE_COLOR)
    c.setFont("Helvetica", 11)
    c.drawString(MARGIN_X, TOP_Y - 20, "One-page summary based on repo files and current source code.")

    c.setFillColor(TITLE_COLOR)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN_X, TOP_Y - 52, "Scope")
    c.setFont("Helvetica", 10.5)
    c.setFillColor(BODY_COLOR)
    c.drawString(
        MARGIN_X + 48,
        TOP_Y - 52,
        "Windows/macOS desktop app for single-item YouTube downloads as MP4 video or MP3 audio.",
    )

    left_x = MARGIN_X
    right_x = MARGIN_X + COLUMN_WIDTH + GUTTER
    start_y = PAGE_HEIGHT - 152

    left_y = start_y
    left_y = draw_section(
        c,
        left_x,
        left_y,
        "What it is",
        body_lines=[
            "A minimal desktop app for downloading YouTube media locally as MP4 video or MP3 audio.",
            "Electron provides the desktop shell, React renders the interface, and a Python service runs the download workflow.",
        ],
    )
    left_y = draw_section(
        c,
        left_x,
        left_y,
        "Who it's for",
        body_lines=[
            "Named persona: Not found in repo.",
            "Inferred primary user: a Windows or macOS user who wants a simple, one-link-at-a-time way to save YouTube media offline.",
        ],
    )
    left_y = draw_section(
        c,
        left_x,
        left_y,
        "What it does",
        bullets=[
            "Accepts YouTube URLs and rejects invalid or non-YouTube links.",
            "Downloads one item at a time as MP4 video or MP3 audio.",
            "Shows live status, filename, and percent progress in the UI.",
            "Lets the user change the save folder and persists that setting.",
            "Cancels the active download from the desktop app.",
            "Shows recent jobs and can open the saved file or reveal its folder.",
        ],
    )

    right_y = start_y
    right_y = draw_section(
        c,
        right_x,
        right_y,
        "How it works",
        body_lines=[
            "Electron main creates the window, reads/writes settings, and either launches the local Python backend or uses `YT_DOWNLOADER_API_URL` if one is provided.",
            "The preload script exposes a small IPC bridge (`window.ytApi`) for settings, downloads, progress polling, history, and file/folder actions.",
            "React submits download requests and polls `/progress` every 600 ms; terminal states trigger a history refresh.",
            "Flask exposes `/health`, `/download`, `/progress`, `/cancel`, and `/history`. `DownloadManager` runs `yt-dlp` in a background thread, allows one active job, and keeps up to 20 history items in memory.",
            "Data flow: Renderer -> preload IPC -> Electron main -> Flask API -> `yt-dlp`, then status/history returns back through the same path.",
        ],
    )
    right_y = draw_section(
        c,
        right_x,
        right_y,
        "How to run",
        bullets=[
            "Install prerequisites: Node.js 18+, Python 3.10+, and FFmpeg for MP3 extraction.",
            "FFmpeg install steps: Not found in repo.",
            "Install backend deps: `python -m pip install -r services/downloader/requirements.txt`",
            "Install desktop deps in `apps/desktop`: `npm install`",
            "Start the app from `apps/desktop`: `npm run dev`",
        ],
    )

    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(0.8)
    c.line(MARGIN_X, 56, PAGE_WIDTH - MARGIN_X, 56)
    c.setFillColor(SUBTITLE_COLOR)
    c.setFont("Helvetica", 8.8)
    c.drawString(
        MARGIN_X,
        42,
        "Notes: architecture summary is limited to repo evidence; backend history persistence beyond in-memory state was not found in repo.",
    )

    c.showPage()
    c.save()


def render_preview():
    pdf = pdfium.PdfDocument(PDF_PATH)
    page = pdf[0]
    bitmap = page.render(scale=2.2)
    pil_image = bitmap.to_pil()
    pil_image.save(PNG_PATH)
    page.close()
    pdf.close()


def validate():
    with pdfplumber.open(PDF_PATH) as pdf:
        page_count = len(pdf.pages)
        text = pdf.pages[0].extract_text() or ""
    return page_count, text


if __name__ == "__main__":
    build_pdf()
    render_preview()
    page_count, text = validate()
    print(PDF_PATH)
    print(PNG_PATH)
    print(f"page_count={page_count}")
    print(f"text_chars={len(text)}")
