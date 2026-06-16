from docx import Document
import sys

def read_structure(path):
    doc = Document(path)
    for p in doc.paragraphs:
        if p.style.name.startswith('Heading'):
            print(f"{p.style.name}: {p.text}")
        elif len(p.text.strip()) > 0 and 'Title' in p.style.name:
            print(f"Title: {p.text}")

if __name__ == "__main__":
    read_structure(sys.argv[1])
