"""Точка входа PaintGuide.

Запуск:  python run.py
"""

from __future__ import annotations

import os

from paintguide import create_app

app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"\n  PaintGuide → http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=debug)
