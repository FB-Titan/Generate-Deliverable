"""
Submittal PDF Generator — Modern Design
Transmittal-style cover sheet with specification references,
material/product info, and approval section.
"""
import os
import logging
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import markdown2

import config
from utils import process_common_fields
from generators.base import (
    TITAN_BLUE, TITAN_RED, LIGHT_BLUE,
    hex_to_rgb, draw_badge, add_form_field, add_checkbox
)

logger = logging.getLogger(__name__)


def process_submittal_fields(task_data, common_data):
    """Extract Submittal-specific fields from task data."""
    processed = dict(common_data)

    # Document ID for Submittals
    processed['document_id'] = f"{processed['project_id']}-SUB-{processed['sequence']}"

    return processed


class SubmittalPDF(FPDF):
    """Modern design Submittal PDF with branded header and transmittal layout."""

    def header(self):
        # Logo
        if os.path.exists(config.LOGO_PATH):
            self.image(config.LOGO_PATH, x=10, y=10, w=40)

        doc_id = getattr(self, 'document_id', '')
        sent_date = getattr(self, 'sent_date', '')
        due_date = getattr(self, 'due_date', '')
        work_order = getattr(self, 'work_order_id', '')

        # Metadata Grid (2x2)
        start_x = 90
        start_y = 10
        row_h = 6
        col_w_label = 22
        col_w_val = 33

        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.1)

        def meta_cell(x, y, label, value):
            self.set_xy(x, y)
            self.set_fill_color(*LIGHT_BLUE)
            self.set_font('Helvetica', 'B', 8)
            self.set_text_color(0, 0, 0)
            self.cell(col_w_label, row_h, label, border=1, fill=True)
            self.set_xy(x + col_w_label, y)
            self.set_fill_color(255, 255, 255)
            self.set_font('Helvetica', '', 8)
            self.cell(col_w_val, row_h, value, border=1, fill=True)

        meta_cell(start_x, start_y, "Submittal ID", doc_id)
        meta_cell(start_x + col_w_label + col_w_val, start_y, "Sent Date", sent_date)
        meta_cell(start_x, start_y + row_h, "Work Order", work_order)
        meta_cell(start_x + col_w_label + col_w_val, start_y + row_h, "Due Date", due_date)

        self.set_y(start_y + (row_h * 2) + 5)

        # Red Divider
        self.set_draw_color(*TITAN_RED)
        self.set_line_width(1.0)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-10)
        self.set_font('Helvetica', '', 6)
        self.set_text_color(150, 150, 150)
        doc_id = getattr(self, 'document_id', 'Unknown ID')
        self.cell(0, 5, f'{doc_id} | Page {self.page_no()}', align='R')


