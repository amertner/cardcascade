// CC Poster Export — iterate variable-mode combinations on the selected
// node (the Card), export each configuration as PNG, stream the files to
// the UI which zips them for download.
//
// The UI picks individual modes, not whole collections: it sends
// axes = [{collectionId, modeIds}] and the cartesian product is taken over
// exactly those modes. A collection with no modes picked is left alone; a
// collection with one mode picked is pinned to it for the whole run.

figma.showUI(__html__, { width: 400, height: 620 });

// Mode ids are only stable within a file, so scope the remembered picks to
// this document.
const storeKey = () => "cc-poster-export:" + figma.root.id;

async function init() {
  const cols = await figma.variables.getLocalVariableCollectionsAsync();
  const sel = figma.currentPage.selection;
  let saved = null;
  try {
    saved = await figma.clientStorage.getAsync(storeKey());
  } catch (e) {
    // storage is a convenience; a failure here must not block exporting
  }
  figma.ui.postMessage({
    type: "init",
    collections: cols.map((c) => ({
      id: c.id,
      name: c.name,
      modes: c.modes.map((m) => ({ id: m.modeId, name: m.name })),
    })),
    selection: sel.length === 1 ? sel[0].name : null,
    saved: saved || null,
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
  if (msg.type === "save") {
    try {
      await figma.clientStorage.setAsync(storeKey(), msg.state);
    } catch (e) {}
    return;
  }
  if (msg.type !== "export") return;
  const sel = figma.currentPage.selection;
  if (sel.length !== 1) {
    figma.ui.postMessage({ type: "error", text: "Select the Card first." });
    return;
  }
  const node = sel[0];

  // Resolve each axis against the live collection: modes can have been
  // renamed or deleted since the UI (or clientStorage) last saw them.
  const axes = [];
  for (const a of msg.axes || []) {
    const c = await figma.variables.getVariableCollectionByIdAsync(a.collectionId);
    if (!c) continue;
    const modes = c.modes.filter((m) => a.modeIds.indexOf(m.modeId) !== -1);
    if (modes.length) axes.push({ col: c, modes: modes });
  }
  if (!axes.length) {
    figma.ui.postMessage({ type: "error", text: "Pick at least one mode." });
    return;
  }

  const original = Object.assign({}, node.explicitVariableModes);
  const combos = cartesian(
    axes.map((a) => a.modes.map((m) => ({ col: a.col, mode: m })))
  );

  let done = 0;
  try {
    for (const combo of combos) {
      for (const { col, mode } of combo)
        node.setExplicitVariableModeForCollection(col, mode.modeId);
      await new Promise((r) => setTimeout(r, msg.settleMs || 150));

      let name = msg.pattern;
      for (const { col, mode } of combo) {
        // {Sleeves} -> mode name; {Sleeves:Sleeved=S,Unsleeved=U} -> mapped
        const re = new RegExp(
          "\\{" + col.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
          "(?::([^}]*))?\\}", "g");
        name = name.replace(re, (_, mapStr) => {
          if (mapStr) {
            for (const pair of mapStr.split(",")) {
              const i = pair.indexOf("=");
              if (i > 0 && pair.slice(0, i).trim() === mode.name)
                return pair.slice(i + 1).trim();
            }
          }
          return mode.name;
        });
      }
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
    // Restore only the collections this run touched. A collection that had
    // no explicit mode before must be cleared, not left pinned to whatever
    // the last combination happened to set.
    for (const { col } of axes) {
      if (Object.prototype.hasOwnProperty.call(original, col.id))
        node.setExplicitVariableModeForCollection(col, original[col.id]);
      else if ("clearExplicitVariableModeForCollection" in node)
        node.clearExplicitVariableModeForCollection(col);
    }
  }
};
