from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from typing import Dict, List, Any
import datetime
import httpx
import asyncio
import re

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.core.llm import generate

app = FastAPI(title="Hub Server", description="UI Server and Telemetry Ingestion")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        self.active_alarms: List[Dict[str, Any]] = []
        self.active_debug_faults: List[Dict[str, Any]] = []
        self.simulation_mode: str = "NORMAL"
        self.last_seen: Dict[str, float] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = {"is_human": False}

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    async def identify(self, websocket: WebSocket, is_human: bool):
        if websocket in self.active_connections:
            self.active_connections[websocket]["is_human"] = is_human
            if is_human:
                await self.send_personal_message(
                    {"type": "SYNC_STATE", "alarms": self.active_alarms, "faults": self.active_debug_faults, "mode": self.simulation_mode},
                    websocket
                )

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict, debug_only: bool = False):
        for connection, metadata in self.active_connections.items():
            if debug_only and not metadata.get("is_human", False):
                continue
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

class HonestMediationEngine:
    """Regex + LLM-based TMF-642 normalisation engine."""

    def __init__(self):
        self.rules = [
            (re.compile(r'(?i)bgp.*(down|idle|active)'), 'Routing alarm — BGP Session Down'),
            (re.compile(r'(?i)ospf.*(down|lost|init)'), 'Routing alarm — OSPF Adjacency Lost'),
            (re.compile(r'(?i)(link|interface|eth).*down'), 'Equipment alarm — Physical Link Down'),
            (re.compile(r'(?i)cpu.*>.*90'), 'Performance alarm — CPU Threshold Exceeded'),
            (re.compile(r'(?i)%%SYSTEM-1-ANOMALY'), 'Diagnostic alarm — Opaque Anomaly'),
        ]

    def process(self, payload: dict) -> dict:
        msg = payload.get("message", "")
        hostname = payload.get("hostname", "unknown")

        alarm_type = None
        for pattern, a_type in self.rules:
            if pattern.search(msg):
                alarm_type = a_type
                break

        # If regex missed it but it looks important (e.g. error, fail), consult LLM
        if not alarm_type and any(kw in msg.lower() for kw in ['error', 'fail', 'critical']):
            try:
                prompt = f"Categorize this network syslog message into a standard TMF-642 alarm type (e.g. Equipment alarm, Processing error alarm). Message: '{msg}'. Reply with ONLY the alarm type string."
                alarm_type = generate(prompt).strip()
            except Exception as e:
                print(f"LLM mediation failed: {e}")

        if alarm_type:
            timestamp = int(datetime.datetime.now().timestamp())
            return {
                "id": f"ALM-{alarm_type.replace(' ', '_')}-{timestamp}-{hostname}",
                "type": "TMF_ALARM",
                "alarm_type": alarm_type,
                "hostname": hostname,
                "message": msg,
                "timestamp": timestamp
            }
        return None

mediation_engine = HonestMediationEngine()

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "IDENTIFY:HUMAN_UI":
                await manager.identify(websocket, True)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/v1/telemetry/ingest")
async def ingest_telemetry(request: Request):
    payload = await request.json()
    hostname = payload.get("hostname", "unknown")

    # 1. Update heartbeat
    manager.last_seen[hostname] = datetime.datetime.now().timestamp()

    # 2. Track simulation mode
    if "simulation_mode" in payload:
        manager.simulation_mode = payload["simulation_mode"]

    # 3. Track debug faults
    if payload.get("type") == "INTERNAL_UI_DEBUG":
        if payload.get("state") == "FAULTY":
            manager.active_debug_faults.append(payload)
        elif payload.get("state") == "ACTIVE":
            manager.active_debug_faults = [f for f in manager.active_debug_faults if f.get("hostname") != hostname or f.get("fault_id") != payload.get("fault_id")]

    # 4 & 5. Mediate SYSLOG/METRIC to TMF-642 Alarms
    if payload.get("type") in ["SYSLOG", "METRIC"]:
        alarm = mediation_engine.process(payload)
        if alarm:
            manager.active_alarms.append(alarm)
            await manager.broadcast(alarm)

    # 6. Broadcast raw event
    is_debug = payload.get("type") == "INTERNAL_UI_DEBUG"
    await manager.broadcast(payload, debug_only=is_debug)

    return {"status": "ok"}

@app.post("/api/reset")
async def reset_network():
    manager.active_alarms.clear()
    manager.active_debug_faults.clear()

    # Notify simulator
    try:
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:9999/api/infrastructure/reset", timeout=10.0)
    except Exception as e:
        print(f"Failed to reset simulator: {e}")

    # Broadcast reset to clients
    await manager.broadcast({"type": "SYSTEM_RESET"})

    return {"status": "resetting"}