def create_submittal_pdf(task_data, output_path):
    """Generate a Submittal transmittal cover sheet PDF from ClickUp task data."""
    common = process_common_fields(task_data)
    processed = process_submittal_fields(task_data, common)

    pdf = SubmittalPDF()
    pdf.document_id = processed['document_id']
    pdf.project_name = processed['project_name']
    pdf.sent_date = processed['sent_date']
    pdf.due_date = processed['due_date']
    pdf.work_order_id = processed['work_order_id']

    pdf.add_page()
    pdf.set_auto_page_break(True, margin=20)

    # --- Body ---
    pdf.set_y(35)

    # FROM / TO
    pdf.set_x(10)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(15, 5, "FROM: ", align='L')
    pdf.set_font('Helvetica', '', 10)
    from_name = processed.get('assignee_name') or processed.get('creator_name', '')
    pdf.cell(80, 5, f"{config.COMPANY_NAME} / {from_name}", align='L')

    pdf.set_x(110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(10, 5, "TO: ", align='L')
    pdf.set_font('Helvetica', '', 10)
    to_name = processed.get('submitted_to') or "[Architect / Engineer]"
    pdf.cell(70, 5, to_name, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # Reference
    pdf.set_x(10)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(25, 5, "REFERENCE: ", align='L')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(70, 5, processed.get('drawing_ref', 'N/A'), align='L')

    # PO #
    pdf.set_x(110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(10, 5, "PO: ", align='L')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(70, 5, processed.get('purchase_order_id', 'N/A'), align='L',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    current_y = pdf.get_y()
    pdf.set_y(current_y + 4)

    # Red divider
    pdf.set_draw_color(*TITAN_RED)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # SUBJECT
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, "SUBJECT:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.multi_cell(0, 6, processed['subject'])
    pdf.ln(5)

    # DESCRIPTION / SCOPE
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, "DESCRIPTION / SCOPE:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    html_desc = markdown2.markdown(processed['description'])
    pdf.write_html(html_desc)
    pdf.ln(10)

    # SUBMITTED FOR section
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, "SUBMITTED FOR:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    submit_options = [
        "Review & Comment",
        "Approval",
        "Record / Information Only"
    ]
    submit_check_y = pdf.get_y()
    submit_checkbox_coords = []

    pdf.set_font('Helvetica', '', 10)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    for opt in submit_options:
        pdf.rect(15, submit_check_y, 4, 4)
        pdf.set_xy(22, submit_check_y)
        pdf.cell(80, 5, opt)
        submit_checkbox_coords.append({
            'name': f"submit_{opt.replace(' ', '_').replace('/', '_').lower()}",
            'x': 15, 'y': submit_check_y, 'size': 4
        })
        submit_check_y += 7

    pdf.set_y(submit_check_y + 5)

    # --- Page 2: Response / Approval ---
    pdf.add_page()
    pdf.set_auto_page_break(False)

    pdf.set_y(30)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(*TITAN_RED)
    pdf.set_line_width(0.5)
    pdf.cell(0, 10, "REVIEWER RESPONSE", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # Response text area
    text_area_y = pdf.get_y()
    text_area_h = 90

    pdf.set_draw_color(150, 150, 150)
    pdf.set_fill_color(252, 252, 252)
    pdf.rect(10, text_area_y, 190, text_area_h, 'DF')
    pdf.set_xy(10, text_area_y)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(190, 5, " Reviewer comments...", align='L')

    # Bottom: Approval checkboxes (left) + Stamp area (right)
    split_start_y = text_area_y + text_area_h + 10
    left_x = 10
    right_x = 110
    col_width = 90

    # Stamp box
    pdf.set_xy(right_x, split_start_y)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.5)
    stamp_h = 90
    pdf.rect(right_x, split_start_y, col_width, stamp_h, 'D')
    pdf.set_xy(right_x, split_start_y + (stamp_h / 2) - 5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(220, 220, 220)
    pdf.cell(col_width, 10, "ENGINEER STAMP AREA", align='C')

    # Approval checkboxes
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    approval_options = [
        "Approved",
        "Approved as Noted",
        "Revise & Resubmit",
        "Rejected",
        "Furnish as Corrected"
    ]
    current_check_y = split_start_y
    approval_checkbox_coords = []

    pdf.set_font('Helvetica', '', 11)
    for opt in approval_options:
        pdf.rect(left_x + 5, current_check_y, 5, 5)
        pdf.set_xy(left_x + 15, current_check_y)
        pdf.cell(col_width - 15, 6, opt)
        approval_checkbox_coords.append({
            'name': f"approval_{opt.replace(' ', '_').lower()}",
            'x': left_x + 5, 'y': current_check_y, 'size': 5
        })
        current_check_y += 9

    # Signature lines
    sig_start_y = current_check_y + 10
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)

    def sig_line(label, y):
        pdf.line(left_x, y, left_x + 80, y)
        pdf.set_xy(left_x, y + 2)
        pdf.set_font('Helvetica', 'I', 9)
        pdf.cell(80, 5, label)

    sig_line("Date", sig_start_y)
    sig_line("Name", sig_start_y + 18)
    sig_line("Signature", sig_start_y + 36)

    # Save static PDF
    pdf.output(output_path)

    # Add interactive form fields
    # Page 1 submit-for checkboxes
    for chk in submit_checkbox_coords:
        add_checkbox(output_path, chk['x'], chk['y'], chk['size'], False, chk['name'])

    # Page 2 response text field
    add_form_field(output_path, x=10, y=text_area_y, width=190, height=text_area_h)

    # Page 2 approval checkboxes
    for chk in approval_checkbox_coords:
        add_checkbox(output_path, chk['x'], chk['y'], chk['size'], False, chk['name'])

    logger.info("Submittal PDF created: %s", output_path)
    return output_path
