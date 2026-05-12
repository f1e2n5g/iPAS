import pdfplumber
import os
import sys

def pdf_to_text(pdf_path, txt_path):
    """Convert PDF to text file"""
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"Processing: {os.path.basename(pdf_path)}")
    
    all_text = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                all_text.append(f"=== Page {i} ===")
                all_text.append(text)
                all_text.append("")
    
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_text))
    
    print(f"Completed: {os.path.basename(txt_path)}")
    print(f"Total pages processed: {len(pdf.pages)}")
    print()

base_dir = r"c:\Users\f1e2n\Desktop\📁 我的專案\iPAS\同學分享"

pdf1 = os.path.join(base_dir, "iPAS_AI應用規劃師初級_01-1模擬題本_0831.pdf")
pdf2 = os.path.join(base_dir, "iPAS_AI應用規劃師初級20260110模擬題p1.pdf")

txt1 = os.path.join(base_dir, "iPAS_AI應用規劃師初級_01-1模擬題本_0831.txt")
txt2 = os.path.join(base_dir, "iPAS_AI應用規劃師初級20260110模擬題p1.txt")

pdf_to_text(pdf1, txt1)
pdf_to_text(pdf2, txt2)

print("All PDFs converted successfully!")
