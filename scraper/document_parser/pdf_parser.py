"""
PDF Parser - Extract text and data from PDF files.
"""
import io
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class PDFPage:
    """A page from a PDF."""
    page_number: int
    text: str
    images: List[str]
    links: List[str]


class PDFParser:
    """
    Extract text, images, and tables from PDF files.
    Supports both local files and URLs.
    """

    def __init__(self):
        self.pypdf_available = self._check("pypdf")
        self.pymupdf_available = self._check("fitz")  # PyMuPDF
        self.pdfplumber_available = self._check("pdfplumber")

    def _check(self, module: str) -> bool:
        try:
            __import__(module)
            return True
        except ImportError:
            return False

    def parse_file(self, filepath: str) -> Dict[str, Any]:
        """Parse a local PDF file."""
        with open(filepath, "rb") as f:
            return self.parse_bytes(f.read())

    def parse_bytes(self, data: bytes) -> Dict[str, Any]:
        """Parse PDF from bytes."""
        pages = []

        # Try pdfplumber (best for tables)
        if self.pdfplumber_available:
            pages = self._parse_pdfplumber(data)
        # Try PyMuPDF
        elif self.pymupdf_available:
            pages = self._parse_pymupdf(data)
        # Try pypdf
        elif self.pypdf_available:
            pages = self._parse_pypdf(data)
        else:
            logger.warning("No PDF library available. Install: pip install pdfplumber")
            return {"error": "No PDF library installed", "pages": []}

        return {
            "page_count": len(pages),
            "pages": pages,
            "full_text": "\n\n".join(p.text for p in pages),
        }

    def parse_url(self, url: str) -> Dict[str, Any]:
        """Parse PDF from URL."""
        try:
            import requests
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return self.parse_bytes(response.content)
        except Exception as e:
            logger.error(f"Failed to download PDF: {e}")
            return {"error": str(e), "pages": []}

    def extract_tables(self, pdf_data: Dict) -> List[List[List[str]]]:
        """Extract tables from PDF."""
        tables = []

        if self.pdfplumber_available:
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(pdf_data.get("raw", b""))) as pdf:
                    for page in pdf.pages:
                        page_tables = page.extract_tables()
                        if page_tables:
                            tables.extend(page_tables)
            except Exception as e:
                logger.debug(f"Table extraction failed: {e}")

        return tables

    def _parse_pdfplumber(self, data: bytes) -> List[PDFPage]:
        """Parse using pdfplumber."""
        import pdfplumber
        pages = []

        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""

                    # Extract images
                    images = []
                    for img in page.images:
                        if "width" in img and "height" in img:
                            images.append({
                                "x": img.get("x0", 0),
                                "y": img.get("top", 0),
                                "width": img.get("width", 0),
                                "height": img.get("height", 0),
                            })

                    pages.append(PDFPage(
                        page_number=i,
                        text=text,
                        images=images,
                        links=[],
                    ))
        except Exception as e:
            logger.error(f"pdfplumber parse failed: {e}")

        return pages

    def _parse_pymupdf(self, data: bytes) -> List[PDFPage]:
        """Parse using PyMuPDF."""
        import fitz  # PyMuPDF
        pages = []

        try:
            doc = fitz.open(stream=data, filetype="pdf")
            for i, page in enumerate(doc, 1):
                text = page.get_text()

                # Extract images
                images = []
                for img_index, img in enumerate(page.get_images(full=True)):
                    xref = img[0]
                    images.append({"index": img_index, "xref": xref})

                # Extract links
                links = []
                for link in page.get_links():
                    if link.get("uri"):
                        links.append(link["uri"])

                pages.append(PDFPage(
                    page_number=i,
                    text=text,
                    images=images,
                    links=links,
                ))
            doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF parse failed: {e}")

        return pages

    def _parse_pypdf(self, data: bytes) -> List[PDFPage]:
        """Parse using pypdf."""
        from pypdf import PdfReader
        pages = []

        try:
            reader = PdfReader(io.BytesIO(data))
            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                pages.append(PDFPage(
                    page_number=i,
                    text=text,
                    images=[],
                    links=[],
                ))
        except Exception as e:
            logger.error(f"pypdf parse failed: {e}")

        return pages


class DocumentConverter:
    """
    Convert documents to text/markdown.
    """

    def __init__(self):
        self.pdf_parser = PDFParser()

    def convert(self, filepath: str = None, url: str = None, data: bytes = None) -> Dict:
        """Convert document to text."""
        if filepath:
            if filepath.endswith(".pdf"):
                return self.pdf_parser.parse_file(filepath)
            elif filepath.endswith(".docx"):
                from .docx_parser import DocxParser
                parser = DocxParser()
                return parser.parse_file(filepath)
        elif url:
            if ".pdf" in url.lower():
                return self.pdf_parser.parse_url(url)
        elif data:
            return self.pdf_parser.parse_bytes(data)

        return {"error": "Unsupported format"}
