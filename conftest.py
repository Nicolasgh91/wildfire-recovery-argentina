import sys
from pathlib import Path

# Add the root directory to the Python path so 'app' module can be imported
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))
