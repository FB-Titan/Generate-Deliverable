import requests
import os
import logging
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DictionaryObject, ArrayObject, NumberObject, TextStringObject, BooleanObject, IndirectObject
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_task_details(task_id):
    """Fetch task details from ClickUp API."""
    url = f"{config.CLICKUP_API_BASE_URL}/task/{task_id}?include_markdown_description=true"
    headers = {"Authorization": config.CLICKUP_API_TOKEN}
    
    logger.info("Fetching task details for task ID: %s", task_id)
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch task: {response.status_code} {response.text}")

def process_task_data(task_data):
    """Process the raw task data from ClickUp into a format we can use."""
    processed = {}
    
    # Get custom fields
    custom_fields = task_data.get('custom_fields', [])
    
    # Initialize values
    processed['impacts'] = []
    processed['subject'] = ''
    processed['project_id'] = ''
    processed['project_name'] = task_data.get('project', {}).get('name', '')
    processed['creator_name'] = task_data.get('creator', {}).get('username', 'Titan Electric')
    processed['date_created'] = getattr(task_data, 'date_created', '') # Raw timestamp
    
    # Initialize extraction variables
    processed['cost_impact_val'] = False
    processed['schedule_impact_val'] = False
    processed['scope_impact_val'] = False
    processed['estimated_cost'] = 'N/A'
    processed['days_delayed'] = 'N/A'
    processed['rfi_type'] = 'N/A'
    processed['drawing_ref'] = 'N/A'
    
    processed['work_order_id'] = ''
    processed['pmo_item_type'] = ''
    processed['sequence'] = ''
    processed['start_date'] = ''
    
    # PMO Item Type mapping
    pmo_item_type_map = {
        0: "Task", 1: "RFI", 2: "Submittal", 3: "Change Request",
        4: "Subcontractor", 5: "Purchase Order", 6: "Threats",
        7: "Opportunities", 8: "Lesson Learned", 9: "Safety",
        10: "Milestone", 11: "Material", 12: "Activities"
    }
    
    # Process custom fields
    for field in custom_fields:
        field_name = field.get('name', '').lower()
        field_value = field.get('value', '')
        
        if field_value is None:
            continue

        str_value = str(field_value).lower()

        if field_name == 'schedule impact':
            if str_value == 'true':
                 processed['impacts'].append('Schedule Impact')
                 processed['schedule_impact_val'] = True
        elif field_name == 'scope impact':
            if str_value == 'true':
                processed['impacts'].append('Scope Impact')
                processed['scope_impact_val'] = True
        elif field_name == 'cost impact':
            if str_value == 'true':
                processed['impacts'].append('Cost Impact')
                processed['cost_impact_val'] = True
        elif field_name == 'days delayed':
             processed['days_delayed'] = str(field_value)
        elif field_name == 'estimated amount' or field_name == 'estimated value':
             # Format as currency if possible
             try:
                 val_float = float(field_value)
                 processed['estimated_cost'] = "${:,.2f}".format(val_float)
             except (ValueError, TypeError):
                 processed['estimated_cost'] = str(field_value)
        elif field_name == 'rfi type/reason':
             # Dropdowns usually provide an index or ID, need to check if value is the label or valid index. 
             # In the provided JSON, dropdowns effectively return an index or object? 
             # Actually, Process logic for dropdowns usually needs mapping if it returns an int index.
             # The 'value' in the JSON update shows it might be an index for dropdowns.
             # Let's map it if possible, or stringify.
             # Based on API snippet: options have orderindex.
             # For simpler handling, we will assume value might be the selected option index or directly the string if available.
             # But typically ClickUp API returns the index for dropdowns.
             # We should probably fetch the label from the type_config options if we had the full task_data custom fields definition available in context.
             # Since we are iterating 'custom_fields' from the task_data response:
             # The response custom_fields usually contains 'type_config' with 'options'.
             
             if 'type_config' in field and 'options' in field['type_config']:
                 try:
                     val_idx = int(field_value)
                     for opt in field['type_config']['options']:
                         if opt.get('orderindex') == val_idx:
                             processed['rfi_type'] = opt.get('name')
                             break
                 except:
                     processed['rfi_type'] = str(field_value)
             else:
                 processed['rfi_type'] = str(field_value)

        elif field_name == 'reference data':
             processed['drawing_ref'] = str(field_value)

        elif field_name == 'subject':
            processed['subject'] = str(field_value)
        elif field_name == 'project id':
            processed['project_id'] = str(field_value)
        elif field_name == 'work order id':
            processed['work_order_id'] = str(field_value)
        elif field_name == 'pmo item type':
            try:
                val_int = int(field_value)
                processed['pmo_item_type'] = pmo_item_type_map.get(val_int, str(field_value))
            except (ValueError, TypeError):
                processed['pmo_item_type'] = str(field_value)
        elif field_name == 'sequence':
            processed['sequence'] = str(field_value)
        elif field_name == 'start date':
            processed['start_date'] = str(field_value)
        elif field_name == 'submitted to':
             processed['submitted_to'] = str(field_value)

    # Get Assignees
    assignees = task_data.get('assignees', [])
    processed['assignees'] = [a.get('username') for a in assignees] if assignees else []
    processed['assignee_name'] = ", ".join(processed['assignees']) if processed['assignees'] else processed['creator_name']

    # Get Priority
    priority_data = task_data.get('priority')
    if priority_data:
        processed['priority'] = {
            'priority': priority_data.get('priority'),
            'color': priority_data.get('color')
        }
    else:
        processed['priority'] = None

    # RFI Type Color Mapping (Fallback if not in API)
    # Based on user image
    rfi_type_colors = {
        'field condition': '#FF7F00', # Orange
        'design conflict': '#00C853', # Green
        'clarification / missing info': '#FF0000', # Red (Approximated)
        'material substitution': '#00CED1', # Teal
        'constructability issue': '#1E90FF', # Blue
        'scope / schedule': '#4B0082', # Indigo/Dark
        'other': '#00BFFF' # Light Blue
    }
    
    # Try to get color from type_config if available, else use map
    processed['rfi_type_color'] = '#808080' # Default Gray
    
    if processed['rfi_type'] != 'N/A':
        val_lower = processed['rfi_type'].lower()
        # Partial match check since some labels are long
        for key, color in rfi_type_colors.items():
            if key in val_lower:
                processed['rfi_type_color'] = color
                break



    # Create Document ID
    processed['document_id'] = f"{processed['project_id']}-RFI-{processed['sequence']}"

    # Format dates
    try:
        if task_data.get('due_date'):
            processed['due_date'] = datetime.fromtimestamp(int(task_data.get('due_date')) / 1000).strftime("%m/%d/%Y")
        else:
            processed['due_date'] = 'N/A'
    except:
        processed['due_date'] = 'N/A'
        
    try:
        # Use date_created for Sent Date
        if task_data.get('date_created'):
            processed['sent_date'] = datetime.fromtimestamp(int(task_data.get('date_created')) / 1000).strftime("%m/%d/%Y")
        elif processed['start_date']:
            processed['sent_date'] = datetime.fromtimestamp(int(processed['start_date']) / 1000).strftime("%m/%d/%Y")
        else:
            processed['sent_date'] = 'N/A'
    except:
        processed['sent_date'] = 'N/A'

    # Get description - prioritize markdown_description
    processed['description'] = task_data.get('markdown_description') or task_data.get('description', 'N/A')
    
    return processed

