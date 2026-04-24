let ws = null;

function connect() {
    ws = new WebSocket("ws://localhost:8888/ws/events");

    ws.onopen = () => {
        console.log("WebSocket connected");
        ws.send("IDENTIFY:HUMAN_UI");
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        routeEvent(data);
    };

    ws.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting in 3s...");
        setTimeout(connect, 3000);
    };
}

function routeEvent(data) {
    if (data.type === "SYNC_STATE") {
        console.log("State synced:", data);
    } else if (data.type === "TMF_ALARM") {
        console.log("Alarm received:", data);
    } else if (data.type === "SYSTEM_RESET") {
        console.log("System reset broadcast received.");
    }
}

connect();
