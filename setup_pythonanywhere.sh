#!/bin/bash
# ============================================================
#  Swiss Job Finder — PythonAnywhere setup script
#  Run this in PythonAnywhere's Bash console:
#    bash setup_pythonanywhere.sh
# ============================================================

set -e

REPO_URL="https://github.com/jbertranr/primertestclaudecode.git"
PROJECT_DIR="$HOME/swiss-job-finder"
VENV_DIR="$PROJECT_DIR/.venv"

echo ""
echo "=== Swiss Job Finder — PythonAnywhere Setup ==="
echo ""

# 1. Clone or update the repository
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "[1/5] Updating existing repository..."
    git -C "$PROJECT_DIR" pull origin claude/initial-testing-setup-e5dFn
else
    echo "[1/5] Cloning repository..."
    git clone --branch claude/initial-testing-setup-e5dFn "$REPO_URL" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# 2. Create virtual environment
echo "[2/5] Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"

# 3. Install dependencies
echo "[3/5] Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r requirements_pythonanywhere.txt --quiet
echo "      Done."

# 4. Create .env file if it doesn't exist
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "[4/5] Creating .env file from template..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo ""
    echo "  *** ACTION REQUIRED ***"
    echo "  Edit $PROJECT_DIR/.env and fill in your credentials:"
    echo ""
    echo "    TELEGRAM_BOT_TOKEN=...   <-- from @BotFather on Telegram"
    echo "    TELEGRAM_CHAT_ID=...     <-- your personal Telegram chat ID"
    echo ""
    echo "  To edit the file, run:"
    echo "    nano $PROJECT_DIR/.env"
    echo ""
else
    echo "[4/5] .env file already exists — skipping."
fi

# 5. Initialise the database
echo "[5/5] Initialising database..."
"$VENV_DIR/bin/python" -c "
import sys; sys.path.insert(0, '$PROJECT_DIR')
from storage import database as db
db.init_db()
print('      Database ready at storage/jobs.db')
"

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo ""
echo "  1. Edit your credentials (if you haven't already):"
echo "       nano $PROJECT_DIR/.env"
echo ""
echo "  2. Enable Telegram in config.yaml:"
echo "       nano $PROJECT_DIR/config.yaml"
echo "       → set  notifications > telegram > enabled: true"
echo ""
echo "  3. Test a manual run:"
echo "       $VENV_DIR/bin/python $PROJECT_DIR/main.py"
echo ""
echo "  4. Set up the daily scheduled task on PythonAnywhere:"
echo "       → Go to:  Dashboard → Tasks tab"
echo "       → Add a Daily task at 08:00 with this command:"
echo ""
echo "       $VENV_DIR/bin/python $PROJECT_DIR/main.py"
echo ""
echo "======================================================="
