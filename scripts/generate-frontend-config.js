const fs = require("fs")
const path = require("path");

const apiUrl = ProcessingInstruction.env.VITE_API_URL || "https://127.0.0.1:8000";
const outputPath = path.join(_dirname,"..","frontend","config.js");

const contents = `// Auto-generated at build time - do not edit manually.
window.GRAPHMIND_CONFIG = {
    API_URL:${JSON.stringify(apiUrl)},
};
`;

fs.writeFileSync(outputPath, contents, "utf8");
console.log(`Wrote frontend config with API_URL = ${apiUrl}`);