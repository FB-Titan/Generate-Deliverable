import os
import logging
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DictionaryObject, ArrayObject, NumberObject, TextStringObject, BooleanObject
import markdown2
import config
from rfi_utils import fetch_task_details, process_task_data, add_form_field, add_checkbox

TITAN_BLUE = (12, 77, 162)
TITAN_RED = (204, 0, 0)
LIGHT_BLUE = (240, 248, 255)


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Proposal A: Modern Minimalist ---
# --- Proposal A: Professional Modern Grid ---
class RFIPDF_Modern(FPDF):
    def header(self):
        # 1. Top Section: Logo (Left) vs Metadata Grid (Right)
        if os.path.exists(config.LOGO_PATH):
            self.image(config.LOGO_PATH, x=10, y=10, w=40)
        
        # We need access to processed data or store it on the pdf object more robustly
        doc_id = getattr(self, 'document_id', '')
        sent_date = getattr(self, 'sent_date', '')
        due_date = getattr(self, 'due_date', '')
        work_order = getattr(self, 'work_order_id', '')

        # Metadata Grid (2x2)
        # Top Left starts around x=100 or so to fit? 
        # Page width 210. Logo is at 10, width 40. 
        # Let's align grid to right margin.
        
        # Grid layout:
        # [RFI ID Label | RFI ID Val] [Sent Date Label | Sent Date Val]
        # [Due Date Label | Due Date Val] [Work Order Label | Work Order Val]
        # Actually user asked for "RFI ID Table over into a 2x2".
        # Let's do:
        # Col 1: RFI ID, Sent Date
        # Col 2: Work Order, Due Date
        
        start_x = 90
        start_y = 10
        row_h = 6
        col_w_label = 20
        col_w_val = 35
        
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.1)

        def meta_cell(x, y, label, value):
            # Label
            self.set_xy(x, y)
            self.set_fill_color(*LIGHT_BLUE)
            self.set_font('Helvetica', 'B', 8)
            self.set_text_color(0, 0, 0)
            self.cell(col_w_label, row_h, label, border=1, fill=True)
            
            # Value
            self.set_xy(x + col_w_label, y)
            self.set_fill_color(255, 255, 255)
            self.set_font('Helvetica', '', 8)
            self.set_text_color(0, 0, 0)
            self.cell(col_w_val, row_h, value, border=1, fill=True)

        # Row 1
        meta_cell(start_x, start_y, "RFI ID", doc_id)
        meta_cell(start_x + col_w_label + col_w_val, start_y, "Sent Date", sent_date)
        
        # Row 2
        meta_cell(start_x, start_y + row_h, "Work Order", work_order)
        meta_cell(start_x + col_w_label + col_w_val, start_y + row_h, "Due Date", due_date)
        
        # Reduced whitespace below grid
        self.set_y(start_y + (row_h * 2) + 5)
        
        # Red Divider Line
        self.set_draw_color(*TITAN_RED)
        self.set_line_width(1.0) # Thicker bar
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        
    def footer(self):
        # Only show the complex impacts footer on Page 1
        if self.page_no() == 1:
            self.set_y(-45) # Reserve space at bottom
            
            # Draw 3-Column Boxed Row
            y_start = self.get_y()
            h = 30
            col_w = 190 / 3
            
            # Helper to draw impact box
            def draw_impact_box(x, title, is_checked, value_label, value):
                # Box Border
                self.set_xy(x, y_start)
                self.set_draw_color(0, 0, 0)
                self.set_line_width(0.2)
                self.rect(x, y_start, col_w, h)
                
                # Title Box
                self.set_xy(x, y_start)
                self.set_fill_color(*LIGHT_BLUE)
                self.set_text_color(0, 0, 0)
                self.set_font('Helvetica', 'B', 10)
                self.cell(col_w, 8, title, border=1, fill=True, align='C')
                
                # Checkbox Visual (Static)
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
                
                # Value Area
                if value_label:
                    self.set_xy(x + 5, y_start + 20)
                    self.set_font('Helvetica', 'I', 8)
                    self.cell(0, 4, f"{value_label}: {value}")

            # Get data stored in instance
            impacts = getattr(self, 'impact_data', {})
            
            # Col 1: Cost
            draw_impact_box(10, "COST IMPACT", impacts.get('cost_impact_val'), "Est. Amount", impacts.get('estimated_cost'))
            
            # Col 2: Schedule
            draw_impact_box(10 + col_w, "SCHEDULE IMPACT", impacts.get('schedule_impact_val'), "Days Delayed", impacts.get('days_delayed'))
            
            # Col 3: Scope
            draw_impact_box(10 + (col_w*2), "SCOPE IMPACT", impacts.get('scope_impact_val'), None, None)
            
        # Standard Footer text
        self.set_y(-10)
        self.set_font('Helvetica', '', 6)
        self.set_text_color(150, 150, 150)
        doc_id = getattr(self, 'document_id', 'Unknown ID')
        self.cell(0, 5, f'{doc_id} | Page {self.page_no()}', align='R')

