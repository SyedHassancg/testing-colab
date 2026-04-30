import time
import random
from datetime import datetime

from lib.utlis import timeasit

FAKE_USERS      = ["coachnickmoney", "cryptoking", "traderpro99", "wallstreetbull", "moonshot_alex"]
FAKE_ASSETS     = ["BTC", "ETH", "TSLA", "AAPL", "SOL", "NVDA"]
FAKE_DIRECTIONS = ["LONG", "SHORT"]
POLL_INTERVAL   = 5
DATE_CUTOFF     = "2026-04-12"

STEPS = [
    "Get raw data",
    "Get predictions",
    "Prediction success",
    "Batches",
    "Scores",
    "Save API output",
    "Save scores",
    "Mark raw data scored",
]


@timeasit
def fake_score(record_id, username, asset, direction):
    print(f"[SCORE] Processing started for message ID: {record_id}")
    for i, name in enumerate(STEPS, 1):
        delay = random.uniform(0.1, 0.6)
        time.sleep(delay)
        print(f"[SCORE] Step {i} ({name}) took {delay:.2f}s")
    print(f"[SCORE] ✅ Completed {record_id} for user {username} [{asset} {direction}]")


if __name__ == "__main__":
    print("=" * 60)
    print("  Twitter Prediction Scorer — Demo Worker")
    print(f"  Polling for unscored records (date >= {DATE_CUTOFF})")
    print("=" * 60)

    record_counter = 0
    while True:
        if random.random() >= 0.70:
            print(f"No unscored records found. Retrying in {POLL_INTERVAL}s ...")
            time.sleep(POLL_INTERVAL)
            continue

        record_counter += 1
        record_id = f"rec_{datetime.now().strftime('%H%M%S')}_{record_counter:04d}"
        username  = random.choice(FAKE_USERS)
        asset     = random.choice(FAKE_ASSETS)
        direction = random.choice(FAKE_DIRECTIONS)
        posted    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"Processing record {record_id} — @{username} | {asset} {direction} | posted: {posted}")
        try:
            fake_score(record_id, username, asset, direction)
            print(f"Scored record {record_id} ✓")
        except Exception as e:
            print(f"Failed to score record {record_id}: {e}")
            time.sleep(POLL_INTERVAL)
