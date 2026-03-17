import fpdf
print(dir(fpdf))
try:
    from fpdf import PdfField
    print("PdfField imported from fpdf")
except ImportError:
    print("PdfField NOT in fpdf")

try:
    import fpdf.defs
    print("fpdf.defs imported")
except ImportError:
    print("fpdf.defs NOT imported")
