"""
Demo Worker — mimics the real main.py behavior for client demo.
Shows the same log format, same loop, same steps — no real DB or API needed.
"""

import logging
import sys
import time
import random
from datetime import datetime

# --- Logger setup (same format as real main.py) ---
logger = logging.getLogger("main")
log_format = "[%(asctime)s][%(funcName)25s:%(lineno)4d] %(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_format)

# --- Fake data ---
FAKE_USERS = ["coachnickmoney", "cryptoking", "traderpro99", "wallstreetbull", "moonshot_alex"]
FAKE_ASSETS = ["BTC", "ETH", "TSLA", "AAPL", "SOL", "NVDA"]
FAKE_DIRECTIONS = ["LONG", "SHORT"]

POLL_INTERVAL = 5   # seconds to wait when no records found
DATE_CUTOFF = "2026-04-12"


def fake_score(record_id: str, username: str, asset: str, direction: str):
    """Mimics the 8-step scoring pipeline from real main.py"""
    overall_start = time.time()

    logger.info(f"[SCORE] Processing started for message ID: {record_id}")

    # STEP 1 — Get raw data
    time.sleep(random.uniform(0.2, 0.5))
    logger.info(f"[SCORE] Step 1 (Get raw data) took {random.uniform(0.2, 0.5):.2f}s")

    # STEP 2 — Get predictions
    time.sleep(random.uniform(0.3, 0.6))
    logger.info(f"[SCORE] Step 2 (Get predictions) took {random.uniform(0.3, 0.6):.2f}s")

    # STEP 3 — Prediction success
    time.sleep(random.uniform(0.2, 0.4))
    logger.info(f"[SCORE] Step 3 (Prediction success) took {random.uniform(0.2, 0.4):.2f}s")

    # STEP 4 — Batch updates
    time.sleep(random.uniform(0.3, 0.5))
    logger.info(f"[SCORE] Step 4 (Batches) took {random.uniform(0.3, 0.5):.2f}s")

    # STEP 5 — Update scores
    time.sleep(random.uniform(0.2, 0.4))
    logger.info(f"[SCORE] Step 5 (Scores) took {random.uniform(0.2, 0.4):.2f}s")

    # STEP 6 — Save API output
    time.sleep(random.uniform(0.1, 0.3))
    logger.info(f"[SCORE] Step 6 (Save API output) took {random.uniform(0.1, 0.3):.2f}s")

    # STEP 7 — Save prediction & score updates
    time.sleep(random.uniform(0.2, 0.4))
    logger.info(f"[SCORE] Step 7 (Save scores) took {random.uniform(0.2, 0.4):.2f}s")

    # STEP 8 — Mark as scored
    time.sleep(random.uniform(0.1, 0.2))
    logger.info(f"[SCORE] Step 8 (Mark raw data scored) took {random.uniform(0.1, 0.2):.2f}s")

    total_time = time.time() - overall_start
    logger.info(f"[SCORE] ✅ Completed {record_id} for user {username} [{asset} {direction}] in {total_time:.2f}s")
    return True


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  Twitter Prediction Scorer — Demo Worker")
    logger.info(f"  Polling for unscored records (date >= {DATE_CUTOFF})")
    logger.info("=" * 60)

    record_counter = 0
    no_record_streak = 0

    while True:
        # Randomly simulate: 70% chance a record is found, 30% chance queue is empty
        has_record = random.random() < 0.70

        if not has_record:
            no_record_streak += 1
            logger.info(f"No unscored records found. Retrying in {POLL_INTERVAL}s ...")
            time.sleep(POLL_INTERVAL)
            no_record_streak = 0
            continue

        # Generate a fake record
        record_counter += 1
        record_id = f"rec_{datetime.now().strftime('%H%M%S')}_{record_counter:04d}"
        username = random.choice(FAKE_USERS)
        asset = random.choice(FAKE_ASSETS)
        direction = random.choice(FAKE_DIRECTIONS)
        posted = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"Processing record {record_id} — @{username} | {asset} {direction} | posted: {posted}")

        try:
            fake_score(record_id, username, asset, direction)
            logger.info(f"Scored record {record_id} ✓")
        except Exception as e:
            logger.error(f"Failed to score record {record_id}: {e}")
            time.sleep(POLL_INTERVAL)
