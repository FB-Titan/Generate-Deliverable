import os
from dotenv import load_dotenv

load_dotenv()

# ClickUp Configuration
CLICKUP_API_TOKEN = os.getenv('CLICKUP_API_TOKEN')
CLICKUP_API_BASE_URL = "https://api.clickup.com/api/v2"

# Custom Field IDs
GENERATE_PDF_FIELD_ID = os.getenv('GENERATE_PDF_FIELD_ID', '')
try:
    GENERATED_OPTION_INDEX = int(os.getenv('GENERATED_OPTION_INDEX', '2'))
except (ValueError, TypeError):
    GENERATED_OPTION_INDEX = 2

# PDF Configuration
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'FB_Titan.png')
COMPANY_NAME = 'TITAN ELECTRIC, INC.'
COMPANY_ADDRESS_1 = '4752 W California Ave, Suite A1000'
COMPANY_ADDRESS_2 = 'Salt Lake City, UT 84104'

# Output
PDF_OUTPUT_DIR = os.getenv(
    'PDF_OUTPUT_DIR',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
)

# PMO Item Type Routing
PMO_TYPE_RFI = 1
PMO_TYPE_SUBMITTAL = 2
