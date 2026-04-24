class ScenarioEngine:
    def __init__(self):
        self.running_tasks = []

    def stop_all(self):
        """Cancels all running tasks, clears link_overrides, flips FAILED->ACTIVE."""
        for task in self.running_tasks:
            task.cancel()
        self.running_tasks.clear()
        # Stub: logic to clear overrides and reset states would go here
