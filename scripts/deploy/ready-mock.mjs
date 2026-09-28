import { createServer } from "node:http";
import { readFileSync } from "node:fs";

const modeFile = process.env.MODE_FILE ?? "/tmp/pdoom-mode";

function mode() {
  try {
    return readFileSync(modeFile, "utf8").trim();
  } catch {
    return "ready";
  }
}

const server = createServer((request, response) => {
  const current = mode();
  if (current === "closed") {
    request.socket.destroy();
    return;
  }
  const path = request.url ?? "/";
  if (path.startsWith("/api/live")) {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ status: "live" }));
    return;
  }
  if (path.startsWith("/api/ready") || path.startsWith("/api/health")) {
    if (current === "ready") {
      response.writeHead(200, { "content-type": "application/json" });
      response.end(
        JSON.stringify({
          status: "ready",
          checks: { process: "live", database: "ok", migrations: "current" },
        }),
      );
      return;
    }
    const database = current === "db-down" ? "unavailable" : "ok";
    const migrations = current === "migration" ? "pending" : current === "db-down" ? "unknown" : "pending";
    response.writeHead(503, { "content-type": "application/json" });
    response.end(
      JSON.stringify({
        status: "not_ready",
        checks: { process: "live", database, migrations },
      }),
    );
    return;
  }
  if (current !== "ready") {
    response.writeHead(503, { "content-type": "text/plain" });
    response.end("app-not-ready");
    return;
  }
  response.writeHead(200, { "content-type": "text/plain" });
  response.end(process.env.BODY ?? "ok");
});

server.listen(3000, "0.0.0.0");
