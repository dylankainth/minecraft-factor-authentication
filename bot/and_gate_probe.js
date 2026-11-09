// AND gate: NOT(A), NOT(B), each through its own repeater onto a shared
// support block, one more inverter on top. See build_and_gate_test.py
// for the full layout and the reasoning behind each piece.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: "totp_bot",
  version: "1.20.4",
  auth: "offline",
});

bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });

const ANCHOR = new Vec3(840, 90, 840);
const PTS = {
  LEVER_A: ANCHOR.offset(2, 0, 0),
  TORCH_A: ANCHOR.offset(3, 1, 0),
  REP_A: ANCHOR.offset(3, 1, 2),
  LEVER_B: ANCHOR.offset(0, 0, 2),
  TORCH_B: ANCHOR.offset(0, 1, 3),
  REP_B: ANCHOR.offset(2, 1, 3),
  SF: ANCHOR.offset(3, 1, 3),
  TF: ANCHOR.offset(3, 2, 3),
  REP_F: ANCHOR.offset(3, 2, 4),
  LAMP_F: ANCHOR.offset(3, 2, 5),
};

function dump(label, pos) {
  const b = bot.blockAt(pos);
  console.log(`[block] ${label} @ ${pos}: name=${b.name} stateId=${b.stateId} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
}

function dumpAll(label) {
  console.log(`--- ${label} ---`);
  for (const [k, p] of Object.entries(PTS)) dump(k, p);
}

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos] ${bot.entity.position}`);

  bot.chat("//load and_gate_test.schem");
  await sleep(1500);
  bot.chat("//paste");
  await sleep(2500);

  const a = () => bot.activateBlock(bot.blockAt(PTS.LEVER_A));
  const b = () => bot.activateBlock(bot.blockAt(PTS.LEVER_B));

  console.log("=== AND gate truth table ===");
  dumpAll("A=off B=off");

  a(); await sleep(1500);
  dumpAll("A=on B=off");

  b(); await sleep(1500);
  dumpAll("A=on B=on");

  a(); await sleep(1500);
  dumpAll("A=off B=on");

  b(); await sleep(1500);
  dumpAll("A=off B=off (back to start)");

  // TF (the final torch) has been stuck at its as-pasted lit=true the
  // whole time -- SF never got powered in a way that then released again,
  // so TF never underwent a real transition and dustF/lampF downstream of
  // it are unverified. Drive A and B both back on to force SF to lose
  // power (both repeaters go false) and TF to genuinely flip, then check
  // whether that finally, correctly lights the lamp.
  a(); await sleep(1500);
  b(); await sleep(1500);
  dumpAll("A=on B=on, second time (TF should now have had a real transition)");

  // DUST_F correctly read power=15 there but LAMP_F still didn't light --
  // same symptom as the original wall-torch bug, but with a standing
  // torch this time (which worked fine in isolation for the plain NOT
  // gate). One more full off/on cycle: does lampF just need another kick,
  // or is this a structural break like the OR-gate merge was?
  a(); await sleep(1200);
  b(); await sleep(1200);
  a(); await sleep(1200);
  b(); await sleep(1200);
  dumpAll("A=on B=on, third time, after an extra full cycle");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
