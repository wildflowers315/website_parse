"""
Generate a PDF from the extracted HTML while preserving the order of text and images.
- Walks the HTML in DOM order to keep images near their corresponding text.
- Downloads images and embeds them in the PDF.
- Uses only core fonts to avoid platform issues.
"""

import os
import json
import hashlib
import re
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from fpdf import FPDF
from tqdm import tqdm


def _hash_url(url: str) -> str:
    """Create a stable filename from a URL."""
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def _safe(text: str) -> str:
    """Best-effort ASCII/latin-1 fallback to avoid font issues."""
    return text.encode("latin-1", "replace").decode("latin-1")


def _parse_markdown_inline(text: str) -> list:
    """
    Parse inline Markdown formatting and return segments with styles.
    Returns list of tuples: (text, style_dict)
    Supports: **bold**, *italic*, `code`, [links](url)
    """
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
            match = re.match(r'\[([^\]]+)\]\(([^\)]+)\)', text[i:])
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


class ContentPDF(FPDF):
    """Custom PDF with simple header/footer."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("helvetica", "B", 12)
        self.cell(0, 10, _safe("Collect Earth Tutorials - OpenForis"), 0, 1, "C")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")


class PDFBuilder:
    """Build a PDF from HTML while preserving content order."""

    def __init__(self, html_file: str, output_pdf: str = "output/openforis_content.pdf",
                 base_url: str = "https://openforis.org/collect-earth-tutorials/",
                 images_dir: str = "output/images"):
        self.html_file = html_file
        self.output_pdf = output_pdf
        self.base_url = base_url
        self.images_dir = images_dir
        self.blocks = []  # Ordered list of content blocks
        self.downloaded_images = {}

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def load_blocks(self):
        """Parse HTML and build an ordered list of blocks (text, headings, images)."""
        if not os.path.exists(self.html_file):
            raise FileNotFoundError(f"HTML file not found: {self.html_file}")

        with open(self.html_file, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        for bad in tqdm(soup.find_all(["script", "style", "noscript", "meta", "link"]), desc="Cleaning HTML", unit="tag"):
            bad.decompose()

        main = soup.find("main") or soup.find("article") or soup.find(id="content") or soup.body or soup

        self.blocks = self._walk(main)
        return self.blocks

    def _walk(self, node) -> list:
        """Recursively walk the DOM and produce ordered blocks."""
        blocks = []
        buffer = []

        def flush_buffer():
            text = " ".join(" ".join(buffer).split())
            if text:
                blocks.append({"type": "paragraph", "text": text})
            buffer.clear()

        for child in node.children: # superfast process
            if isinstance(child, NavigableString):
                txt = " ".join(child.strip().split())
                if txt:
                    buffer.append(txt)
            elif isinstance(child, Tag):
                name = child.name.lower()

                if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                    flush_buffer()
                    blocks.append({
                        "type": "heading",
                        "level": int(name[1]),
                        "text": child.get_text(" ", strip=True),
                    })

                elif name == "img":
                    flush_buffer()
                    src = child.get("src") or ""
                    if src:
                        blocks.append({
                            "type": "image",
                            "src": urljoin(self.base_url, src),
                            "alt": child.get("alt", ""),
                        })

                elif name in {"ul", "ol"}:
                    flush_buffer()
                    ordered = name == "ol"
                    for li in child.find_all("li", recursive=False):
                        li_blocks = self._walk(li)
                        for b in li_blocks:
                            if b.get("type") == "paragraph":
                                b = {"type": "list", "ordered": ordered, "text": b["text"]}
                            blocks.append(b)

                elif name == "br":
                    buffer.append("\n")

                else:
                    nested = self._walk(child)
                    blocks.extend(nested)

        flush_buffer()
        return blocks

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    def _download_image(self, url: str) -> str | None:
        """Download image if not already cached; return local path or None."""
        os.makedirs(self.images_dir, exist_ok=True)
        fname = _hash_url(url)
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1] or ".jpg"
        fname = f"{fname}{ext}"
        local_path = os.path.join(self.images_dir, fname)

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

    def prepare_images(self, max_workers: int = 8):
        """Download all images referenced in blocks (with caching) using parallel downloads."""
        # Collect unique image URLs
        image_urls = []
        for blk in self.blocks:
            if blk.get("type") == "image":
                url = blk.get("src", "")
                if url and url not in self.downloaded_images:
                    image_urls.append(url)
        
        if not image_urls:
            return
        
        # Download images in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_url = {executor.submit(self._download_image, url): url for url in image_urls}
            
            # Process completed downloads with progress bar
            for future in tqdm(as_completed(future_to_url), total=len(image_urls), desc="Preparing images", unit="image"):
                url = future_to_url[future]
                try:
                    path = future.result()
                    if path:
                        self.downloaded_images[url] = path
                except Exception:
                    pass  # Already handled in _download_image

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render_heading(self, pdf: ContentPDF, text: str, level: int):
        sizes = {1: 18, 2: 16, 3: 14, 4: 12, 5: 11, 6: 10}
        pdf.set_font("helvetica", "B", sizes.get(level, 11))
        pdf.multi_cell(0, 8, _safe(text))
        pdf.ln(2)

    def _render_paragraph(self, pdf: ContentPDF, text: str):
        """Render paragraph with Markdown inline formatting support."""
        segments = _parse_markdown_inline(text)
        
        # Check if we need to render with formatting
        has_formatting = any(style for _, style in segments if style)
        
        if not has_formatting:
            # Simple case: no formatting
            pdf.set_font("helvetica", "", 11)
            pdf.multi_cell(0, 6, _safe(text))
            pdf.ln(1)
            return
        
        # Complex case: render each segment with its own style
        pdf.set_font("helvetica", "", 11)
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        for seg_text, style in segments:
            if not seg_text:
                continue
            
            # Determine font style
            font_style = ""
            if style.get('bold'):
                font_style = "B"
            elif style.get('italic'):
                font_style = "I"
            elif style.get('code'):
                font_style = ""
            
            # Set font
            if style.get('code'):
                pdf.set_font("courier", "", 10)
            else:
                pdf.set_font("helvetica", font_style, 11)
            
            # Set color for links
            if style.get('link'):
                pdf.set_text_color(0, 0, 255)  # Blue for links
            
            # Write text
            pdf.write(6, _safe(seg_text))
            
            # Reset color
            if style.get('link'):
                pdf.set_text_color(0, 0, 0)  # Reset to black
        
        pdf.ln(7)  # Move to next line after paragraph

    def _render_list(self, pdf: ContentPDF, text: str, ordered: bool, idx: int):
        """Render list item with Markdown inline formatting support."""
        bullet = f"{idx}. " if ordered else "• "
        
        segments = _parse_markdown_inline(text)
        has_formatting = any(style for _, style in segments if style)
        
        if not has_formatting:
            # Simple case
            pdf.set_font("helvetica", "", 11)
            pdf.multi_cell(0, 6, _safe(f"{bullet}{text}"))
            pdf.ln(1)
            return
        
        # Complex case: render bullet then formatted text
        pdf.set_font("helvetica", "", 11)
        pdf.write(6, _safe(bullet))
        
        for seg_text, style in segments:
            if not seg_text:
                continue
            
            font_style = ""
            if style.get('bold'):
                font_style = "B"
            elif style.get('italic'):
                font_style = "I"
            
            if style.get('code'):
                pdf.set_font("courier", "", 10)
            else:
                pdf.set_font("helvetica", font_style, 11)
            
            if style.get('link'):
                pdf.set_text_color(0, 0, 255)
            
            pdf.write(6, _safe(seg_text))
            
            if style.get('link'):
                pdf.set_text_color(0, 0, 0)
        
        pdf.ln(7)

    def _render_image(self, pdf: ContentPDF, path: str, alt: str | None = None):
        if not path or not os.path.exists(path):
            return
        if alt:
            pdf.set_font("helvetica", "I", 9)
            pdf.multi_cell(0, 5, _safe(alt[:120]))
        try:
            pdf.image(path, x=10, w=190)
            pdf.ln(4)
        except Exception:
            if alt:
                pdf.set_font("helvetica", "", 8)
                pdf.multi_cell(0, 5, _safe(f"[Image could not be embedded: {alt[:80]}]"))

    def build_pdf(self):
        """Generate the PDF file."""
        if not self.blocks:
            self.load_blocks()
        self.prepare_images()

        pdf = ContentPDF()
        pdf.add_page()

        # Title page
        pdf.set_font("helvetica", "B", 20)
        pdf.cell(0, 20, _safe("Collect Earth Tutorials"), 0, 1, "C")
        pdf.set_font("helvetica", "", 14)
        pdf.cell(0, 10, _safe("OpenForis extracted content"), 0, 1, "C")
        pdf.ln(10)

        # Render blocks in order
        list_counter = 1
        for blk in tqdm(self.blocks, desc="Building PDF", unit="block"):
            btype = blk.get("type")
            if btype == "heading":
                self._render_heading(pdf, blk.get("text", ""), blk.get("level", 3))
                list_counter = 1
            elif btype == "paragraph":
                self._render_paragraph(pdf, blk.get("text", ""))
            elif btype == "list":
                self._render_list(pdf, blk.get("text", ""), blk.get("ordered", False), list_counter if blk.get("ordered") else 0)
                if blk.get("ordered"):
                    list_counter += 1
            elif btype == "image":
                url = blk.get("src", "")
                alt = blk.get("alt", "")
                path = self.downloaded_images.get(url)
                self._render_image(pdf, path, alt)

        os.makedirs(os.path.dirname(self.output_pdf) or ".", exist_ok=True)
        pdf.output(self.output_pdf)
        size_kb = os.path.getsize(self.output_pdf) / 1024
        print(f"\n✅ PDF created: {self.output_pdf} ({size_kb:.1f} KB)")


def main():
    print("=" * 80)
    print("ORDER-PRESERVING PDF GENERATION")
    print("=" * 80 + "\n")

    HTML_FILE = "input/openforis_website_html.txt"
    OUTPUT_PDF = "output/openforis_content.pdf"

    builder = PDFBuilder(html_file=HTML_FILE, output_pdf=OUTPUT_PDF)
    builder.load_blocks()
    builder.build_pdf()

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()
