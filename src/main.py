import os
import time
import json
import logging
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from openai import OpenAI
from pymongo import MongoClient
from dotenv import load_dotenv

from lib.utlis import timeasit

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI        = os.environ["MONGO_URI"]
MONGO_DB         = os.environ["MONGO_DB"]
MONGO_COLLECTION = os.environ["MONGO_COLLECTION"]
OPENAI_API_KEY   = os.environ["OPENAI_API_KEY"]
POLL_INTERVAL    = 5
DATE_CUTOFF      = "2026-04-12"

# ── Clients ───────────────────────────────────────────────────────────────────
mongo  = MongoClient(MONGO_URI)
db     = mongo[MONGO_DB]
col    = db[MONGO_COLLECTION]
ai     = OpenAI(api_key=OPENAI_API_KEY)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scorer")

# ── Pipeline steps ────────────────────────────────────────────────────────────

@timeasit
def step1_fetch_record():
    return col.find_one(
        {"scored": False, "posted_at": {"$gte": DATE_CUTOFF}},
        sort=[("posted_at", 1)],
    )


def step2_extract_prediction(record):
    return {
        "record_id":   str(record["_id"]),
        "username":    record.get("username", "unknown"),
        "ticker":      record.get("ticker", "").upper(),
        "direction":   record.get("direction", "").upper(),
        "posted_at":   record.get("posted_at"),
        "target_date": record.get("target_date"),
    }


def step3_fetch_prices(ticker, posted_at, target_date):
    return yf.Ticker(ticker).history(start=posted_at, end=target_date, interval="1d")


def step4_openai_evaluate(prediction, prices_df):
    price_summary = (
        prices_df[["Open", "Close"]].tail(5).to_string()
        if not prices_df.empty
        else "No price data available."
    )
    prompt = (
        f"Prediction: @{prediction['username']} predicted {prediction['ticker']} "
        f"would go {prediction['direction']} from {prediction['posted_at']} "
        f"to {prediction['target_date']}.\n"
        f"Price data:\n{price_summary}\n"
        f'Did the prediction succeed? Answer with JSON: {{"success": true|false, "reason": "one sentence"}}'
    )
    response = ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=100,
    )
    return json.loads(response.choices[0].message.content)


def step5_batch_stats(username, success):
    rows = list(col.aggregate([
        {"$match": {"username": username, "scored": True}},
        {"$group": {
            "_id": None,
            "wins":  {"$sum": {"$cond": ["$score_result.success", 1, 0]}},
            "total": {"$sum": 1},
        }},
    ]))
    wins  = (rows[0]["wins"] if rows else 0) + (1 if success else 0)
    total = (rows[0]["total"] if rows else 0) + 1
    return {"wins": wins, "total": total, "win_rate": round(wins / total, 4)}


def step6_user_score(username, batch):
    return {
        "username":   username,
        "wins":       batch["wins"],
        "total":      batch["total"],
        "win_rate":   batch["win_rate"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def step7_save_results(record_id, openai_output, user_score, batch):
    from bson import ObjectId
    col.update_one(
        {"_id": ObjectId(record_id)},
        {"$set": {"score_result": openai_output, "batch_stats": batch, "user_score": user_score}},
    )


def step8_mark_scored(record_id):
    from bson import ObjectId
    col.update_one(
        {"_id": ObjectId(record_id)},
        {"$set": {"scored": True, "scored_at": datetime.now(timezone.utc).isoformat()}},
    )


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_pipeline(record):
    overall = time.time()

    t = time.time(); log.info(f"[SCORE] Step 1 (Get raw data) took {time.time()-t:.2f}s")
    t = time.time(); pred = step2_extract_prediction(record)
    log.info(f"[SCORE] Step 2 (Get predictions) took {time.time()-t:.2f}s")
    t = time.time(); prices = step3_fetch_prices(pred["ticker"], pred["posted_at"], pred["target_date"])
    log.info(f"[SCORE] Step 3 (Prediction success) took {time.time()-t:.2f}s")
    t = time.time(); openai_out = step4_openai_evaluate(pred, prices)
    log.info(f"[SCORE] Step 4 (Batches) took {time.time()-t:.2f}s")
    t = time.time(); batch = step5_batch_stats(pred["username"], openai_out.get("success", False))
    log.info(f"[SCORE] Step 5 (Scores) took {time.time()-t:.2f}s")
    t = time.time(); user_score = step6_user_score(pred["username"], batch)
    log.info(f"[SCORE] Step 6 (Save API output) took {time.time()-t:.2f}s")
    t = time.time(); step7_save_results(pred["record_id"], openai_out, user_score, batch)
    log.info(f"[SCORE] Step 7 (Save scores) took {time.time()-t:.2f}s")
    t = time.time(); step8_mark_scored(pred["record_id"])
    log.info(f"[SCORE] Step 8 (Mark raw data scored) took {time.time()-t:.2f}s")

    log.info(
        f"[SCORE] ✅ Completed {pred['record_id']} for user {pred['username']} "
        f"[{pred['ticker']} {pred['direction']}] in {time.time()-overall:.2f}s"
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  Twitter Prediction Scorer — Live Worker")
    print(f"  DB: {MONGO_DB}.{MONGO_COLLECTION} @ {MONGO_URI}")
    print(f"  Polling for unscored records (date >= {DATE_CUTOFF})")
    print("=" * 60)

    while True:
        try:
            record = step1_fetch_record()

            if not record:
                log.info(f"No unscored records found. Retrying in {POLL_INTERVAL}s ...")
                time.sleep(POLL_INTERVAL)
                continue

            record_id = str(record["_id"])
            log.info(
                f"Processing record {record_id} — @{record.get('username')} | "
                f"{record.get('ticker')} {record.get('direction')} | posted: {record.get('posted_at')}"
            )
            run_pipeline(record)
            log.info(f"Scored record {record_id} ✓")

        except KeyboardInterrupt:
            log.info("Scorer stopped by user.")
            break
        except Exception as e:
            log.error(f"Pipeline error: {e}", exc_info=True)
            time.sleep(POLL_INTERVAL)
