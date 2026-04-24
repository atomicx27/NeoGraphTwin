class TelemetryProducer:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.active_incidents = {}
        self.drifts = {}
        self.link_overrides = {}

    def trigger_incident(self, fault_id: str, hostname: str):
        self.active_incidents[hostname] = fault_id
        # Stub: Stagger syslog storm and send %%SYSTEM-1-ANOMALY
        # Stub: Send INTERNAL_UI_DEBUG with state=FAULTY

    def resolve_incident(self, hostname: str, fault_id: str):
        if hostname in self.active_incidents:
            del self.active_incidents[hostname]
        # Stub: Send INTERNAL_UI_DEBUG with state=ACTIVE and emit recovery syslog
