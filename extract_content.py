"""
Extract text and images from HTML file with accordion support.
This script parses the HTML and extracts:
- All text content from the page (including accordion content)
- All images (URLs and optional download)
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False


class HTMLContentExtractor:
    def __init__(self, html_file_path, base_url='https://openforis.org/collect-earth-tutorials/'):
        """
        Initialize the extractor.
        
        Args:
            html_file_path: Path to the HTML file
            base_url: Base URL for resolving relative URLs
        """
        self.html_file_path = html_file_path
        self.base_url = base_url
        self.soup = None
        
    def load_html(self):
        """Load and parse the HTML file."""
        with open(self.html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Try to use lxml parser, fall back to html.parser if not available
        try:
            self.soup = BeautifulSoup(html_content, 'lxml')
            parser = 'lxml'
        except:
            self.soup = BeautifulSoup(html_content, 'html.parser')
            parser = 'html.parser'
        
        print(f"✓ Loaded HTML file: {self.html_file_path} (parser: {parser})")
        
    def extract_text(self, output_file='output/extracted_text.txt'):
        """
        Extract all text content from the HTML.
        Focuses on main content areas and accordion sections.
        """
        if not self.soup:
            self.load_html()
        
        # Remove script and style elements
        for script in self.soup(['script', 'style', 'meta', 'link']):
            script.decompose()
        
        # Try to find main content area
        main_content = self.soup.find('main') or self.soup.find('article') or self.soup.find(id='content') or self.soup
        
        # Extract text from accordion panels (Kadence blocks)
        accordion_sections = []
        accordions = main_content.find_all(class_=re.compile('kt-accordion|wp-block-kadence-accordion'))
        
        for accordion in accordions:
            # Find accordion panes/panels
            panes = accordion.find_all(class_=re.compile('wp-block-kadence-pane|kt-accordion-pane'))
            for pane in panes:
                # Get title
                title_elem = pane.find(class_=re.compile('kt-blocks-accordion-header|kt-accordion-title'))
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # Get content
                content_elem = pane.find(class_=re.compile('kt-accordion-panel|kt-accordion-panel-inner'))
                content = content_elem.get_text(separator='\n', strip=True) if content_elem else ''
                
                if title or content:
                    accordion_sections.append({
                        'title': title,
                        'content': content
                    })
        
        # Get all text from main content
        all_text = main_content.get_text(separator='\n', strip=True)
        
        # Clean up multiple newlines
        all_text = re.sub(r'\n{3,}', '\n\n', all_text)
        
        # Create output directory
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("EXTRACTED TEXT CONTENT\n")
            f.write("="*80 + "\n\n")
            f.write(all_text)
            
            if accordion_sections:
                f.write("\n\n" + "="*80 + "\n")
                f.write("ACCORDION SECTIONS (Structured)\n")
                f.write("="*80 + "\n\n")
                for i, section in enumerate(accordion_sections, 1):
                    f.write(f"\n--- Section {i} ---\n")
                    f.write(f"Title: {section['title']}\n")
                    f.write(f"Content:\n{section['content']}\n")
        
        print(f"✓ Extracted text to: {output_file}")
        print(f"  - Found {len(accordion_sections)} accordion sections")
        return all_text, accordion_sections
    
    def extract_images(self, output_file='output/image_urls.json', download=False, download_dir='output/images'):
        """
        Extract all image URLs from the HTML.
        
        Args:
            output_file: Path to save image URLs (JSON format)
            download: Whether to download images
            download_dir: Directory to save downloaded images
        """
        if not self.soup:
            self.load_html()
        
        images = []
        
        # Find all img tags
        img_tags = self.soup.find_all('img')
        
        for img in img_tags:
            img_data = {}
            
            # Get src (main image URL)
            src = img.get('src', '')
            if src:
                img_data['src'] = urljoin(self.base_url, src)
            
            # Get srcset (responsive images)
            srcset = img.get('srcset', '')
            if srcset:
                img_data['srcset'] = srcset
            
            # Get alt text
            alt = img.get('alt', '')
            if alt:
                img_data['alt'] = alt
            
            # Get title
            title = img.get('title', '')
            if title:
                img_data['title'] = title
            
            # Get dimensions
            width = img.get('width', '')
            height = img.get('height', '')
            if width:
                img_data['width'] = width
            if height:
                img_data['height'] = height
            
            if img_data and 'src' in img_data:
                images.append(img_data)
        
        # Also check for background images in style attributes
        elements_with_bg = self.soup.find_all(style=re.compile(r'background.*url'))
        for elem in elements_with_bg:
            style = elem.get('style', '')
            urls = re.findall(r'url\([\'"]?([^\'"()]+)[\'"]?\)', style)
            for url in urls:
                full_url = urljoin(self.base_url, url)
                images.append({
                    'src': full_url,
                    'type': 'background-image'
                })
        
        # Create output directory
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        
        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(images, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Extracted {len(images)} images to: {output_file}")
        
        # Download images if requested
        if download and images:
            os.makedirs(download_dir, exist_ok=True)
            print(f"\nDownloading images to: {download_dir}")
            
            downloaded = 0
            for i, img in enumerate(images, 1):
                src = img.get('src', '')
                if src and src.startswith('http'):
                    try:
                        # Generate filename from URL
                        parsed = urlparse(src)
                        filename = os.path.basename(parsed.path)
                        if not filename:
                            filename = f'image_{i}.jpg'
                        
                        filepath = os.path.join(download_dir, filename)
                        
                        # Download
                        response = requests.get(src, timeout=10)
                        response.raise_for_status()
                        
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        
                        downloaded += 1
                        print(f"  [{i}/{len(images)}] Downloaded: {filename}")
                    except Exception as e:
                        print(f"  [{i}/{len(images)}] Failed: {src} - {str(e)}")
            
            print(f"\n✓ Downloaded {downloaded}/{len(images)} images")
        
        return images
    
    def extract_markdown(self, output_file='output/extracted_content.md'):
        """
        Extract content in Markdown format.
        Preserves formatting like headings, bold, italic, links, lists, etc.
        """
        if not HTML2TEXT_AVAILABLE:
            print("⚠ Warning: html2text not installed. Install with: pip install html2text")
            print("  Falling back to plain text extraction.")
            return self.extract_text(output_file.replace('.md', '.txt'))
        
        if not self.soup:
            self.load_html()
        
        # Remove script and style elements
        for script in self.soup(['script', 'style', 'meta', 'link', 'noscript']):
            script.decompose()
        
        # Find main content
        main_content = self.soup.find('main') or self.soup.find('article') or self.soup.find(id='content') or self.soup
        
        # Configure html2text
        h = html2text.HTML2Text()
        h.body_width = 0  # Don't wrap lines
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_emphasis = False
        h.skip_internal_links = False
        h.inline_links = True
        h.protect_links = True
        h.unicode_snob = True
        
        # Convert to Markdown
        markdown_content = h.handle(str(main_content))
        
        # Clean up excessive newlines
        markdown_content = re.sub(r'\n{4,}', '\n\n\n', markdown_content)
        
        # Create output directory
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Collect Earth Tutorials - OpenForis\n\n")
            f.write("*Extracted content in Markdown format*\n\n")
            f.write("---\n\n")
            f.write(markdown_content)
        
        print(f"✓ Extracted Markdown to: {output_file}")
        return markdown_content
    
    def extract_all(self, text_output='output/extracted_text.txt', 
                    images_output='output/image_urls.json',
                    download_images=False,
                    markdown_output='output/extracted_content.md'):
        """
        Extract both text and images.
        """
        print("\n" + "="*80)
        print("EXTRACTING CONTENT FROM HTML")
        print("="*80 + "\n")
        
        self.load_html()
        
        # Extract text
        text, accordions = self.extract_text(text_output)
        
        # Extract Markdown
        markdown = None
        if HTML2TEXT_AVAILABLE and markdown_output:
            markdown = self.extract_markdown(markdown_output)
        
        # Extract images
        images = self.extract_images(images_output, download=download_images)
        
        print("\n" + "="*80)
        print("EXTRACTION COMPLETE")
        print("="*80)
        print(f"\nSummary:")
        print(f"  - Text output: {text_output}")
        if markdown_output and HTML2TEXT_AVAILABLE:
            print(f"  - Markdown output: {markdown_output}")
        print(f"  - Images found: {len(images)}")
        print(f"  - Accordion sections: {len(accordions)}")
        
        return {
            'text': text,
            'accordions': accordions,
            'images': images
        }


def main():
    """Main function to run the extraction."""
    
    # Configuration
    HTML_FILE = 'input/openforis_website_html.txt'
    TEXT_OUTPUT = 'output/extracted_text.txt'
    MARKDOWN_OUTPUT = 'output/extracted_content.md'
    IMAGES_OUTPUT = 'output/image_urls.json'
    DOWNLOAD_IMAGES = False  # Set to True to download images
    
    # Check if input file exists
    if not os.path.exists(HTML_FILE):
        print(f"Error: HTML file not found: {HTML_FILE}")
        return
    
    # Create extractor and run
    extractor = HTMLContentExtractor(HTML_FILE)
    results = extractor.extract_all(
        text_output=TEXT_OUTPUT,
        markdown_output=MARKDOWN_OUTPUT,
        images_output=IMAGES_OUTPUT,
        download_images=DOWNLOAD_IMAGES
    )
    
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
