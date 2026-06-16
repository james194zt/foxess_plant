#!/usr/bin/env node
/** Extract gear path data from agent transcript user message (Lottie SVG paste). */
const fs = require("fs");
const path = require("path");

const transcript = process.argv[2] || "C:/Users/James/.cursor/projects/c-Users-James-Documents-repo-HADashboard/agent-transcripts/e5fc66e9-671f-4aa4-a72f-dbbf52ca2461/e5fc66e9-671f-4aa4-a72f-dbbf52ca2461.jsonl";
const outFile = path.resolve(__dirname, "fox_alarm_cog_paths.json");

const lines = fs.readFileSync(transcript, "utf8").split("\n");
const line = lines.filter((l) => l.includes("0.8079075813293457,0.5893091559410095")).pop();
if (!line) {
  console.error("Could not find Lottie cog line in transcript");
  process.exit(1);
}
const obj = JSON.parse(line);
const text = obj.message.content.find((c) => c.type === "text")?.text || "";
const pathRe = /fill="rgb\((\d+),(\d+),(\d+)\)"[^>]*d="\s*([^"]+)"/g;
const paths = [];
let m;
while ((m = pathRe.exec(text))) {
  const hex =
    "#" +
    [m[1], m[2], m[3]]
      .map((n) => Number(n).toString(16).padStart(2, "0"))
      .join("");
  paths.push({ fill: hex, d: m[4].trim() });
}
if (paths.length < 4) {
  console.error("Expected 4 paths, got", paths.length);
  process.exit(1);
}
const out = {
  grayInner: paths[1].d,
  greenOuter: paths[2].d,
  greenInner: paths[3].d,
};
fs.writeFileSync(outFile, JSON.stringify(out));
console.log("Wrote", outFile, "path lengths:", Object.values(out).map((s) => s.length));
