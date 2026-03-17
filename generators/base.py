"""
Shared PDF utilities: colors, form field helpers, and common layout components.
Used by all deliverable generators (RFI, Submittal, etc.).
"""
import os
import logging
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    NameObject, DictionaryObject, ArrayObject,
    NumberObject, TextStringObject, BooleanObject
)
import config

logger = logging.getLogger(__name__)

# Brand Colors
TITAN_BLUE = (12, 77, 162)
TITAN_RED = (204, 0, 0)
LIGHT_BLUE = (240, 248, 255)


def hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple."""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def draw_badge(pdf, x, y, text, bg_color, text_color=(255, 255, 255)):
    """Draw a colored pill-shaped badge on the PDF."""
    pdf.set_xy(x, y)
    pdf.set_font('Helvetica', 'B', 8)
    w = pdf.get_string_width(text) + 6
    h = 5

    pdf.set_fill_color(*bg_color)
    pdf.set_draw_color(*bg_color)
    try:
        pdf.rect(x, y, w, h, style='DF', round_corners=True, corner_radius=2.5)
    except TypeError:
        pdf.rect(x, y, w, h, style='DF')

    pdf.set_xy(x, y)
    pdf.set_text_color(*text_color)
    pdf.cell(w, h, text, align='C')
    return w


def add_form_field(pdf_path, x, y, width, height, field_name="response"):
    """Add a multiline text form field to an existing PDF using pypdf."""
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)

    page = writer.pages[-1]
    page_height = page.mediabox.height
    mm_to_pt = 72 / 25.4

    x_pt = x * mm_to_pt
    y_pt = y * mm_to_pt
    w_pt = width * mm_to_pt
    h_pt = height * mm_to_pt

    rect_x1 = x_pt
    rect_y1 = float(page_height) - (y_pt + h_pt)
    rect_x2 = x_pt + w_pt
    rect_y2 = float(page_height) - y_pt

    annotation = DictionaryObject()
    annotation.update({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Widget"),
        NameObject("/FT"): NameObject("/Tx"),
        NameObject("/T"): TextStringObject(field_name),
        NameObject("/Rect"): ArrayObject([
            NumberObject(rect_x1), NumberObject(rect_y1),
            NumberObject(rect_x2), NumberObject(rect_y2),
        ]),
        NameObject("/DA"): TextStringObject("/Helv 12 Tf 0 g"),
        NameObject("/F"): NumberObject(4),
        NameObject("/Ff"): NumberObject(4096),  # Multiline
        NameObject("/MK"): DictionaryObject({
            NameObject("/BC"): ArrayObject([NumberObject(0)]),
            NameObject("/BG"): ArrayObject([
                NumberObject(1), NumberObject(1), NumberObject(1)
            ]),
        }),
    })

    annot_obj = writer._add_object(annotation)

    if "/Annots" not in page:
        page[NameObject("/Annots")] = ArrayObject()
    page["/Annots"].append(annot_obj)

    if "/AcroForm" not in writer.root_object:
        writer.root_object.update({
            NameObject("/AcroForm"): DictionaryObject({
                NameObject("/Fields"): ArrayObject(),
                NameObject("/DA"): TextStringObject("/Helv 12 Tf 0 g"),
                NameObject("/NeedAppearances"): BooleanObject(True)
            })
        })

    writer.root_object["/AcroForm"]["/Fields"].append(annot_obj)

    with open(pdf_path, "wb") as f:
        writer.write(f)


def add_checkbox(pdf_path, x, y, size, checked, field_name):
    """Add a checkbox form field to an existing PDF using pypdf."""
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)

    page = writer.pages[-1]
    page_height = page.mediabox.height
    mm_to_pt = 72 / 25.4

    x_pt = x * mm_to_pt
    y_pt = y * mm_to_pt
    size_pt = size * mm_to_pt

    rect_x1 = x_pt
    rect_y1 = float(page_height) - (y_pt + size_pt)
    rect_x2 = x_pt + size_pt
    rect_y2 = float(page_height) - y_pt

    annotation = DictionaryObject()
    annotation.update({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Widget"),
        NameObject("/FT"): NameObject("/Btn"),
        NameObject("/T"): TextStringObject(field_name),
        NameObject("/Rect"): ArrayObject([
            NumberObject(rect_x1), NumberObject(rect_y1),
            NumberObject(rect_x2), NumberObject(rect_y2)
        ]),
        NameObject("/F"): NumberObject(4),
        NameObject("/Ff"): NumberObject(0),
        NameObject("/V"): NameObject("/Yes") if checked else NameObject("/Off"),
        NameObject("/AS"): NameObject("/Yes") if checked else NameObject("/Off"),
        NameObject("/MK"): DictionaryObject({
            NameObject("/BC"): ArrayObject([NumberObject(0)]),
            NameObject("/BG"): ArrayObject([
                NumberObject(1), NumberObject(1), NumberObject(1)
            ]),
            NameObject("/CA"): TextStringObject("4"),
        }),
        NameObject("/DA"): TextStringObject("/ZapfDingbats 0 Tf 0 g")
    })

    annot_obj = writer._add_object(annotation)

    if "/Annots" not in page:
        page[NameObject("/Annots")] = ArrayObject()
    page["/Annots"].append(annot_obj)

    if "/AcroForm" not in writer.root_object:
        writer.root_object.update({
            NameObject("/AcroForm"): DictionaryObject({
                NameObject("/Fields"): ArrayObject(),
                NameObject("/DA"): TextStringObject("/Helv 12 Tf 0 g"),
                NameObject("/NeedAppearances"): BooleanObject(True),
                NameObject("/DR"): DictionaryObject({
                    NameObject("/Font"): DictionaryObject({
                        NameObject("/ZapfDingbats"): DictionaryObject({
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/ZapfDingbats")
                        })
                    })
                })
            })
        })

    writer.root_object["/AcroForm"]["/Fields"].append(annot_obj)

    with open(pdf_path, "wb") as f:
        writer.write(f)