def add_checkbox(pdf_path, x, y, size, checked, field_name):
    """Add a checkbox form field using pypdf."""
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    writer.append_pages_from_reader(reader)
    page = writer.pages[-1] # Assuming adding to last page
    
    page_height = page.mediabox.height
    mm_to_pt = 72 / 25.4
    
    x_pt = x * mm_to_pt
    y_pt = y * mm_to_pt
    size_pt = size * mm_to_pt
    
    rect_x1 = x_pt
    rect_y1 = float(page_height) - (y_pt + size_pt)
    rect_x2 = x_pt + size_pt
    rect_y2 = float(page_height) - y_pt
    
    # Checkbox Annotation
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
        NameObject("/F"): NumberObject(4), # Print
        NameObject("/Ff"): NumberObject(0), # Not readonly?
        # Appearance state
        NameObject("/V"): NameObject("/Yes") if checked else NameObject("/Off"),
        NameObject("/AS"): NameObject("/Yes") if checked else NameObject("/Off")
        # AP dictionary omitted to avoid invalid indirect object references. 
        # Reliance on NeedAppearances=True for basic widget rendering.
    })
    
    
    # Note: Creating proper appearance streams for checkboxes is complex in raw PDF.
    # However, setting /V and /AS usually allows viewers to render standard styling or handle interaction.
    # Some viewers strictly require /AP.
    # For simplicity, we define basic styling. 
    # Or rely on NeedAppearances=True in AcroForm.
    
    annotation.update({
        NameObject("/MK"): DictionaryObject({
            NameObject("/BC"): ArrayObject([NumberObject(0)]), # Border Black
            NameObject("/BG"): ArrayObject([NumberObject(1), NumberObject(1), NumberObject(1)]), # White
            NameObject("/CA"): TextStringObject("4"), # ZapfDingbats checkmark? or 8?
        }),
        NameObject("/DA"): TextStringObject("/ZapfDingbats 0 Tf 0 g")
    })
    
    # We'll use the _add_object method to handle indirect object creation properly
    annot_obj = writer._add_object(annotation)
    
    # Add to page
    if "/Annots" not in page:
        page[NameObject("/Annots")] = ArrayObject()
    page["/Annots"].append(annot_obj)
    
    # Add to AcroForm
    if "/AcroForm" not in writer.root_object:
        writer.root_object.update({
             NameObject("/AcroForm"): DictionaryObject({
                NameObject("/Fields"): ArrayObject(),
                NameObject("/DA"): TextStringObject("/Helv 12 Tf 0 g"),
                NameObject("/NeedAppearances"): BooleanObject(True),
                # Define resources for ZapfDingbats if needed?
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

def add_form_field(pdf_path, x, y, width, height, field_name="response"):
    """Add a text form field using pypdf."""
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    # Copy all pages
    writer.append_pages_from_reader(reader)
    
    # Get the page where we want the field (assuming last page for now)
    page = writer.pages[-1]
    
    # Get page size from reader
    page_height = page.mediabox.height
    
    # FPDF x, y are in mm. Convert to points.
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
        NameObject("/FT"): NameObject("/Tx"),  # Text Field
        NameObject("/T"): TextStringObject(field_name),
        NameObject("/Rect"): ArrayObject([
            NumberObject(rect_x1),
            NumberObject(rect_y1),
            NumberObject(rect_x2),
            NumberObject(rect_y2),
        ]),
        NameObject("/DA"): TextStringObject("/Helv 12 Tf 0 g"), # Appearance
        NameObject("/F"): NumberObject(4), # Print
        NameObject("/Ff"): NumberObject(4096), # Multiline
        NameObject("/MK"): DictionaryObject({
            NameObject("/BC"): ArrayObject([NumberObject(0)]), # Border Color: Black
            NameObject("/BG"): ArrayObject([NumberObject(1), NumberObject(1), NumberObject(1)]), # Background: White
        }),
    })
    
    # We'll use the _add_object method to handle indirect object creation properly
    annot_obj = writer._add_object(annotation)
    
    # Add to page
    if "/Annots" not in page:
        page[NameObject("/Annots")] = ArrayObject()
    page["/Annots"].append(annot_obj)
    
    # Add to AcroForm
    # Ensure AcroForm exists
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
