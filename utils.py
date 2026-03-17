import requests
import os
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)


def fetch_task_details(task_id):
    """Fetch task details from ClickUp API, including markdown description."""
    url = f"{config.CLICKUP_API_BASE_URL}/task/{task_id}?include_markdown_description=true"
    headers = {"Authorization": config.CLICKUP_API_TOKEN}

    logger.info("Fetching task details for task ID: %s", task_id)
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch task: {response.status_code} {response.text}")


def upload_attachment(task_id, file_path):
    """Upload a file as an attachment to a ClickUp task."""
    url = f"{config.CLICKUP_API_BASE_URL}/task/{task_id}/attachment"
    headers = {"Authorization": config.CLICKUP_API_TOKEN}

    filename = os.path.basename(file_path)
    logger.info("Uploading attachment '%s' to task %s", filename, task_id)

    with open(file_path, 'rb') as f:
        files = {"attachment": (filename, f, "application/pdf")}
        response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        logger.info("Attachment uploaded successfully")
        return response.json()
    else:
        raise Exception(f"Failed to upload attachment: {response.status_code} {response.text}")


def update_custom_field(task_id, field_id, value):
    """Update a custom field value on a ClickUp task."""
    url = f"{config.CLICKUP_API_BASE_URL}/task/{task_id}/field/{field_id}"
    headers = {
        "Authorization": config.CLICKUP_API_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {"value": value}

    logger.info("Updating field %s on task %s to value: %s", field_id, task_id, value)
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        logger.info("Custom field updated successfully")
        return response.json()
    else:
        logger.error("Failed to update field: %s %s", response.status_code, response.text)
        raise Exception(f"Failed to update custom field: {response.status_code} {response.text}")


def get_pmo_item_type(task_data):
    """Extract the PMO Item Type orderindex from task data."""
    for field in task_data.get('custom_fields', []):
        if field.get('name', '').lower() == 'pmo item type':
            value = field.get('value')
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
    return None


def process_common_fields(task_data):
    """Process fields common to all deliverable types (RFI, Submittal, etc.)."""
    processed = {}
    custom_fields = task_data.get('custom_fields', [])

    # Defaults
    processed['subject'] = ''
    processed['project_id'] = ''
    processed['project_name'] = task_data.get('project', {}).get('name', '')
    processed['creator_name'] = task_data.get('creator', {}).get('username', 'Titan Electric')
    processed['work_order_id'] = ''
    processed['pmo_item_type'] = ''
    processed['sequence'] = ''
    processed['start_date'] = ''
    processed['drawing_ref'] = 'N/A'
    processed['submitted_to'] = ''
    processed['purchase_order_id'] = ''

    # PMO Item Type label mapping
    pmo_item_type_map = {
        0: "Task", 1: "RFI", 2: "Submittal", 3: "Change Request",
        4: "Subcontractor", 5: "Purchase Order", 6: "Threats",
        7: "Opportunities", 8: "Lesson Learned", 9: "Safety",
        10: "Milestone", 11: "Material", 12: "Activities", 13: "Permit"
    }

    for field in custom_fields:
        field_name = field.get('name', '').lower()
        field_value = field.get('value', '')
        if field_value is None:
            continue

        if field_name == 'subject':
            processed['subject'] = str(field_value)
        elif field_name == 'project id':
            processed['project_id'] = str(field_value)
        elif field_name == 'work order id':
            processed['work_order_id'] = str(field_value)
        elif field_name == 'purchase order id':
            processed['purchase_order_id'] = str(field_value)
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
        elif field_name == 'reference data':
            processed['drawing_ref'] = str(field_value)

    # Assignees
    assignees = task_data.get('assignees', [])
    processed['assignees'] = [a.get('username') for a in assignees] if assignees else []
    processed['assignee_name'] = (
        ", ".join(processed['assignees']) if processed['assignees']
        else processed['creator_name']
    )

    # Priority
    priority_data = task_data.get('priority')
    if priority_data:
        processed['priority'] = {
            'priority': priority_data.get('priority'),
            'color': priority_data.get('color')
        }
    else:
        processed['priority'] = None

    # Dates
    try:
        if task_data.get('due_date'):
            processed['due_date'] = datetime.fromtimestamp(
                int(task_data['due_date']) / 1000
            ).strftime("%m/%d/%Y")
        else:
            processed['due_date'] = 'N/A'
    except Exception:
        processed['due_date'] = 'N/A'

    try:
        if task_data.get('date_created'):
            processed['sent_date'] = datetime.fromtimestamp(
                int(task_data['date_created']) / 1000
            ).strftime("%m/%d/%Y")
        elif processed['start_date']:
            processed['sent_date'] = datetime.fromtimestamp(
                int(processed['start_date']) / 1000
            ).strftime("%m/%d/%Y")
        else:
            processed['sent_date'] = 'N/A'
    except Exception:
        processed['sent_date'] = 'N/A'

    # Description (prefer markdown)
    processed['description'] = (
        task_data.get('markdown_description') or task_data.get('description', 'N/A')
    )

    return processed
