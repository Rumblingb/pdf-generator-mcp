#!/usr/bin/env python3
"""PDF Generator MCP — Generate PDFs from HTML, text, or URLs."""

import json, base64, io, os, re, tempfile
from mcp.server import Server, stdio_server
import httpx

server = Server("pdf-generator-mcp")

def _html_to_pdf(html):
    """Convert HTML to PDF bytes using fpdf2's HTML support."""
    from fpdf import FPDF
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Simple HTML parsing for fpdf2
    # Strip tags and add content
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Split into lines and add
    pdf.set_font("Helvetica", size=12)
    for line in text.split('\n'):
        line = line.strip()
        if line:
            pdf.multi_cell(0, 10, line)
    
    return pdf.output(dest='S').encode('latin-1', errors='replace')

@server.tool(
    name="pdf_generate_from_html",
    description="Generate a PDF from HTML content",
    input_schema={
        "type": "object",
        "properties": {
            "html_content": {"type": "string", "description": "HTML content to convert to PDF"},
            "filename": {"type": "string", "description": "Output filename (optional)", "default": "output.pdf"}
        },
        "required": ["html_content"]
    }
)
async def pdf_generate_from_html(html_content: str, filename: str = "output.pdf") -> str:
    try:
        pdf_bytes = _html_to_pdf(html_content)
        b64 = base64.b64encode(pdf_bytes).decode()
        return json.dumps({
            "filename": filename,
            "size_bytes": len(pdf_bytes),
            "base64": b64,
            "mime_type": "application/pdf"
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "isError": True}, indent=2)

@server.tool(
    name="pdf_generate_from_text",
    description="Generate a PDF from plain text",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text content"},
            "filename": {"type": "string", "default": "output.pdf"},
            "font_size": {"type": "integer", "default": 12}
        },
        "required": ["text"]
    }
)
async def pdf_generate_from_text(text: str, filename: str = "output.pdf", font_size: int = 12) -> str:
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Helvetica", size=font_size)
        
        for line in text.split('\n'):
            if line.strip():
                pdf.multi_cell(0, 10, line.strip())
            else:
                pdf.ln(5)
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1', errors='replace')
        return json.dumps({
            "filename": filename,
            "size_bytes": len(pdf_bytes),
            "base64": base64.b64encode(pdf_bytes).decode()
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "isError": True}, indent=2)

@server.tool(
    name="pdf_generate_from_url",
    description="Fetch a URL and generate a PDF of its content",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "filename": {"type": "string", "default": "webpage.pdf"},
            "max_chars": {"type": "integer", "default": 10000}
        },
        "required": ["url"]
    }
)
async def pdf_generate_from_url(url: str, filename: str = "webpage.pdf", max_chars: int = 10000) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            
            # Extract text from HTML
            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text).strip()[:max_chars]
            
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Helvetica", size=11)
            
            # Add title
            pdf.set_font("Helvetica", size=16, style='B')
            pdf.cell(0, 10, f"Content from: {url}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            pdf.set_font("Helvetica", size=11)
            
            for line in text.split('. '):
                if line.strip():
                    pdf.multi_cell(0, 8, line.strip() + '.')
            
            pdf_bytes = pdf.output(dest='S').encode('latin-1', errors='replace')
            return json.dumps({
                "filename": filename,
                "url": url,
                "size_bytes": len(pdf_bytes),
                "base64": base64.b64encode(pdf_bytes).decode()
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "isError": True}, indent=2)

def main():
    import anyio
    async def run():
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())
    anyio.run(run)

if __name__ == "__main__":
    main()
