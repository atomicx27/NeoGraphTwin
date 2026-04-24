from fastapi.testclient import TestClient
from src.ui.server import app as hub_app
from src.sim.network_app import app as sim_app
from src.sim.orchestrator_api import app as mano_app

hub_client = TestClient(hub_app)
sim_client = TestClient(sim_app)
mano_client = TestClient(mano_app)

def test_hub_ingest():
    response = hub_client.post("/api/v1/telemetry/ingest", json={"hostname": "test-router", "type": "SYSLOG", "message": "bgp session down"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_hub_reset():
    response = hub_client.post("/api/reset")
    assert response.status_code == 200

def test_sim_sync():
    response = sim_client.post("/api/infrastructure/sync")
    assert response.status_code == 200

def test_mano_patch():
    response = mano_client.post("/api/mano/patch_vnf", json={"vnf_hostname": "vnf-1"})
    assert response.status_code == 200
