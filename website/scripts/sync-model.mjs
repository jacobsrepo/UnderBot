import { readFile, writeFile, mkdir, copyFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import { existsSync } from "node:fs";
import { execFileSync } from "node:child_process";

const bundledSource = resolve("../models/r08");
const source = resolve(process.argv[2] || (existsSync(bundledSource) ? bundledSource : "../UnderBot-Personal"));
const destination = resolve("public/model");
await mkdir(destination, { recursive: true });
const viewer = await readFile(
  join(source, "underbot_description/viewer.html"),
  "utf8",
);
const match = viewer.match(
  /<script id="model-data" type="application\/json">([\s\S]*?)<\/script>/,
);
if (!match) throw new Error("Model data missing from the upstream viewer");
const data = JSON.parse(match[1]);
await writeFile(join(destination, "robot.json"), JSON.stringify(data));
for (const [from, to] of [
  ["underbot_description/viewer.html", "viewer.html"],
  ["underbot_description/docs/model_preview.png", "preview.png"],
  ["underbot_description/docs/floor_plan_R08.svg", "floor-plan.svg"],
  ["downloads/Underbot_WR141E_R08_200mm_description.zip", "Underbot-R08.zip"],
])
  await copyFile(join(source, from), join(destination, to));
let commit = execFileSync("git", ["-C", source, "rev-parse", "HEAD"], {
  encoding: "utf8",
}).trim();
// Bundled snapshots are inside the consolidated Git repository: use their
// recorded upstream commit rather than attributing the model to its HEAD.
const provenancePath = resolve("../docs/SOURCE_SNAPSHOTS.json");
if (source === bundledSource && existsSync(provenancePath)) {
  const provenance = JSON.parse(await readFile(provenancePath, "utf8"));
  commit = provenance.snapshots.find((entry) => entry.path === "models/r08").source_commit;
}
await writeFile(
  join(destination, "source.json"),
  JSON.stringify(
    {
      repository: "https://github.com/gautamsajeen/UnderBot-Personal",
      commit,
      revision: data.revision,
      description:
        "Unmodified upstream model and viewer; robot.json extracted from embedded viewer data.",
    },
    null,
    2,
  ) + "\n",
);
console.log(`Synced ${data.revision} model from ${commit}`);
