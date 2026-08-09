"""Split ONE combined assembly 3MF export (onshape_config.ASSEMBLY) into the
individual monochrome component 3MFs the pipeline consumes — so a whole cascade's
Box/Pushers/Holders/TokenHolder cost ONE translation call instead of one each.

Objects in the assembly map to component types by name (Box, Pusher, TokenHolder,
HalfTokenHolder, Holder). HalfTokenHolder rides only on Mat cascades; when absent
it's simply skipped. When a cascade has a distinct first-riser holder the assembly
names it
"FirstHolder" (separate from the default "Holder"), so the two are told apart by
NAME — no guessing. Older exports that lack the distinct name (both instances
called "Holder") fall back to a HEIGHT heuristic: height tracks card capacity
(~a card's thickness per card), so the taller/shorter holder is matched to the
cascade's Cards/First Riser vs Cards/Riser, with a sanity gate that refuses to
guess if the measured height gap doesn't match the expected card-count gap.

Emits, per component, a minimal single-object 3MF byte-string that
make_cascade.load_export accepts unchanged. Makes NO API calls.
"""
import io
import re
import zipfile

MODEL = "3D/3dmodel.model"

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
    'package.relationships+xml"/><Default Extension="model" ContentType='
    '"application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type='
    '"http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
    '</Relationships>')
_NS = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
       'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02"')
_IDENTITY = "1 0 0 0 1 0 0 0 1 0 0 0"


def _model_text(data):
    return zipfile.ZipFile(io.BytesIO(data)).read(MODEL).decode()


def _palette(model):
    g = re.search(r'<m:colorgroup[^>]*>(.*?)</m:colorgroup>', model, re.S)
    return re.findall(r'color="([^"]+)"', g.group(1)) if g else []


def _objects(model):
    """{id: {name, mesh, color}} for mesh-bearing parts (skips the container)."""
    palette = _palette(model)
    out = {}
    for om in re.finditer(r'<object id="(\d+)"([^>]*)>(.*?)</object>', model, re.S):
        oid, attrs, body = om.groups()
        if '<components>' in body:                 # assembly container, not a part
            continue
        mesh = re.search(r'<mesh>.*?</mesh>', body, re.S)
        if not mesh:
            continue
        name = re.search(r'name="([^"]*)"', attrs)
        pidx = re.search(r'pindex="(\d+)"', attrs)
        color = palette[int(pidx.group(1))] if pidx and palette else None
        out[oid] = {"name": name.group(1) if name else "",
                    "mesh": mesh.group(0), "color": color}
    return out


def _unit(model):
    m = re.search(r'unit="(\w+)"', model)
    return m.group(1) if m else "meter"


def _height_mm(mesh, unit):
    scale = 1000.0 if unit == "meter" else 1.0
    ys = [float(y) for _, y, _ in re.findall(
        r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', mesh)]
    return (max(ys) - min(ys)) * scale if ys else 0.0


def build_component_3mf(unit, name, mesh, color=None):
    """A minimal single-object 3MF (identity build item) that load_export reads."""
    color_res = (f'  <m:colorgroup id="1"><m:color color="{color}"/></m:colorgroup>\n'
                 if color else '')
    pref = ' pid="1" pindex="0"' if color else ''
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<model unit="{unit}" xml:lang="en-US" {_NS}>\n <resources>\n'
        f'{color_res}'
        f'  <object id="1" name="{name}" type="model"{pref}>\n   {mesh}\n'
        '  </object>\n </resources>\n'
        f' <build><item objectid="1" transform="{_IDENTITY}"/></build>\n</model>\n')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr(MODEL, model)
    return buf.getvalue()


def split(assembly_bytes, cards_first=None, cards_slot=None, card_mm=0.64):
    """Return {role: 3mf-bytes}. Roles: Box, Pusher, TokenHolder, Holder,
    Holder_first (only when the cascade has a distinct first-riser holder), and
    HalfTokenHolder (only when the assembly export contains it — Mat cascades).

    When the assembly names the first-riser holder "FirstHolder", the two holders
    are told apart by NAME. cards_first / cards_slot / card_mm are only the
    fallback for legacy exports whose two holders both share the name "Holder":
    cards_first / cards_slot are the cascade's Cards/First Riser and Cards/Riser
    slot, used to disambiguate them by height, and card_mm is a card's thickness
    (sleeved ≈ 0.64, unsleeved thinner) for the sanity gate.
    """
    model = _model_text(assembly_bytes)
    unit = _unit(model)
    by_name = {}
    for oid, o in _objects(model).items():
        by_name.setdefault(o["name"], []).append(o)

    out = {}
    # HalfTokenHolder is present only on Mat cascades; when absent the loop just
    # skips it, and non-Mat plans never request the role (see plan_exports).
    for role in ("Box", "Pusher", "TokenHolder", "HalfTokenHolder"):
        got = by_name.get(role, [])
        if len(got) > 1:
            raise ValueError(f"assembly has {len(got)} {role!r} objects, expected 1")
        if got:
            out[role] = build_component_3mf(unit, role, got[0]["mesh"], got[0]["color"])

    holders = by_name.get("Holder", [])
    firsts = by_name.get("FirstHolder", [])
    if firsts:
        # The model names the first-riser holder distinctly — no guessing.
        if len(firsts) > 1:
            raise ValueError(f"assembly has {len(firsts)} FirstHolder objects, expected 1")
        if len(holders) != 1:
            raise ValueError(f"assembly has FirstHolder plus {len(holders)} Holder "
                             "objects, expected exactly 1 default Holder")
        out["Holder"] = build_component_3mf(unit, "Holder", holders[0]["mesh"], holders[0]["color"])
        out["Holder_first"] = build_component_3mf(unit, "Holder", firsts[0]["mesh"], firsts[0]["color"])
    elif len(holders) == 1 or (holders and (not cards_first or cards_first == cards_slot)):
        o = holders[0]
        out["Holder"] = build_component_3mf(unit, "Holder", o["mesh"], o["color"])
    elif len(holders) == 2:
        # Legacy export: both instances share the name "Holder" — tell apart by height.
        ranked = sorted(holders, key=lambda o: _height_mm(o["mesh"], unit))
        short, tall = ranked[0], ranked[1]
        gap = _height_mm(tall["mesh"], unit) - _height_mm(short["mesh"], unit)
        expected = abs(cards_first - cards_slot) * card_mm
        if abs(gap - expected) > max(2.0, 0.4 * expected):
            raise ValueError(
                f"holder height gap {gap:.1f}mm doesn't match the expected "
                f"{expected:.1f}mm for |{cards_first}-{cards_slot}| cards "
                f"(x{card_mm}mm/card) — refusing to guess first vs default holder")
        first = tall if cards_first > cards_slot else short
        default = short if cards_first > cards_slot else tall
        out["Holder"] = build_component_3mf(unit, "Holder", default["mesh"], default["color"])
        out["Holder_first"] = build_component_3mf(unit, "Holder", first["mesh"], first["color"])
    elif holders:
        raise ValueError(f"assembly has {len(holders)} Holder objects, expected 1-2")
    return out
