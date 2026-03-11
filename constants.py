APP_NAME = "OIL Tracking Bot v2"

ROOT_OK_TEXT = "✅ Oil Tracking Bot v2 is up."
HEALTH_OK_TEXT = "✅ Health check passed."

HELP_TEXT = """\
Available commands:

General
/start - bot status
/help - show this help
/ping - quick bot check
/checksheet - verify Google Sheet connectivity
/sheetinfo - show connected worksheet title

User Commands
/history - view your recent OIL records
/summary - view your OIL summary
/clockoff - clock normal OIL
/claimoff - claim normal OIL
/clockphoff - clock PH OIL
/claimphoff - claim PH OIL
/clockspecialoff - clock Special OIL
/claimspecialoff - claim Special OIL
/newuser - import old OIL records for a brand-new user

Admin Commands
/startadmin - start admin PM session
/overview - view sector OIL overview
/adjustoil - manually adjust one user's OIL
/massadjustoff - mass adjust OIL for all tracked users

Notes
- For claim commands, the bot will show your current available balance first.
- PH and Special claims cannot go below available active balance.
- Normal OIL may go negative and will be flagged to admin where applicable.
- Use -quit anytime during an active flow to cancel.
"""

START_TEXT = """\
OIL Tracking Bot v2 is running.

Current build:
- baseline deployment ✅
- flow layer (Phase 2A) in progress
- ledger layer not rebuilt yet
"""
