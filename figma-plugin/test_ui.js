// Headless test of ui.html's mode-selection logic:  node figma-plugin/test_ui.js
//
// A Figma plugin UI is a plain web page talking to code.js over postMessage,
// so the whole selection model can be driven from node with a minimal DOM
// stub — no Figma, no browser. It is the only way to check this without
// clicking through the real plugin.
const vm = require("vm"), fs = require("fs"), path = require("path");
const html = fs.readFileSync(path.join(__dirname, "ui.html"), "utf8");
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];

function El(tag) {
  return {
    tag, children: [], className: "", textContent: "", value: "", type: "",
    checked: false, indeterminate: false, disabled: false, scrollTop: 0,
    style: {}, onclick: null, onchange: null,
    set innerHTML(v) { if (v === "") this.children = []; },
    get innerHTML() { return ""; },
    appendChild(c) { this.children.push(c); return c; },
    append(...cs) { this.children.push(...cs); },
  };
}
const byId = {};
for (const id of ["selname","colbox","pattern","scale","settle","go","dl","log","allall","allnone"])
  byId[id] = El("div");
byId.pattern.value = "CC {Box Sizes}{Sleeves:Sleeved=S,Unsleeved=U}";
byId.scale.value = "1"; byId.settle.value = "150";

const sent = [];
const ctx = {
  document: { getElementById: (id) => byId[id], createElement: El },
  parent: { postMessage: (m) => sent.push(m.pluginMessage) },
  console,
};
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(js, ctx);

const SIZES = ["202","270","330","400","470"].map((n,i)=>({id:"s"+i,name:n}));
const COLLECTIONS = [
  { id: "c1", name: "Box Sizes", modes: SIZES },
  { id: "c2", name: "Sleeves", modes: [{id:"m0",name:"Sleeved"},{id:"m1",name:"Unsleeved"}] },
];
const init = (saved) => ctx.onmessage({ data: { pluginMessage:
  { type: "init", collections: COLLECTIONS, selection: "Card", saved } } });

const btn = () => byId.go.textContent;
const rows = () => byId.colbox.children;
const head = (i) => rows()[i].children[0];
const master = (i) => head(i).children[1];
const countText = (i) => head(i).children[3].textContent;
const modeBox = (i) => rows()[i].children[1];
const modeCb = (i, j) => modeBox(i).children[j].children[0];
const lastSave = () => [...sent].reverse().find((m) => m.type === "save");

let fails = 0;
const eq = (label, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) fails++;
  console.log(`${ok ? "ok  " : "FAIL"} ${label}${ok ? "" : `  got ${JSON.stringify(got)} want ${JSON.stringify(want)}`}`);
};

// --- 1. fresh open: everything ticked, collapsed, product = 5 x 2
init(null);
eq("fresh: button", btn(), "Export 10 combinations");
eq("fresh: master checked", [master(0).checked, master(0).indeterminate], [true, false]);
eq("fresh: count text", countText(0), "all 5");
eq("fresh: collapsed", modeBox(0).className, "modes hid");
eq("fresh: not disabled", byId.go.disabled, false);

// --- 2. 'none' then tick two sizes -> subset, tri-state, count 2 x 2
head(0).children[4].children[1].onclick();      // Box Sizes 'none'
eq("none: count", countText(0), "not iterated");
eq("none: product falls back to other axis", btn(), "Export 2 combinations");
modeCb(0, 1).checked = true; modeCb(0, 1).onclick();
modeCb(0, 3).checked = true; modeCb(0, 3).onclick();
eq("subset: count", countText(0), "2 of 5");
eq("subset: master indeterminate", [master(0).checked, master(0).indeterminate], [false, true]);
eq("subset: button", btn(), "Export 4 combinations");
eq("subset: saved in collection order", lastSave().state.axes.c1, ["s1","s3"]);
master(0).onclick();                            // partial master -> all
eq("master from partial: all", countText(0), "all 5");
master(0).onclick();                            // full master -> none
eq("master from all: none", countText(0), "not iterated");

// --- 3. pin Sleeves to one mode: all sizes, sleeved only
head(0).children[4].children[0].onclick();      // Box Sizes 'all'
modeCb(1, 1).checked = false; modeCb(1, 1).onclick();
eq("pin: button", btn(), "Export 5 combinations");
eq("pin: axes sent", (() => { byId.go.onclick(); return sent[sent.length-1].axes; })(),
   [{collectionId:"c1", modeIds:["s0","s1","s2","s3","s4"]}, {collectionId:"c2", modeIds:["m0"]}]);

// --- 4. nothing ticked at all
byId.allnone.onclick();
eq("empty: button", btn(), "Pick at least one mode");
eq("empty: disabled", byId.go.disabled, true);

// --- 5. reopen with remembered subset -> restored and auto-expanded
init({ axes: { c1: ["s1","s3"], c2: ["m0","m1"] }, pattern: "P", scale: 2, settleMs: 300 });
eq("restore: count", countText(0), "2 of 5");
eq("restore: partial expanded", modeBox(0).className, "modes");
eq("restore: full collapsed", modeBox(1).className, "modes hid");
eq("restore: button", btn(), "Export 4 combinations");
eq("restore: pattern/scale/settle", [byId.pattern.value, byId.scale.value, byId.settle.value], ["P", 2, 300]);

// --- 6. remembered mode ids that no longer exist
init({ axes: { c1: ["gone-1","gone-2"], c2: ["m1"] } });
eq("stale: falls back to all", countText(0), "all 5");
init({ axes: { c1: ["s2","gone"], c2: ["m1"] } });
eq("stale: keeps the survivor", countText(0), "1 of 5");

// --- 7. a collection absent from storage (added since) defaults to all
init({ axes: { c1: ["s2"] } });
eq("new collection: all", countText(1), "all 2");

console.log(fails ? `\n${fails} FAILURES` : "\nall passed");
process.exit(fails ? 1 : 0);
