import threading
import time
import logging

logger = logging.getLogger("spacexbot.alerts")

_jobs = {}
_running = False
_thread = None

def register_job(name, interval_seconds, func):
    """Register a timed alert job (name, interval, function)."""
    _jobs[name] = {
        "interval": interval_seconds,
        "func": func,
        "last_run": 0
    }
    logger.info(f"Registered alert job: {name} every {interval_seconds}s")

def _billing_job():
    from . import billalerts
    billalerts.run()

def _self_test_job():
    logger.debug("Alerts background loop self-test heartbeat OK.")

def _alert_loop():
    global _running
    logger.info("Alerts background loop started.")
    register_job("self_test", 60, _self_test_job)
    register_job("billing_plan", 600, _billing_job)
    
    while _running:
        now = time.time()
        for name, job in list(_jobs.items()):
            if now - job["last_run"] >= job["interval"]:
                try:
                    job["func"]()
                except Exception as e:
                    logger.error(f"Error in alert job {name}: {e}")
                job["last_run"] = time.time()
        time.sleep(5)

def start():
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_alert_loop, daemon=True)
    _thread.start()
    logger.info("Alerts thread initialized.")

def stop():
    global _running, _thread
    _running = False
    if _thread:
        _thread.join(timeout=2)
        _thread = None
    logger.info("Alerts thread stopped.")
