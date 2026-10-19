import sys
import os

# Add parent directory to path so app can be imported cleanly in Vercel serverless context
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import app

# Expose app for Vercel Python serverless runtime
# Vercel's @vercel/python looks for 'app' or 'handler'
handler = app
