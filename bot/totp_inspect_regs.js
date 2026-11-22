// Directly inspects the compiled totp_core's internal FSM `state` (4 bits)
// and `round` (7 bits) registers live via /redpiler inspect -- bypasses the
// world/flush path entirely (reads the compiled node struct and dumps it via
// Rust's debug! log, which lands in the SERVER's own stdout, not chat).
// Takes exactly two snapshots (before/after a long silent wait) to see
// whether the FSM is advancing at all, with minimal extra commands so as not
// to reproduce the //count-polling-stalls-progress bug from the reproducer
// investigation.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs_fork_server", port: parseInt(process.env.MC_PORT || "25565", 10), username: "totp_inspect", version: "1.20.4", auth: "offline" });
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));

function waitForChatMatch(regex, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`timeout waiting for /${regex.source}/`)), timeoutMs);
    function handler(m) {
      const match = m.toString().match(regex);
      if (match) { clearTimeout(timer); bot.removeListener("message", handler); resolve(match); }
    }
    bot.on("message", handler);
  });
}

// Local-frame (relative to first_pos) world offsets for state[0..3] and
// round[0..6], found by cross-referencing netlist.json's netnames (state,
// round) to their driving $_DFFE_PP_ cells' Q pin position in
// component_layout.json.
const STATE_OFFSETS = [
  [49, 217, 158], // state[0]
  [33, 205, 168], // state[1]
  [30, 214, 167], // state[2]
  [33, 214, 155], // state[3]
];
const ROUND_OFFSETS = [
  [103, 174, 187], // round[0]
  [81, 182, 158], // round[1]
  [100, 169, 194], // round[2]
  [93, 154, 180], // round[3]
  [79, 149, 166], // round[4]
  [65, 182, 158], // round[5]
  [63, 154, 159], // round[6]
];

async function inspectAt(bot, firstPos, offset, label) {
  const pos = firstPos.offset(offset[0], offset[1], offset[2]);
  await bot.creative.flyTo(pos.offset(1, 0, 0));
  await bot.lookAt(pos.offset(0.5, 0.5, 0.5));
  await sleep(300);
  console.log(`[inspect] ${label} at ${pos}`);
  bot.chat("/redpiler inspect");
  await sleep(500);
}

const FIRST_POS = new Vec3(
  parseInt(process.argv[2] || "400", 10),
  parseInt(process.argv[3] || "8", 10),
  parseInt(process.argv[4] || "277", 10)
);
const WAIT_SECONDS = parseInt(process.argv[5] || "60", 10);
const FRESH_LOAD = process.argv[6] === "load";

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps 1000000000");
  await sleep(500);

  let firstPos = FIRST_POS;
  if (FRESH_LOAD) {
    await bot.creative.flyTo(new Vec3(100, 70, 100));
    bot.chat("/load totp_core.litematic -c");
    const loadMsg = await waitForChatMatch(/Reloaded .* at (-?\d+), (-?\d+), (-?\d+)/, 60000);
    firstPos = new Vec3(parseInt(loadMsg[1], 10), parseInt(loadMsg[2], 10), parseInt(loadMsg[3], 10));
    console.log(`[load] first_pos = ${firstPos}`);
    await sleep(3000);

    async function chatAndConfirm(cmd, regex) {
      bot.chat(cmd);
      const m = await waitForChatMatch(regex, 10000);
      console.log(`[confirmed] ${cmd} -> ${m[0]}`);
    }
    await chatAndConfirm("/lever rst on", /rst is already on|Turned rst on/);
    await sleep(500);
    await chatAndConfirm("/lever rst off", /rst is already off|Turned rst off/);
    await sleep(500);
    await chatAndConfirm("/lever start on", /start is already on|Turned start on/);
  } else {
    console.log(`[resume] using first_pos = ${firstPos}, not re-driving inputs`);
  }

  console.log("[snapshot 1] state + round, right after start");
  for (let i = 0; i < STATE_OFFSETS.length; i++) await inspectAt(bot, firstPos, STATE_OFFSETS[i], `state[${i}]`);
  for (let i = 0; i < ROUND_OFFSETS.length; i++) await inspectAt(bot, firstPos, ROUND_OFFSETS[i], `round[${i}]`);

  console.log(`[wait] sleeping ${WAIT_SECONDS}s with zero further commands`);
  await sleep(WAIT_SECONDS * 1000);

  console.log("[snapshot 2] state + round, after the wait");
  for (let i = 0; i < STATE_OFFSETS.length; i++) await inspectAt(bot, firstPos, STATE_OFFSETS[i], `state[${i}]`);
  for (let i = 0; i < ROUND_OFFSETS.length; i++) await inspectAt(bot, firstPos, ROUND_OFFSETS[i], `round[${i}]`);

  console.log(`[first_pos_for_resume] ${firstPos.x} ${firstPos.y} ${firstPos.z}`);
  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
