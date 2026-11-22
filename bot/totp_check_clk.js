// Resumes the already-running totp_core (no re-drive of inputs) and samples
// the clk net's output wire repeatedly via /redpiler inspect, with real
// wall-clock gaps between samples, to see whether the self-generated ring
// oscillator is actually toggling at all. If every sample reads the same
// powered value, clk is stuck -- which alone would explain state/round never
// advancing regardless of how fast ticks are processed.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs_fork_server", port: parseInt(process.env.MC_PORT || "25565", 10), username: "totp_clk", version: "1.20.4", auth: "offline" });
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));

const FIRST_POS = new Vec3(
  parseInt(process.argv[2] || "400", 10),
  parseInt(process.argv[3] || "8", 10),
  parseInt(process.argv[4] || "277", 10)
);
const CLK_OFFSET = [126, 79, 216];
const SAMPLES = parseInt(process.argv[5] || "6", 10);
const GAP_MS = parseInt(process.argv[6] || "3000", 10);

bot.once("login", async () => {
  console.log("[login] ok -- resuming, checking clk toggling");
  await sleep(1500);
  bot.chat("/gamemode creative");
  await sleep(500);

  const clkPos = FIRST_POS.offset(CLK_OFFSET[0], CLK_OFFSET[1], CLK_OFFSET[2]);
  const approaches = [
    [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1],
    [1, 1, 0], [-1, 1, 0], [0, 1, 1], [0, 1, -1], [1, -1, 0], [0, -1, 1],
  ];
  for (let i = 0; i < SAMPLES; i++) {
    const a = approaches[i % approaches.length];
    await bot.creative.flyTo(clkPos.offset(a[0], a[1], a[2]));
    await bot.lookAt(clkPos.offset(0.5, 0.5, 0.5));
    await sleep(300);
    console.log(`[sample ${i}] t=${Date.now()} approach=${a} inspecting clk at ${clkPos}`);
    bot.chat("/redpiler inspect");
    await sleep(GAP_MS);
  }

  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
