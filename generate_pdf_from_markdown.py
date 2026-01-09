"""
Generate a PDF from Markdown file with proper formatting.
- Parses Markdown syntax for headings, lists, bold, italic, code, links
- Embeds images (reuses already downloaded images)
- Maintains readable formatting with proper spacing
"""

import os
import re
import hashlib
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from fpdf import FPDF
from tqdm import tqdm


def _hash_url(url: str) -> str:
    """Create a stable filename from a URL."""
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def _safe(text: str) -> str:
    """Best-effort ASCII/latin-1 fallback to avoid font issues."""
    return text.encode("latin-1", "replace").decode("latin-1")


class MarkdownPDF(FPDF):
    """Custom PDF with header/footer for Markdown content."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("helvetica", "B", 12)
        self.cell(0, 10, _safe("Collect Earth Tutorials - OpenForis"), align="C")
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


class MarkdownPDFGenerator:
    """Generate PDF from Markdown file."""

    def __init__(self, markdown_file: str, output_pdf: str = "output/openforis_markdown.pdf",
                 images_dir: str = "output/images", max_workers: int = 8):
        self.markdown_file = markdown_file
        self.output_pdf = output_pdf
        self.images_dir = images_dir
        self.max_workers = max_workers
        self.downloaded_images = {}
        self.lines = []

    def load_markdown(self):
        """Load and parse Markdown file."""
        if not os.path.exists(self.markdown_file):
            raise FileNotFoundError(f"Markdown file not found: {self.markdown_file}")

        with open(self.markdown_file, "r", encoding="utf-8") as f:
            self.lines = f.readlines()
        
        print(f"✓ Loaded Markdown file: {self.markdown_file} ({len(self.lines)} lines)")
        return self.lines

    def _download_image(self, url: str) -> str | None:
        """Download image if not already cached; return local path or None."""
        os.makedirs(self.images_dir, exist_ok=True)
        fname = _hash_url(url)
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1] or ".jpg"
        fname = f"{fname}{ext}"
        local_path = os.path.join(self.images_dir, fname)

        # Check if already exists
        if os.path.exists(local_path):
            return local_path

        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(resp.content)
            return local_path
        except Exception:
            return None

    def prepare_images(self):
        """Extract and download images from Markdown (with caching)."""
        # Extract image URLs from Markdown: ![alt](url) or ![alt](<url>)
        image_pattern = re.compile(r'!\[([^\]]*)\]\(\s*<?([^\s>\)]+)>?\s*\)')
        image_urls = []
        for line in self.lines:
            for alt, url in image_pattern.findall(line):
                if url and url.startswith('http') and url not in self.downloaded_images:
                    image_urls.append(url)
        
        if not image_urls:
            print("✓ No images to download")
            return
        
        # Check which images are already downloaded
        already_cached = []
        to_download = []
        
        for url in image_urls:
            fname = _hash_url(url)
            parsed = urlparse(url)
            ext = os.path.splitext(parsed.path)[1] or ".jpg"
            local_path = os.path.join(self.images_dir, f"{fname}{ext}")
            
            if os.path.exists(local_path):
                self.downloaded_images[url] = local_path
                already_cached.append(url)
            else:
                to_download.append(url)
        
        print(f"✓ Images: {len(already_cached)} cached, {len(to_download)} to download")
        
        if not to_download:
            return
        
        # Download missing images in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self._download_image, url): url for url in to_download}
            
            for future in tqdm(as_completed(future_to_url), total=len(to_download), 
                             desc="Downloading images", unit="image"):
                url = future_to_url[future]
                try:
                    path = future.result()
                    if path:
                        self.downloaded_images[url] = path
                except Exception:
                    pass

    def _parse_inline_formatting(self, text: str) -> list:
        """Parse inline Markdown and return segments with styles (stores link URLs)."""
        segments = []
        i = 0
        current_text = ""
        
        while i < len(text):
            # Bold: **text**
            if text[i:i+2] == '**':
                if current_text:
                    segments.append((current_text, {}))
                    current_text = ""
                end = text.find('**', i+2)
                if end != -1:
                    segments.append((text[i+2:end], {'bold': True}))
                    i = end + 2
                    continue
            
            # Italic: *text* (but not **)
            elif text[i] == '*' and (i == 0 or text[i-1:i+1] != '**') and (i+1 >= len(text) or text[i:i+2] != '**'):
                if current_text:
                    segments.append((current_text, {}))
                    current_text = ""
                end = i + 1
                while end < len(text) and text[end] != '*':
                    end += 1
                if end < len(text):
                    segments.append((text[i+1:end], {'italic': True}))
                    i = end + 1
                    continue
            
            # Code: `text`
            elif text[i] == '`':
                if current_text:
                    segments.append((current_text, {}))
                    current_text = ""
                end = text.find('`', i+1)
                if end != -1:
                    segments.append((text[i+1:end], {'code': True}))
                    i = end + 1
                    continue
            
            # Links: [text](url)
            elif text[i] == '[':
                match = re.match(r'\[([^\]]+)\]\(\s*<?([^\s>\)]+)>?\s*\)', text[i:])
                if match:
                    if current_text:
                        segments.append((current_text, {}))
                        current_text = ""
                    link_text = match.group(1)
                    link_url = match.group(2)
                    segments.append((link_text, {'link': link_url}))
                    i += len(match.group(0))
                    continue
            
            current_text += text[i]
            i += 1
        
        if current_text:
            segments.append((current_text, {}))
        
        return segments if segments else [(text, {})]

    def _render_formatted_text(self, pdf: MarkdownPDF, text: str, base_size: int = 11):
        """Render text with inline formatting."""
        segments = self._parse_inline_formatting(text)
        
        for seg_text, style in segments:
            if not seg_text:
                continue
            
            font_style = ""
            font_size = base_size
            
            if style.get('bold'):
                font_style = "B"
            elif style.get('italic'):
                font_style = "I"
            
            if style.get('code'):
                pdf.set_font("courier", "", font_size - 1)
                pdf.set_fill_color(240, 240, 240)
            else:
                pdf.set_font("helvetica", font_style, font_size)
                pdf.set_fill_color(255, 255, 255)
            
            link_target = None
            if style.get('link'):
                href = style['link']
                # Ignore internal anchors (e.g., #section) to avoid missing PDF destinations
                if href.startswith('#'):
                    pdf.set_text_color(0, 0, 0)
                else:
                    link_target = href
                    pdf.set_text_color(0, 0, 255)
            else:
                pdf.set_text_color(0, 0, 0)
            pdf.write(6, _safe(seg_text), link=link_target)

    def generate_pdf(self):
        """Generate PDF from Markdown."""
        if not self.lines:
            self.load_markdown()
        
        self.prepare_images()
        
        pdf = MarkdownPDF()
        pdf.add_page()
        
        in_code_block = False
        list_level = 0
        
        print("Generating PDF from Markdown...")
        
        for line in tqdm(self.lines, desc="Processing", unit="line"):
            line = line.rstrip('\n')
            
            # Skip front matter separator
            if line.strip() == '---':
                continue
            
            # Code blocks: ```
            if line.startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                pdf.set_font("courier", "", 9)
                pdf.set_fill_color(245, 245, 245)
                pdf.multi_cell(0, 5, _safe(line), fill=True)
                continue
            
            # Empty line
            if not line.strip():
                pdf.ln(2)
                continue
            
            # Heading: # ## ### etc.
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2)
                sizes = {1: 20, 2: 18, 3: 16, 4: 14, 5: 12, 6: 11}
                
                pdf.ln(3)
                pdf.set_font("helvetica", "B", sizes.get(level, 12))
                pdf.multi_cell(0, 8, _safe(text))
                pdf.ln(2)
                continue
            
            # Images: support multiple images on the same line if the line is image-only
            image_pattern = re.compile(r'!\[([^\]]*)\]\(\s*<?([^\s>\)]+)>?\s*\)')
            image_matches = image_pattern.findall(line)
            if image_matches and image_pattern.sub('', line).strip() == '':
                for alt, url in image_matches:
                    if alt:
                        pdf.set_font("helvetica", "I", 9)
                        pdf.multi_cell(0, 5, _safe(alt[:120]))

                    path = self.downloaded_images.get(url)
                    if path and os.path.exists(path):
                        try:
                            pdf.image(path, x=10, w=190)
                        except Exception:
                            pdf.set_font("helvetica", "", 8)
                            pdf.multi_cell(0, 5, _safe(f"[Image not available: {alt or url[:50]}]"))
                    pdf.ln(4)
                continue
            
            # Unordered list: - or * or •
            list_match = re.match(r'^(\s*)[-*•]\s+(.+)$', line)
            if list_match:
                indent = len(list_match.group(1))
                text = list_match.group(2)
                
                pdf.set_x(10 + indent * 2)
                pdf.set_font("helvetica", "", 11)
                pdf.write(6, _safe("• "))
                self._render_formatted_text(pdf, text)
                pdf.ln(6)
                continue
            
            # Ordered list: 1. 2. etc.
            ordered_list_match = re.match(r'^(\s*)(\d+)\.\s+(.+)$', line)
            if ordered_list_match:
                indent = len(ordered_list_match.group(1))
                number = ordered_list_match.group(2)
                text = ordered_list_match.group(3)
                
                pdf.set_x(10 + indent * 2)
                pdf.set_font("helvetica", "", 11)
                pdf.write(6, _safe(f"{number}. "))
                self._render_formatted_text(pdf, text)
                pdf.ln(6)
                continue
            
            # Blockquote: >
            if line.startswith('>'):
                text = line[1:].strip()
                pdf.set_font("helvetica", "I", 10)
                pdf.set_fill_color(250, 250, 250)
                pdf.set_x(15)
                pdf.multi_cell(0, 6, _safe(text), fill=True)
                pdf.ln(2)
                continue
            
            # Horizontal rule: --- or ***
            if re.match(r'^(\*{3,}|-{3,}|_{3,})$', line.strip()):
                pdf.ln(2)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)
                continue

            # Simple table rows: detect pipes with at least 2 columns
            if '|' in line and not line.strip().startswith('http'):
                # Ignore separator rows like |---|
                if re.match(r'^\s*\|?\s*:?[- ]+:?\s*(\|\s*:?[- ]+:?\s*)+\|?\s*$', line):
                    continue
                # Split columns and strip
                cols = [c.strip() for c in line.strip().strip('|').split('|')]
                if len(cols) >= 2:
                    pdf.set_font("helvetica", "", 9)
                    available_w = 190
                    col_w = available_w / len(cols)
                    line_h = 5
                    # Measure required height for each cell (dry run)
                    cell_heights = []
                    for col in cols:
                        lines = pdf.multi_cell(col_w, line_h, _safe(col), dry_run=True, output="LINES")
                        cell_heights.append(len(lines) * line_h)
                    row_h = max(cell_heights) if cell_heights else line_h

                    y_start = pdf.get_y()
                    x_start = 10
                    for i, col in enumerate(cols):
                        pdf.set_xy(x_start + i * col_w, y_start)
                        pdf.multi_cell(col_w, line_h, _safe(col), border=1, new_x="RIGHT", new_y="TOP")
                    # Move to the next line at the end of the row
                    pdf.set_xy(10, y_start + row_h)
                    continue
            
            # Regular paragraph
            pdf.set_font("helvetica", "", 11)
            self._render_formatted_text(pdf, line)
            pdf.ln(6)
        
        # Save PDF
        os.makedirs(os.path.dirname(self.output_pdf) or ".", exist_ok=True)
        pdf.output(self.output_pdf)
        
        size_kb = os.path.getsize(self.output_pdf) / 1024
        print(f"\n✅ PDF created: {self.output_pdf} ({size_kb:.1f} KB)")
        print(f"   Total images embedded: {len(self.downloaded_images)}")


def main():
    print("=" * 80)
    print("MARKDOWN TO PDF CONVERSION")
    print("=" * 80 + "\n")

    MARKDOWN_FILE = "output/extracted_content.md"
    OUTPUT_PDF = "output/openforis_markdown.pdf"
    IMAGES_DIR = "output/images"

    if not os.path.exists(MARKDOWN_FILE):
        print(f"❌ Error: Markdown file not found: {MARKDOWN_FILE}")
        print("   Run 'python extract_content.py' first to generate the Markdown file.")
        return

    generator = MarkdownPDFGenerator(
        markdown_file=MARKDOWN_FILE,
        output_pdf=OUTPUT_PDF,
        images_dir=IMAGES_DIR,
        max_workers=8
    )
    
    generator.generate_pdf()

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()
