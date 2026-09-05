// build.mjs — generates js/config.js from the API_BASE_URL environment variable.
// Runs on Vercel via the buildCommand in vercel.json. Falls back to "" (same origin).
import { writeFileSync, readFileSync, existsSync } from "node:fs";

// Minimal .env loader (no dependency) so a local `npm run build` picks up a
// local .env file. process.env (e.g. Vercel dashboard vars) always wins.
function loadEnv() {
  const url = new URL("./.env", import.meta.url);
  if (!existsSync(url)) return;
  for (const line of readFileSync(url, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([\w.-]+)\s*=\s*(.*)\s*$/);
    if (!m) continue;
    const val = m[2].trim().replace(/^['"]|['"]$/g, "");
    if (process.env[m[1]] === undefined) process.env[m[1]] = val;
  }
}
loadEnv();

const apiBase = (process.env.API_BASE_URL || "https://cricket-world-cup-rag-assistant-backend.onrender.com").replace(/\/+$/, "");

const contents = `// AUTO-GENERATED at build time by build.mjs — do not edit by hand.
window.APP_CONFIG = {
  API_BASE_URL: ${JSON.stringify(apiBase)},
};
`;

writeFileSync(new URL("./js/config.js", import.meta.url), contents);
console.log(`[build] Wrote js/config.js with API_BASE_URL="${apiBase || "(same origin)"}"`);
