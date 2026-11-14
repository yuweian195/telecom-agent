import { readFileSync } from "node:fs";
import { createServer } from "node:http";
import { resolve } from "node:path";
import { WebSocket, WebSocketServer } from "ws";

interface Alarm {
  alarm_id: string;
  alarm_time: string;
  ne_id: string;
  ne_name: string;
  ne_type: string;
  alarm_type: string;
  severity: string;
  description: string;
  region: string;
  vendor: string;
}

interface AnalysisSummary {
  run_id: string;
  total_alarms: number;
  cluster_count: number;
  compression_ratio: number;
  overall_severity: string;
  review_required: boolean;
  received_at: string;
}

const PORT = Number(process.env.PORT ?? 8081);
const OPS_API_URL = (process.env.OPS_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const CSV_PATH =
  process.env.ALARM_CSV ?? resolve(process.cwd(), "..", "data", "alarms", "incident_day.csv");
const STREAM_INTERVAL_MS = Number(process.env.STREAM_INTERVAL_MS ?? 180);
const BATCH_SIZE = Number(process.env.BATCH_SIZE ?? 20);
const WINDOW_SIZE = Number(process.env.WINDOW_SIZE ?? 120);
const BUFFER_SIZE = Number(process.env.BUFFER_SIZE ?? 80);

function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"' && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
      continue;
    }
    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }

  const [header, ...body] = rows.filter((item) => item.some((value) => value.trim() !== ""));
  if (!header) return [];
  return body.map((values) =>
    Object.fromEntries(header.map((key, index) => [key.trim(), values[index]?.trim() ?? ""])),
  );
}

function loadAlarms(): Alarm[] {
  const rows = parseCsv(readFileSync(CSV_PATH, "utf-8"));
  return rows
    .filter((row) => row.alarm_id && row.alarm_time && row.ne_id && row.severity)
    .map((row) => ({
      alarm_id: row.alarm_id,
      alarm_time: row.alarm_time,
      ne_id: row.ne_id,
      ne_name: row.ne_name ?? row.ne_id,
      ne_type: row.ne_type ?? "UNKNOWN",
      alarm_type: row.alarm_type ?? "UNKNOWN",
      severity: row.severity,
      description: row.description ?? "",
      region: row.region ?? "",
      vendor: row.vendor ?? "",
    }))
    .sort((left, right) => left.alarm_time.localeCompare(right.alarm_time));
}

const alarms = loadAlarms();
if (alarms.length === 0) {
  throw new Error(`No alarms loaded from ${CSV_PATH}`);
}

const buffer: Alarm[] = [];
const windowAlarms: Alarm[] = [];
let cursor = 0;
let pending = 0;
let flushing = false;
let batchCount = 0;
let lastAnalysis: AnalysisSummary | null = null;

const server = createServer((request, response) => {
  response.setHeader("Access-Control-Allow-Origin", "*");
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  const url = new URL(request.url ?? "/", `http://${request.headers.host ?? "localhost"}`);

  if (url.pathname === "/health") {
    response.writeHead(200);
    response.end(
      JSON.stringify({
        status: "ok",
        service: "alarm-gateway",
        alarms: alarms.length,
        buffered: buffer.length,
        window: windowAlarms.length,
        batches: batchCount,
        clients: wss.clients.size,
        last_analysis: lastAnalysis,
      }),
    );
    return;
  }

  if (url.pathname === "/api/alarms") {
    const limit = Math.max(1, Math.min(Number(url.searchParams.get("limit") ?? 20), BUFFER_SIZE));
    response.writeHead(200);
    response.end(JSON.stringify(buffer.slice(-limit)));
    return;
  }

  response.writeHead(404);
  response.end(JSON.stringify({ error: "not found" }));
});

const wss = new WebSocketServer({ server, path: "/ws/alarms" });

function broadcast(payload: unknown): void {
  const message = JSON.stringify(payload);
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  }
}

wss.on("connection", (socket) => {
  socket.send(JSON.stringify({ type: "hello", alarms: alarms.length, buffered: buffer.length }));
  if (buffer.length > 0) {
    socket.send(JSON.stringify({ type: "backlog", alarms: buffer.slice(-10) }));
  }
});

async function flushBatch(): Promise<void> {
  if (flushing || windowAlarms.length === 0) return;
  flushing = true;
  const payload = [...windowAlarms];
  try {
    const response = await fetch(`${OPS_API_URL}/ops/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alarms: payload, use_sample: false }),
      signal: AbortSignal.timeout(20000),
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    const run = (await response.json()) as {
      id: string;
      total_alarms: number;
      cluster_count: number;
      compression_ratio: number;
      overall_severity: string;
      review_required: boolean;
    };
    batchCount += 1;
    lastAnalysis = {
      run_id: run.id,
      total_alarms: run.total_alarms,
      cluster_count: run.cluster_count,
      compression_ratio: run.compression_ratio,
      overall_severity: run.overall_severity,
      review_required: run.review_required,
      received_at: new Date().toISOString(),
    };
    broadcast({ type: "analysis", analysis: lastAnalysis });
    console.log(
      `[batch ${batchCount}] ${payload.length} alarms -> run ${run.id} ` +
        `(${run.cluster_count} clusters, ${(run.compression_ratio * 100).toFixed(1)}%)`,
    );
  } catch (error) {
    console.error(`[batch] analysis failed: ${(error as Error).message}`);
    broadcast({ type: "gateway_error", message: (error as Error).message });
  } finally {
    flushing = false;
  }
}

const timer = setInterval(() => {
  const alarm = alarms[cursor];
  cursor = (cursor + 1) % alarms.length;
  buffer.push(alarm);
  if (buffer.length > BUFFER_SIZE) buffer.shift();
  windowAlarms.push(alarm);
  if (windowAlarms.length > WINDOW_SIZE) windowAlarms.shift();
  pending += 1;

  broadcast({ type: "alarm", alarm });
  if (pending >= BATCH_SIZE) {
    pending = 0;
    void flushBatch();
  }
}, STREAM_INTERVAL_MS);

const shutdown = () => {
  clearInterval(timer);
  void flushBatch().finally(() => {
    wss.close();
    server.close(() => process.exit(0));
  });
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

server.listen(PORT, () => {
  console.log(`alarm gateway listening on :${PORT}`);
  console.log(`streaming ${alarms.length} alarms -> ${OPS_API_URL}/ops/analyze every ${BATCH_SIZE} alarms`);
});
