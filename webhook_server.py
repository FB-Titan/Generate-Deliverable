"""
Generate-Deliverable Webhook Server
Flask app that receives ClickUp automation webhooks, routes by PMO Item Type,
generates the appropriate PDF, and uploads it back to the task.
"""
import os
import time
import logging
from flask import Flask, request, jsonify

import config
from utils import (
    fetch_task_details, upload_attachment,
    update_custom_field, get_pmo_item_type
)
from generators.rfi import create_rfi_pdf
from generators.submittal import create_submittal_pdf

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Ensure output directory exists
os.makedirs(config.PDF_OUTPUT_DIR, exist_ok=True)

# PMO Item Type → generator mapping
GENERATORS = {
    config.PMO_TYPE_RFI: {
        'name': 'RFI',
        'prefix': 'RFI',
        'generator': create_rfi_pdf
    },
    config.PMO_TYPE_SUBMITTAL: {
        'name': 'Submittal',
        'prefix': 'SUB',
        'generator': create_submittal_pdf
    },
}


def extract_task_id(payload):
    """Extract task_id from various ClickUp webhook payload formats."""
    # Direct top-level
    if 'task_id' in payload:
        return payload['task_id']

    # Nested in task object
    if 'task' in payload:
        task = payload['task']
        if isinstance(task, dict) and 'id' in task:
            return task['id']

    # History items format
    if 'history_items' in payload:
        for item in payload['history_items']:
            if 'parent_id' in item:
                return item['parent_id']

    # Payload IS the task
    if 'id' in payload:
        return payload['id']

    return None


def generate_deliverable(task_id):
    """
    Core logic: fetch task → determine type → generate PDF → upload → update field.
    Returns a result dict.
    """
    # 1. Fetch task details
    logger.info("Processing task: %s", task_id)
    task_data = fetch_task_details(task_id)

    # 2. Determine PMO Item Type
    pmo_type = get_pmo_item_type(task_data)
    if pmo_type is None:
        raise ValueError(f"Task {task_id} has no PMO Item Type set")

    gen_config = GENERATORS.get(pmo_type)
    if gen_config is None:
        supported = [f"{v['name']} ({k})" for k, v in GENERATORS.items()]
        raise ValueError(
            f"PMO Item Type '{pmo_type}' not supported. "
            f"Supported: {', '.join(supported)}"
        )

    # 3. Generate PDF
    timestamp = int(time.time())
    filename = f"{gen_config['prefix']}_{task_id}_{timestamp}.pdf"
    output_path = os.path.join(config.PDF_OUTPUT_DIR, filename)

    logger.info("Generating %s PDF: %s", gen_config['name'], filename)
    gen_config['generator'](task_data, output_path)

    # 4. Upload to ClickUp
    logger.info("Uploading to ClickUp task %s", task_id)
    upload_attachment(task_id, output_path)

    # 5. Update "Generate PDF" field to "Generated ✓"
    if config.GENERATE_PDF_FIELD_ID:
        try:
            update_custom_field(
                task_id,
                config.GENERATE_PDF_FIELD_ID,
                config.GENERATED_OPTION_INDEX
            )
            logger.info("Set 'Generate PDF' field to 'Generated'")
        except Exception as e:
            logger.warning("Could not update Generate PDF field: %s", e)

    # 6. Clean up local file (optional — keep for debugging in dev)
    # os.remove(output_path)

    return {
        'task_id': task_id,
        'type': gen_config['name'],
        'filename': filename,
        'status': 'success'
    }


# --- Flask Routes ---

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Railway."""
    return jsonify({
        'status': 'healthy',
        'service': 'generate-deliverable',
        'supported_types': [v['name'] for v in GENERATORS.values()],
        'token_set': bool(config.CLICKUP_API_TOKEN),
        'field_id_set': bool(config.GENERATE_PDF_FIELD_ID)
    })


@app.route('/webhook/generate', methods=['POST'])
def webhook_generate():
    """
    ClickUp Automation webhook endpoint.
    Receives task_id, generates the appropriate PDF, uploads it.
    Accepts task_id from: JSON body, query params, or form data.
    """
    try:
        payload = request.get_json(force=True, silent=True) or {}
        logger.info("Webhook received - payload: %s", payload)
        logger.info("Webhook query params: %s", dict(request.args))

        # Try extracting task_id from multiple sources
        task_id = extract_task_id(payload)

        # Fallback: query parameters
        if not task_id:
            task_id = request.args.get('task_id')

        # Fallback: form data
        if not task_id:
            task_id = request.form.get('task_id')

        if not task_id:
            logger.warning("No task_id found — may be a test ping")
            return jsonify({
                'status': 'ok',
                'message': 'Webhook is active. No task_id provided.',
                'hint': 'Send {"task_id": "your_task_id"} in the body or ?task_id=xxx as query param'
            }), 200

        result = generate_deliverable(task_id)
        return jsonify(result), 200

    except ValueError as e:
        logger.error("Validation error: %s", e)
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Error processing webhook: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/regenerate/<task_id>', methods=['POST'])
def regenerate(task_id):
    """
    Manual re-generation endpoint.
    Call this when RFI/Submittal data has been updated.
    """
    try:
        result = generate_deliverable(task_id)
        return jsonify(result), 200
    except ValueError as e:
        logger.error("Validation error: %s", e)
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Error regenerating: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info("Starting Generate-Deliverable server on port %d", port)
    app.run(host='0.0.0.0', port=port, debug=True)
