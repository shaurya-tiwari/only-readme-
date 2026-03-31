const apiKey = process.env.STITCH_API_KEY || process.env.GOOGLE_STITCH_API_KEY;

if (!apiKey) {
  console.error(
    "Missing STITCH_API_KEY or GOOGLE_STITCH_API_KEY in environment.",
  );
  process.exit(1);
}

const prompt = process.argv.slice(2).join(" ").trim();

if (!prompt) {
  console.error("Usage: node scripts/stitch_generate.mjs \"<prompt>\"");
  process.exit(1);
}

const response = await fetch("https://api.stitch.google/generate", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ prompt }),
});

const text = await response.text();

if (!response.ok) {
  console.error(`Stitch request failed: ${response.status}`);
  console.error(text);
  process.exit(1);
}

try {
  const data = JSON.parse(text);
  console.log(JSON.stringify(data, null, 2));
} catch {
  console.log(text);
}
