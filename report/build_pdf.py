"""
Builds report/report.pdf and report/ai_report.pdf from their Markdown sources
(overview, section 5.3: the PDFs with their sources beside them).

Markdown -> HTML with the `markdown` package (tables extension), then
HTML -> PDF with a headless Chromium browser (Edge or Chrome), so no LaTeX
installation is needed.  Usage:  python report/build_pdf.py
"""

import os
import shutil
import subprocess
import sys

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
CSS = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
body { font-family: "Calibri", "Segoe UI", sans-serif; font-size: 10pt; line-height: 1.35; color: #111; }
h1 { font-size: 17pt; color: #2b4c7e; margin: 0 0 6pt 0; }
h2 { font-size: 13pt; color: #2b4c7e; border-bottom: 1px solid #ccd; margin: 14pt 0 4pt 0; }
h3 { font-size: 11pt; color: #2b4c7e; margin: 10pt 0 3pt 0; }
table { border-collapse: collapse; margin: 5pt 0 8pt 0; font-size: 8.5pt; }
th, td { border: 1px solid #b8bcc8; padding: 2pt 5pt; text-align: left; vertical-align: top; }
th { background: #eef0f5; }
code { font-family: "Consolas", monospace; font-size: 8.5pt; background: #f4f5f8; padding: 0 2pt; }
pre { background: #f4f5f8; padding: 5pt; font-size: 8pt; white-space: pre-wrap; }
img { max-width: 100%; }
.title { text-align: center; margin-top: 60pt; }
.pagebreak { page-break-after: always; }
"""

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "chromium", "chromium-browser", "google-chrome", "microsoft-edge",
]


def find_browser() -> str:
    for b in BROWSERS:
        if os.path.isfile(b) or shutil.which(b):
            return b
    sys.exit("No Chromium-based browser found to print the PDF")


def build(name: str) -> None:
    src = os.path.join(HERE, f"{name}.md")
    html_path = os.path.join(HERE, f"{name}.html")
    pdf_path = os.path.join(HERE, f"{name}.pdf")
    with open(src, 'r', encoding='utf-8') as f:
        body = markdown.markdown(f.read(), extensions=["tables", "fenced_code", "md_in_html"])
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(f"<!doctype html><html><head><meta charset='utf-8'><title>{name}</title>"
                f"<style>{CSS}</style></head><body>{body}</body></html>")
    url = "file:///" + html_path.replace("\\", "/")
    subprocess.run([find_browser(), "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", url], check=True, capture_output=True)
    os.remove(html_path)
    print(f"{pdf_path} written")


if __name__ == "__main__":
    for n in sys.argv[1:] or ["report", "ai_report"]:
        build(n)
