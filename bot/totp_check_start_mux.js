// Checks whether 'start's signal actually reaches its ONLY consumer in the
// netlist -- a MUX select input -- or whether it's stuck powered:false there
// despite the start LEVER itself reading powered:true. A mismatch would mean
// a signal-integrity break (dust decay, missing repeater) between the lever
// and the FSM logic, not a clock or FSM bug.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs_fork_server", port: parseInt(process.env.MC_PORT || "25565", 10), username: "totp_startmux", version: "1.20.4", auth: "offline" });
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));

const FIRST_POS = new Vec3(
  parseInt(process.argv[2] || "400", 10),
  parseInt(process.argv[3] || "8", 10),
  parseInt(process.argv[4] || "277", 10)
);
const MUX_S_OFFSET = [21, 190, 180];
const approaches = [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1],[1,1,0],[0,1,1]];

bot.once("login", async () => {
  console.log("[login] ok -- checking start's MUX-select consumer");
  await sleep(1500);
  bot.chat("/gamemode creative");
  await sleep(500);

  const pos = FIRST_POS.offset(MUX_S_OFFSET[0], MUX_S_OFFSET[1], MUX_S_OFFSET[2]);
  for (const a of approaches) {
    await bot.creative.flyTo(pos.offset(a[0], a[1], a[2]));
    await bot.lookAt(pos.offset(0.5, 0.5, 0.5));
    await sleep(300);
    console.log(`[inspect] start-mux-S approach=${a} at ${pos}`);
    bot.chat("/redpiler inspect");
    await sleep(700);
  }

  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
