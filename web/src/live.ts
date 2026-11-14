import type { LiveAlarm, LiveAnalysis } from "./types";

type LiveStatus = "connecting" | "online" | "offline";

interface LiveHandlers {
  onAlarm: (alarm: LiveAlarm) => void;
  onAnalysis: (analysis: LiveAnalysis) => void;
  onStatus: (status: LiveStatus) => void;
}

export function connectAlarmStream(handlers: LiveHandlers): () => void {
  const explicit = import.meta.env.VITE_WS_URL as string | undefined;
  const url =
    explicit ??
    (import.meta.env.DEV
      ? "ws://127.0.0.1:8081/ws/alarms"
      : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8081/ws/alarms`);

  let socket: WebSocket | null = null;
  let disposed = false;
  let retry: number | undefined;

  const connect = () => {
    if (disposed) return;
    handlers.onStatus("connecting");
    socket = new WebSocket(url);

    socket.onopen = () => handlers.onStatus("online");
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data as string) as {
          type: string;
          alarm?: LiveAlarm;
          alarms?: LiveAlarm[];
          analysis?: LiveAnalysis;
        };
        if (message.type === "alarm" && message.alarm) {
          handlers.onAlarm(message.alarm);
        } else if (message.type === "backlog" && message.alarms) {
          message.alarms.forEach(handlers.onAlarm);
        } else if (message.type === "analysis" && message.analysis) {
          handlers.onAnalysis(message.analysis);
        }
      } catch {
        // Ignore malformed frames; the gateway is an optional live channel.
      }
    };
    socket.onclose = () => {
      handlers.onStatus("offline");
      if (!disposed) {
        retry = window.setTimeout(connect, 5000);
      }
    };
    socket.onerror = () => socket?.close();
  };

  connect();

  return () => {
    disposed = true;
    if (retry) window.clearTimeout(retry);
    socket?.close();
  };
}