def create_modern_pdf(task_data, output_path):
    processed = process_task_data(task_data)
    pdf = RFIPDF_Modern()
    
    # Store data for header/footer accessibility
    pdf.document_id = processed['document_id']
    pdf.project_name = processed['project_name']
    pdf.sent_date = processed['sent_date']
    pdf.due_date = processed['due_date']
    pdf.work_order_id = processed['work_order_id']
    pdf.impact_data = processed
    
    pdf.add_page()
    pdf.set_auto_page_break(True, margin=50) # Large bottom margin for footer on page 1
    
    # --- Body Content ---
    pdf.set_y(35)
    
    # To / From Section
    pdf.set_font('Helvetica', '', 10)
    
    # From
    pdf.set_x(10)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(15, 5, "FROM: ", align='L')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    # Use assignee_name if available, fallback to creator is handled in processing or here
    from_name = processed.get('assignee_name') or processed.get('creator_name', '')
    pdf.cell(80, 5, f"{config.COMPANY_NAME} / {from_name}", align='L')
    
    # To
    pdf.set_x(110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(10, 5, "TO: ", align='L')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    to_name = processed.get('submitted_to') or "[Architect / Engineer]"
    pdf.cell(70, 5, to_name, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(2)
    
    # Ref Data
    pdf.set_x(10)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(25, 5, "REFERENCE: ", align='L')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    ref_text = f"{processed.get('drawing_ref', 'N/A')}"
    pdf.cell(70, 5, ref_text, align='L')
    
    # RFI Type & Priority
    pdf.set_x(110)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(20, 5, "REASON: ", align='L')
    
    # Get color
    rfi_color_hex = processed.get('rfi_type_color', '#808080')
    rfi_text = processed.get('rfi_type', 'N/A')
    
    # Convert hex to rgb
    def hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    
    bg_rgb = hex_to_rgb(rfi_color_hex)
    
    # Draw RFI Type Badge
    current_x = pdf.get_x()
    current_y = pdf.get_y()
    
    # Helper for badges
    def draw_badge(pdf_obj, x, y, text, bg_color, text_color=(255,255,255)):
        pdf_obj.set_xy(x, y)
        pdf_obj.set_font('Helvetica', 'B', 8)
        w = pdf_obj.get_string_width(text) + 6
        h = 5
        
        pdf_obj.set_fill_color(*bg_color)
        pdf_obj.set_draw_color(*bg_color)
        # Use round_corners=True and corner_radius=h/2 for pill shape (2.5)
        # Note: round_corners argument is available in modern fpdf2
        try:
            pdf_obj.rect(x, y, w, h, style='DF', round_corners=True, corner_radius=2.5)
        except TypeError:
            # Fallback for older fpdf2 versions or if argument differs
            pdf_obj.rect(x, y, w, h, style='DF')
        
        pdf_obj.set_xy(x, y)
        pdf_obj.set_text_color(*text_color)
        pdf_obj.cell(w, h, text, align='C')
        return w

    badge_w = draw_badge(pdf, current_x, current_y, rfi_text, bg_rgb)
    
    # Priority
    priority_data = processed.get('priority')
    if priority_data:
        p_text = priority_data['priority']
        p_color_hex = priority_data['color'] or '#808080'
        p_bg_rgb = hex_to_rgb(p_color_hex)
        
        # Label
        pdf.set_xy(110, current_y + 6) # Below Reason
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(20, 5, "PRIORITY: ", align='L')
        
        # Badge
        pdf.set_xy(110 + 20, current_y + 6)
        draw_badge(pdf, pdf.get_x(), pdf.get_y(), p_text.upper(), p_bg_rgb)
    
    # Move down past both rows
    pdf.set_y(current_y + 12)
    pdf.ln(2)
    
    # Horizontal Rule (Red)
    pdf.set_draw_color(*TITAN_RED)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # Subject - Large Bold
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, "SUBJECT:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, processed['subject'])
    pdf.ln(5)
    
    # Description
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, "DESCRIPTION / QUESTION:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    html_desc = markdown2.markdown(processed['description'])
    pdf.write_html(html_desc)
    
    # Page 2: Response Redesign (Text Field Top, Split Bottom)
    pdf.add_page()
    pdf.set_auto_page_break(False) 
    
    pdf.set_y(30)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(*TITAN_RED) # Red separator
    pdf.set_line_width(0.5)
    pdf.cell(0, 10, "RESPONSE", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    
    # 1. Full Width Response Text Area (Top Half)
    text_area_y = pdf.get_y()
    text_area_h = 110 # Space for text
    
    pdf.set_draw_color(150, 150, 150)
    pdf.set_fill_color(252, 252, 252)
    pdf.rect(10, text_area_y, 190, text_area_h, 'DF')
    
    # Label for area
    pdf.set_xy(10, text_area_y)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(190, 5, " Enter Response Here...", align='L')
    
    # 2. Split Section (Bottom Half)
    split_start_y = text_area_y + text_area_h + 10
    
    left_x = 10
    right_x = 110
    col_width = 90
    
    # Right: Stamp Box
    pdf.set_xy(right_x, split_start_y)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.5)
    # Dashed border logic usually requires manual dash pattern setting which fpdf/pypdf simple rect doesn't always expose easily without low-level.
    # We'll use a gray rect for now.
    stamp_h = 90
    pdf.rect(right_x, split_start_y, col_width, stamp_h, 'D')
    
    pdf.set_xy(right_x, split_start_y + (stamp_h/2) - 5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(220, 220, 220)
    pdf.cell(col_width, 10, "ENGINEER STAMP AREA", align='C')
    
    # Left: Checkboxes
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    
    options = [
        "Approved",
        "Approved as Noted",
        "Revise & Resubmit",
        "Rejected",
        "Furnish as Corrected"
    ]
    
    current_check_y = split_start_y
    checkbox_coords = []
    
    pdf.set_font('Helvetica', '', 11)
    for opt in options:
        # Visual Box
        pdf.rect(left_x + 5, current_check_y, 5, 5)
        # Label
        pdf.set_xy(left_x + 15, current_check_y)
        pdf.cell(col_width - 15, 6, opt)
        
        checkbox_coords.append({
            'name': f"chk_{opt.replace(' ', '_').lower()}",
            'x': left_x + 5,
            'y': current_check_y,
            'size': 5
        })
        current_check_y += 9 # Tighter spacing
        
    # Left: Signature Block (Below checkboxes)
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

    pdf.output(output_path)
    
    # Add Interactive Elements
    
    # 1. Response Text Field (Top)
    add_form_field(output_path, x=10, y=text_area_y, width=190, height=text_area_h)
    
    # 2. Checkboxes (Bottom Left)
    for chk in checkbox_coords:
        add_checkbox(output_path, chk['x'], chk['y'], chk['size'], False, chk['name'])



# --- Proposal B: Engineering Grid ---
class RFIPDF_Grid(FPDF):
    def header(self):
        # Full width header box
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.5)
        self.rect(10, 10, 190, 25)
        
        # Logo Box
        self.line(60, 10, 60, 35)
        if os.path.exists(config.LOGO_PATH):
            self.image(config.LOGO_PATH, x=15, y=12, w=35)
            
        # Title Box
        self.line(150, 10, 150, 35)
        self.set_xy(60, 10)
        self.set_font('Helvetica', 'B', 18)
        self.cell(90, 25, 'RFI DOCUMENT', align='C')
        
        # Info Box
        self.set_xy(152, 12)
        self.set_font('Helvetica', 'B', 8)
        self.cell(48, 4, config.COMPANY_NAME, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(152)
        self.set_font('Helvetica', '', 7)
        self.cell(48, 3, config.COMPANY_ADDRESS_1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(152)
        self.cell(48, 3, config.COMPANY_ADDRESS_2, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Courier', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def create_grid_pdf(task_data, output_path):
    processed = process_task_data(task_data)
    pdf = RFIPDF_Grid()
    pdf.document_id = processed['document_id']
    pdf.add_page()
    pdf.set_auto_page_break(True, margin=20)
    
    # Grid Metadata Table
    pdf.set_line_width(0.3)
    pdf.set_draw_color(0, 0, 0)
    
    def grid_row(label1, val1, label2, val2):
        y = pdf.get_y()
        # Row height
        h = 10
        
        # Cell 1 Label
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.rect(10, y, 35, h, 'DF')
        pdf.set_xy(10, y+2)
        pdf.cell(35, 6, label1, align='C')
        
        # Cell 1 Value
        pdf.set_fill_color(255, 255, 255)
        pdf.set_font('Courier', '', 10)
        pdf.rect(45, y, 60, h, 'D')
        pdf.set_xy(45, y+2)
        pdf.cell(60, 6, val1, align='C')
        
        # Cell 2 Label
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.rect(105, y, 35, h, 'DF')
        pdf.set_xy(105, y+2)
        pdf.cell(35, 6, label2, align='C')
        
        # Cell 2 Value
        pdf.set_fill_color(255, 255, 255)
        pdf.set_font('Courier', '', 10)
        pdf.rect(140, y, 60, h, 'D')
        pdf.set_xy(140, y+2)
        pdf.cell(60, 6, val2, align='C')
        
        pdf.ln(h)

    grid_row('RFI #', processed['document_id'], 'Work Order', processed['work_order_id'])
    grid_row('Date Sent', processed['sent_date'], 'Date Due', processed['due_date'])
    
    pdf.ln(5)
    
    # Boxed Sections
    def box_section(title, content, is_html=False):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(0, 0, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 6, f"  {title.upper()}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_text_color(0, 0, 0)
        start_y = pdf.get_y()
        
        # Calculate content height? strict box? flow?
        # Let's just flow and draw a box around it approx
        pdf.set_font('Helvetica', '', 10)
        if is_html:
            pdf.write_html(content)
        else:
            pdf.multi_cell(190, 5, content)
            
        # Draw box around content
        end_y = pdf.get_y()
        pdf.rect(10, start_y, 190, end_y - start_y)
        pdf.ln(5)

    box_section('Subject', processed['subject'])
    
    # Description
    description_html = markdown2.markdown(processed['description'])
    box_section('Description', description_html, is_html=True)
    
    box_section('Impacts', ", ".join(processed['impacts']) if processed['impacts'] else "None")
    
    # Response
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(0, 0, 0)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 6, "  RESPONSE", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    form_y = pdf.get_y()
    available_height = 250 - form_y
    if available_height < 50:
        pdf.add_page()
        form_y = pdf.get_y()
        available_height = 100
    
    # Draw simple frame for response
    pdf.set_draw_color(0, 0, 0)
    pdf.rect(10, form_y, 190, available_height)
        
    pdf.output(output_path)
    add_form_field(output_path, x=10, y=form_y, width=190, height=available_height)

if __name__ == "__main__":
    task_id = "86dvdkn82"
    try:
        data = fetch_task_details(task_id)
        
        create_modern_pdf(data, f"RFI_{task_id}_Modern.pdf")
        print("Created Modern Design")
        
        create_grid_pdf(data, f"RFI_{task_id}_Grid.pdf")
        print("Created Grid Design")
        
    except Exception as e:
        print(e)
