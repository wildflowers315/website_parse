# OpenForis Content Extractor & PDF Generator

Extract text and images from the OpenForis Collect Earth Tutorials website and generate a well-formatted PDF that preserves the original content order.

## Features

- **Text Extraction**: Extracts all text content from HTML, including accordion sections
- **Image Cataloging**: Catalogs all images with URLs, alt text, and dimensions
- **Order-Preserving PDF**: Generates PDF with images placed correctly alongside their related text
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
- **Handles Kadence accordion blocks** specifically
- **Optionally downloads images** (set `DOWNLOAD_IMAGES = True` in the script)

### PDF Generation (`generate_pdf.py`)

- **Preserves content order** by walking the HTML DOM structure
- **Embeds images** next to their related text content
- **Parallel image downloads** using ThreadPoolExecutor (8 workers by default)
- **Progress tracking** with tqdm for all stages (parsing, downloading, rendering)
- **Encoding-safe** using core fonts and fallback to Latin-1
- **Custom styling** with headers, footers, and appropriate text formatting

## Output Files

- `output/extracted_text.txt` - All text content including accordion sections
- `output/image_urls.json` - JSON file with all image metadata
- `output/openforis_content.pdf` - **Complete PDF with text and images in original order**
- `output/images/` - Downloaded images (cached for reuse)

## Configuration

### extract_content.py

Edit to customize extraction behavior:

```python
HTML_FILE = 'input/openforis_website_html.txt'  # Input HTML file
TEXT_OUTPUT = 'output/extracted_text.txt'       # Text output file
IMAGES_OUTPUT = 'output/image_urls.json'        # Image metadata file
DOWNLOAD_IMAGES = False                         # Set to True to download images
```

### generate_pdf.py

Edit to customize PDF generation:

```python
HTML_FILE = "input/openforis_website_html.txt"
OUTPUT_PDF = "output/openforis_content.pdf"
# In prepare_images() call, adjust max_workers for download speed
builder.prepare_images(max_workers=8)  # Default: 8 parallel downloads
```

## Performance

- **Image Downloads**: ~7.7x faster with parallel downloads (8 workers)
  - Sequential: ~161 seconds
  - Parallel: ~21 seconds
- **PDF Generation**: ~3-4 seconds for 800+ content blocks
- **Total Runtime**: ~25-30 seconds for complete PDF generation

## Requirements

- Python 3.8+
- beautifulsoup4
- requests
- lxml (platform-dependent)
- fpdf2
- Pillow
- tqdm

See `requirements.txt` for specific versions.


C:/Users/ISHIKAWATA/website_parse/.venv/Scripts/uv.exe pip install -r requirements.txt