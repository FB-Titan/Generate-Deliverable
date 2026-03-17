"""
RFI PDF Generator — Modern Design
Refactored from design_options.py create_modern_pdf().
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

# RFI Type → color mapping
RFI_TYPE_COLORS = {
    'field condition': '#FF7F00',
    'design conflict': '#00C853',
    'clarification / missing': '#800000',
    'material substitution': '#00CED1',
    'constructability issue': '#1E90FF',
    'scope / schedule': '#4B0082',
    'other': '#00BFFF'
}


def process_rfi_fields(task_data, common_data):
    """Extract RFI-specific fields from task data and merge with common fields."""
    processed = dict(common_data)

    # RFI-specific defaults
    processed['impacts'] = []
    processed['cost_impact_val'] = False
    processed['schedule_impact_val'] = False
    processed['scope_impact_val'] = False
    processed['estimated_cost'] = 'N/A'
    processed['days_delayed'] = 'N/A'
    processed['rfi_type'] = 'N/A'

    for field in task_data.get('custom_fields', []):
        field_name = field.get('name', '').lower()
        field_value = field.get('value', '')
        if field_value is None:
            continue

        str_value = str(field_value).lower()

        if field_name == 'schedule impact' and str_value == 'true':
            processed['impacts'].append('Schedule Impact')
            processed['schedule_impact_val'] = True
        elif field_name == 'scope impact' and str_value == 'true':
            processed['impacts'].append('Scope Impact')
            processed['scope_impact_val'] = True
        elif field_name == 'cost impact' and str_value == 'true':
            processed['impacts'].append('Cost Impact')
            processed['cost_impact_val'] = True
        elif field_name == 'days delayed':
            processed['days_delayed'] = str(field_value)
        elif field_name in ('estimated amount', 'estimated value'):
            try:
                processed['estimated_cost'] = "${:,.2f}".format(float(field_value))
            except (ValueError, TypeError):
                processed['estimated_cost'] = str(field_value)
        elif field_name == 'rfi type/reason':
            if 'type_config' in field and 'options' in field['type_config']:
                try:
                    val_idx = int(field_value)
                    for opt in field['type_config']['options']:
                        if opt.get('orderindex') == val_idx:
                            processed['rfi_type'] = opt.get('name')
                            break
                except (ValueError, TypeError):
                    processed['rfi_type'] = str(field_value)
            else:
                processed['rfi_type'] = str(field_value)

    # Document ID
    processed['document_id'] = f"{processed['project_id']}-RFI-{processed['sequence']}"

    # RFI Type color
    processed['rfi_type_color'] = '#808080'
    if processed['rfi_type'] != 'N/A':
        val_lower = processed['rfi_type'].lower()
        for key, color in RFI_TYPE_COLORS.items():
            if key in val_lower:
                processed['rfi_type_color'] = color
                break

    return processed


class RFIPDF(FPDF):
    """Modern design RFI PDF with branded header metrics grid and impact footer."""

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
        col_w_label = 20
        col_w_val = 35

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

        meta_cell(start_x, start_y, "RFI ID", doc_id)
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
        if self.page_no() == 1:
            self.set_y(-45)
            y_start = self.get_y()
            h = 30
            col_w = 190 / 3

            def draw_impact_box(x, title, is_checked, value_label, value):
                self.set_xy(x, y_start)
                self.set_draw_color(0, 0, 0)
                self.set_line_width(0.2)
                self.rect(x, y_start, col_w, h)

                self.set_xy(x, y_start)
                self.set_fill_color(*LIGHT_BLUE)
                self.set_text_color(0, 0, 0)
                self.set_font('Helvetica', 'B', 10)
                self.cell(col_w, 8, title, border=1, fill=True, align='C')

                check_size = 4
                check_x = x + 5
                check_y = y_start + 12

                self.set_draw_color(0, 0, 0)
                self.set_fill_color(255, 255, 255)
                self.rect(check_x, check_y, check_size, check_size, 'D')
                if is_checked:
                    self.set_font('ZapfDingbats', '', 10)
                    self.set_text_color(0, 0, 0)
                    self.set_xy(check_x, check_y)
                    self.cell(check_size, check_size, '3', align='C')

                self.set_xy(check_x + 6, check_y)
                self.set_font('Helvetica', '', 9)
                self.set_text_color(0, 0, 0)
                self.cell(20, 4, "Yes")

                if value_label:
                    self.set_xy(x + 5, y_start + 20)
                    self.set_font('Helvetica', 'I', 8)
                    self.cell(0, 4, f"{value_label}: {value}")

            impacts = getattr(self, 'impact_data', {})
            draw_impact_box(10, "COST IMPACT",
                            impacts.get('cost_impact_val'),
                            "Est. Amount", impacts.get('estimated_cost'))
            draw_impact_box(10 + col_w, "SCHEDULE IMPACT",
                            impacts.get('schedule_impact_val'),
                            "Days Delayed", impacts.get('days_delayed'))
            draw_impact_box(10 + (col_w * 2), "SCOPE IMPACT",
                            impacts.get('scope_impact_val'), None, None)

        # Standard footer
        self.set_y(-10)
        self.set_font('Helvetica', '', 6)
        self.set_text_color(150, 150, 150)
        doc_id = getattr(self, 'document_id', 'Unknown ID')
        self.cell(0, 5, f'{doc_id} | Page {self.page_no()}', align='R')


def create_rfi_pdf(task_data, output_path):
    """Generate a Modern-design RFI PDF from ClickUp task data."""
    common = process_common_fields(task_data)
    processed = process_rfi_fields(task_data, common)

    pdf = RFIPDF()
    pdf.document_id = processed['document_id']
    pdf.project_name = processed['project_name']
    pdf.sent_date = processed['sent_date']
    pdf.due_date = processed['due_date']
    pdf.work_order_id = processed['work_order_id']
    pdf.impact_data = processed

    pdf.add_page()
    pdf.set_auto_page_break(True, margin=50)

    # --- Body ---
    pdf.set_y(35)

    # FROM / TO
    pdf.set_font('Helvetica', '', 10)
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

    # REFERENCE / REASON
    pdf.set_x(10)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(25, 5, "REFERENCE: ", align='L')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(70, 5, processed.get('drawing_ref', 'N/A'), align='L')

    pdf.set_x(110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(20, 5, "REASON: ", align='L')

    bg_rgb = hex_to_rgb(processed.get('rfi_type_color', '#808080'))
    current_x = pdf.get_x()
    current_y = pdf.get_y()
    draw_badge(pdf, current_x, current_y, processed.get('rfi_type', 'N/A'), bg_rgb)

    # Priority badge
    priority_data = processed.get('priority')
    if priority_data:
        pdf.set_xy(110, current_y + 6)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(20, 5, "PRIORITY: ", align='L')
        p_bg_rgb = hex_to_rgb(priority_data.get('color') or '#808080')
        draw_badge(pdf, pdf.get_x(), pdf.get_y(),
                   priority_data['priority'].upper(), p_bg_rgb)

    pdf.set_y(current_y + 12)
    pdf.ln(2)

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

    # DESCRIPTION
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, "DESCRIPTION / QUESTION:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    html_desc = markdown2.markdown(processed['description'])
    pdf.write_html(html_desc)

    # --- Page 2: Response ---
    pdf.add_page()
    pdf.set_auto_page_break(False)

    pdf.set_y(30)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(*TITAN_RED)
    pdf.set_line_width(0.5)
    pdf.cell(0, 10, "RESPONSE", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # Response text area
    text_area_y = pdf.get_y()
    text_area_h = 110

    pdf.set_draw_color(150, 150, 150)
    pdf.set_fill_color(252, 252, 252)
    pdf.rect(10, text_area_y, 190, text_area_h, 'DF')
    pdf.set_xy(10, text_area_y)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(190, 5, " Enter Response Here...", align='L')

    # Bottom split: Checkboxes (left) + Stamp area (right)
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

    # Checkboxes
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    options = [
        "Approved", "Approved as Noted",
        "Revise & Resubmit", "Rejected", "Furnish as Corrected"
    ]
    current_check_y = split_start_y
    checkbox_coords = []

    pdf.set_font('Helvetica', '', 11)
    for opt in options:
        pdf.rect(left_x + 5, current_check_y, 5, 5)
        pdf.set_xy(left_x + 15, current_check_y)
        pdf.cell(col_width - 15, 6, opt)
        checkbox_coords.append({
            'name': f"chk_{opt.replace(' ', '_').lower()}",
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
    add_form_field(output_path, x=10, y=text_area_y, width=190, height=text_area_h)
    for chk in checkbox_coords:
        add_checkbox(output_path, chk['x'], chk['y'], chk['size'], False, chk['name'])

    logger.info("RFI PDF created: %s", output_path)
    return output_path
