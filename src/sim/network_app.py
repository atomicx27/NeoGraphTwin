from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
import random
import datetime
import os

app = FastAPI(title="Infrastructure Simulator", description="Simulates network state and faults")
scheduler = AsyncIOScheduler()

HUB_URL = os.getenv("MGMT_HUB_URL", "http://localhost:8888")

async def push_telemetry(payload: dict):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{HUB_URL}/api/v1/telemetry/ingest", json=payload, timeout=2.0)
    except Exception:
        pass

async def emit_flow():
    payload = {
        "type": "NETFLOW",
        "hostname": "router-" + str(random.randint(1, 10)),
        "src_ip": f"10.0.{random.randint(1,255)}.{random.randint(1,255)}",
        "dst_ip": f"10.0.{random.randint(1,255)}.{random.randint(1,255)}",
        "bytes": random.randint(100, 10000),
        "timestamp": datetime.datetime.now().isoformat()
    }
    await push_telemetry(payload)

async def emit_ambient_syslog():
    payload = {
        "type": "SYSLOG",
        "hostname": "switch-" + str(random.randint(1, 10)),
        "message": "Routine background process completed.",
        "is_ambient": True,
        "timestamp": datetime.datetime.now().isoformat()
    }
    await push_telemetry(payload)

async def emit_metric():
    payload = {
        "type": "METRIC",
        "hostname": "server-" + str(random.randint(1, 10)),
        "cpu_usage": random.randint(10, 85),
        "mem_usage": random.randint(20, 80),
        "timestamp": datetime.datetime.now().isoformat()
    }
    await push_telemetry(payload)

@app.on_event("startup")
async def startup_event():
    scheduler.add_job(emit_flow, 'interval', seconds=0.5, id='emit_flow', replace_existing=True, max_instances=2)
    scheduler.add_job(emit_ambient_syslog, 'interval', seconds=5, id='emit_syslog', replace_existing=True)
    scheduler.add_job(emit_metric, 'interval', seconds=15, id='emit_metric', replace_existing=True)
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

@app.post("/api/infrastructure/sync")
async def sync_topology():
    return {"status": "syncing"}

@app.post("/api/infrastructure/reset")
async def reset_infrastructure():
    return {"status": "reset"}
