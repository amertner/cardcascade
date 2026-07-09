// CC Poster Export — iterate variable-mode combinations on the selected
// node (the Card), export each configuration as PNG, stream the files to
// the UI which zips them for download.

figma.showUI(__html__, { width: 400, height: 540 });

async function init() {
  const cols = await figma.variables.getLocalVariableCollectionsAsync();
  const sel = figma.currentPage.selection;
  figma.ui.postMessage({
    type: "init",
    collections: cols.map((c) => ({
      id: c.id,
      name: c.name,
      modes: c.modes.map((m) => ({ id: m.modeId, name: m.name })),
    })),
    selection: sel.length === 1 ? sel[0].name : null,
  });
}
init();

figma.on("selectionchange", () => {
  const sel = figma.currentPage.selection;
  figma.ui.postMessage({
    type: "selection",
    selection: sel.length === 1 ? sel[0].name : null,
  });
});

function cartesian(lists) {
  let out = [[]];
  for (const list of lists) {
    const next = [];
    for (const combo of out) for (const item of list) next.push(combo.concat([item]));
    out = next;
  }
  return out;
}

figma.ui.onmessage = async (msg) => {
  if (msg.type !== "export") return;
  const sel = figma.currentPage.selection;
  if (sel.length !== 1) {
    figma.ui.postMessage({ type: "error", text: "Select the Card first." });
    return;
  }
  const node = sel[0];

  const cols = [];
  for (const id of msg.collectionIds) {
    const c = await figma.variables.getVariableCollectionByIdAsync(id);
    if (c) cols.push(c);
  }
  if (!cols.length) {
    figma.ui.postMessage({ type: "error", text: "Pick at least one collection." });
    return;
  }

  const original = Object.assign({}, node.explicitVariableModes);
  const combos = cartesian(
    cols.map((c) => c.modes.map((m) => ({ col: c, mode: m })))
  );

  let done = 0;
  try {
    for (const combo of combos) {
      for (const { col, mode } of combo)
        node.setExplicitVariableModeForCollection(col, mode.modeId);
      await new Promise((r) => setTimeout(r, msg.settleMs || 150));

      let name = msg.pattern;
      for (const { col, mode } of combo)
        name = name.split("{" + col.name + "}").join(mode.name);
      // {text:Layer Name} -> contents of that text layer after the flip
      const tm = name.match(/\{text:([^}]+)\}/);
      if (tm) {
        let t = null;
        if ("findOne" in node)
          t = node.findOne((n) => n.type === "TEXT" && n.name === tm[1]);
        name = name.replace(tm[0], t ? t.characters : "");
      }
      name = name.replace(/[\\/:*?"<>|]/g, "_").trim();

      const bytes = await node.exportAsync({
        format: "PNG",
        constraint: { type: "SCALE", value: msg.scale || 1 },
      });
      done++;
      figma.ui.postMessage(
        { type: "file", name: name + ".png", bytes, done, total: combos.length });
    }
    figma.ui.postMessage({ type: "done", total: combos.length });
  } catch (e) {
    figma.ui.postMessage({ type: "error", text: String(e) });
  } finally {
    for (const [colId, modeId] of Object.entries(original)) {
      const c = await figma.variables.getVariableCollectionByIdAsync(colId);
      if (c) node.setExplicitVariableModeForCollection(c, modeId);
    }
  }
};
