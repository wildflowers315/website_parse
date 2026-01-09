# OpenForis Content Extractor & PDF Generator

Extract text and images from the OpenForis Collect Earth Tutorials website and generate a well-formatted PDF that preserves the original content order.

## Features

- **Text Extraction**: Extracts all text content from HTML, including accordion sections
- **Markdown Extraction**: Converts HTML to Markdown format preserving formatting (NEW!)
- **Image Cataloging**: Catalogs all images with URLs, alt text, and dimensions
- **Order-Preserving PDF**: Generates PDF with images placed correctly alongside their related text
- **Markdown Rendering**: Supports bold, italic, code, and links in PDF output (NEW!)
- **Parallel Downloads**: Uses multithreading (8 workers) for fast image downloads
- **Progress Tracking**: Real-time progress bars for all operations
- **Encoding Safety**: Handles special characters and non-Latin text

## Quick Start

### Option 1: Using uv (Recommended - Fast)

```bash
# Run the setup script
setup_env.bat     # On Windows
# or
./setup_env.sh    # On Linux/Mac

# Activate the virtual environment
.venv\Scripts\activate    # On Windows
# or
source .venv/bin/activate # On Linux/Mac

# Run the extraction
python extract_content.py
```

### Option 2: Manual Setup with uv

```bash
# Install uv (if not already installed)
pip install uv

# Create virtual environment
uv venv

# Activate virtual environment
.venv\Scripts\activate    # On Windows
source .venv/bin/activate # On Linux/Mac

# Install dependencies
uv pip install -r requirements.txt

# Run the extraction
python extract_content.py
```

### Option 3: Traditional pip

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate    # On Windows
source .venv/bin/activate # On Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run the extraction
python extract_content.py
```

## What It Does

### Content Extraction (`extract_content.py`)

- **Extracts all text content** from the HTML file, including accordion sections
- **Catalogs all images** with URLs, alt text, and dimensions
- **Converts to Markdown** preserving headings, bold, italic, links, lists, code
- **Handles Kadence accordion blocks** specifically
- **Optionally downloads images** (set `DOWNLOAD_IMAGES = True` in the script)

### PDF Generation (`generate_pdf.py`)

- **Preserves content order** by walking the HTML DOM structure
- **Embeds images** next to their related text content
- **Renders Markdown formatting** (bold, italic, code, links) with proper styling
- **Parallel image downloads** using ThreadPoolExecutor (8 workers by default)
- **Progress tracking** with tqdm for all stages (parsing, downloading, rendering)
- **Encoding-safe** using core fonts and fallback to Latin-1
- **Custom styling** with headers, footers, and appropriate text formatting

### Markdown PDF Generation (`generate_pdf_from_markdown.py`) - NEW!

- **Generates PDF from Markdown** file for better readability
- **Reuses cached images** (no re-downloading if already exists)
- **Proper Markdown rendering**: headings, lists, bold, italic, code, blockquotes
- **Faster generation** due to image caching
- **Clean formatting** with appropriate spacing and indentation
- **Code blocks** rendered in monospace with background
- **Parallel downloads** only for missing images

## Output Files

- `output/extracted_text.txt` - All text content including accordion sections
- `output/extracted_content.md` - **Markdown formatted content** (NEW!)
- `output/image_urls.json` - JSON file with all image metadata
- `output/openforis_content.pdf` - PDF from HTML (preserves DOM order)
- `output/openforis_markdown.pdf` - **PDF from Markdown (better formatting, faster)** (NEW!)
- `output/images/` - Downloaded images (cached for reuse)

## Configuration

### extract_content.py

Edit to customize extraction behavior:

```python
HTML_FILE = 'input/openforis_website_html.txt'  # Input HTML file
TEXT_OUTPUT = 'output/extracted_text.txt'       # Text output file
MARKDOWN_OUTPUT = 'output/extracted_content.md' # Markdown output file
IMAGES_OUTPUT = 'output/image_urls.json'        # Image metadata file
DOWNLOAD_IMAGES = False                         # Set to True to download images
```

### generate_pdf.py (HTML → PDF)

Generates PDF by walking HTML DOM:

```python
HTML_FILE = "input/openforis_website_html.txt"
OUTPUT_PDF = "output/openforis_content.pdf"
# In prepare_images() call, adjust max_workers for download speed
builder.prepare_images(max_workers=8)  # Default: 8 parallel downloads
```

### generate_pdf_from_markdown.py (Markdown → PDF) - RECOMMENDED

Generates PDF from Markdown with image caching:

```python
MARKDOWN_FILE = "output/extracted_content.md"
OUTPUT_PDF = "output/openforis_markdown.pdf"
IMAGES_DIR = "output/images"  # Reuses cached images
# Adjust max_workers in MarkdownPDFGenerator constructor
generator = MarkdownPDFGenerator(max_workers=8)  # Only downloads missing images
```

## Performance

### HTML → PDF (`generate_pdf.py`)
- **Image Downloads**: ~7.7x faster with parallel downloads (8 workers)
  - Sequential: ~161 seconds
  - Parallel: ~21 seconds
- **PDF Generation**: ~3-4 seconds for 800+ content blocks
- **Total Runtime**: ~25-30 seconds for complete PDF generation

### Markdown → PDF (`generate_pdf_from_markdown.py`) - FASTER!
- **Image Downloads**: Only downloads missing images
  - Cached images: instant (0 seconds)
  - Missing images: ~22 seconds (8 workers)
- **PDF Generation**: ~2-3 seconds for 1400+ lines
- **Total Runtime**: ~25 seconds first run, ~5 seconds subsequent runs (with cache)
- **Recommended workflow**: Use this for cleaner formatting and faster regeneration

## Requirements

- Python 3.8+
- beautifulsoup4
- requests
- lxml (platform-dependent)
- fpdf2
- Pillow
- tqdm
- html2text (for Markdown extraction)

See `requirements.txt` for specific versions.

## Advanced Usage

### Choosing the Right PDF Generator

**For most users, use `generate_pdf_from_markdown.py`** - it's faster, has better formatting, and reuses cached images.

See [PDF_COMPARISON.md](PDF_COMPARISON.md) for a detailed comparison of both approaches.

### Markdown Extraction & Styling

For detailed information about Markdown extraction and PDF styling, see [MARKDOWN_GUIDE.md](MARKDOWN_GUIDE.md).

**Quick example:**
- HTML: `<strong>bold</strong>` → Markdown: `**bold**` → PDF: **bold font**
- HTML: `<em>italic</em>` → Markdown: `*italic*` → PDF: *italic font*
- HTML: `<code>code</code>` → Markdown: `` `code` `` → PDF: `monospace font`
- HTML: `<a href="url">link</a>` → Markdown: `[link](url)` → PDF: blue text


C:/Users/ISHIKAWATA/website_parse/.venv/Scripts/uv.exe pip install -r requirements.txt