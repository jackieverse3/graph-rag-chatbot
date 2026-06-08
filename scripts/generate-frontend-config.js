const fs = require("fs");
const path = require("path");

const apiUrl = process.env.VITE_API_URL || "http://127.0.0.1:8000";
const outputPath = path.join(__dirname, "..", "frontend", "config.js");

const contents = `// Auto-generated at build time — do not edit manually.
window.GRAPHMIND_CONFIG = {
  API_URL: ${JSON.stringify(apiUrl)},
};
`;

fs.writeFileSync(outputPath, contents, "utf8");
console.log(`Wrote frontend config with API_URL=${apiUrl}`);
