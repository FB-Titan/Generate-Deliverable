"""
Local test entry point for Generate-Deliverable.
Uses the webhook_server's core logic to generate a PDF for a specific task.
"""
import os
import sys
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Default test task or accept from command line
    task_id = sys.argv[1] if len(sys.argv) > 1 else "86dvdkn82"

    from webhook_server import generate_deliverable

    try:
        result = generate_deliverable(task_id)
        print(f"\n✓ Success!")
        print(f"  Type:     {result['type']}")
        print(f"  File:     {result['filename']}")
        print(f"  Task ID:  {result['task_id']}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.error("Error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
