from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

app = FastAPI(title="MANO API", description="VNF lifecycle operations")

class MigrateRequest(BaseModel):
    vnf_hostname: str
    target_host_name: str

class PatchRequest(BaseModel):
    vnf_hostname: str

class VerifyRequest(BaseModel):
    vnf_hostname: str

# Dummy state management
vnf_states = {}

@app.post("/api/mano/migrate_vnf")
async def migrate_vnf(request: MigrateRequest):
    if vnf_states.get(request.vnf_hostname) == "PROVISIONING":
        raise HTTPException(status_code=400, detail="VNF already provisioning")

    vnf_states[request.vnf_hostname] = "PROVISIONING"

    # Simulate background delay and transition to VALIDATION
    async def finish_provisioning():
        await asyncio.sleep(2) # Normally 30-120s
        vnf_states[request.vnf_hostname] = "VALIDATION"

    asyncio.create_task(finish_provisioning())
    return {"status": "migrating", "vnf": request.vnf_hostname}

@app.post("/api/mano/patch_vnf")
async def patch_vnf(request: PatchRequest):
    vnf_states[request.vnf_hostname] = "PATCHING"

    # Simulate patch window
    async def finish_patching():
        await asyncio.sleep(2) # Normally 60s
        vnf_states[request.vnf_hostname] = "ACTIVE"

    asyncio.create_task(finish_patching())
    return {"status": "patching", "vnf": request.vnf_hostname}

@app.post("/api/mano/verify_health")
async def verify_health(request: VerifyRequest):
    state = vnf_states.get(request.vnf_hostname)
    if state != "VALIDATION":
        raise HTTPException(status_code=400, detail=f"VNF not in validation state. Current state: {state}")

    vnf_states[request.vnf_hostname] = "ACTIVE"
    return {"status": "verified", "vnf": request.vnf_hostname}
