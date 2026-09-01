from flask import Flask, render_template
import json
from pathlib import Path

app = Flask(__name__, template_folder='templates')
BASE_DIR = Path(__file__).resolve().parent.parent

@app.route('/krishna')
def krishna_story():
    """Serve the complete Krishna story page."""
    # Load Krishna data
    krishna_file = BASE_DIR / "data" / "scriptures" / "krishna_book.json"
    try:
        with open(krishna_file, 'r', encoding='utf-8') as f:
            krishna_entries = json.load(f)
    except Exception:
        krishna_entries = []
    
    return render_template('krishna.html', entries=krishna_entries)

@app.route('/health')
def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    port = int(__import__('os').getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
