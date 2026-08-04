"""Local 3MF surgery for the exporter.

Onshape exports a part studio as a single 3D/3dmodel.model with flat <object>
elements (each a named part) and matching <build><item> references — no
sub-model files. A whole-studio export therefore includes imported reference
parts (e.g. a Holder imported into the Topper studio) that don't belong in the
component; strip_objects() removes those by name, keeping the main part and the
letter parts. No API calls.
"""
import io
import re
import zipfile

MODEL = "3D/3dmodel.model"


def object_names(data):
    """List the <object> names in a 3MF (order as stored)."""
    model = zipfile.ZipFile(io.BytesIO(data)).read(MODEL).decode()
    return [m.group(1) for m in re.finditer(r'<object\b[^>]*\bname="([^"]*)"',
                                            model)]


def strip_objects(data, drop_names):
    """Return (new 3MF bytes, dropped names) with every <object> whose name is in
    drop_names removed along with its build item."""
    zin = zipfile.ZipFile(io.BytesIO(data))
    model = zin.read(MODEL).decode()
    dropped = []
    for m in list(re.finditer(r'<object\b([^>]*)>', model)):
        nm = re.search(r'name="([^"]*)"', m.group(1))
        idm = re.search(r'id="([^"]*)"', m.group(1))
        if not (nm and idm and nm.group(1) in drop_names):
            continue
        oid = re.escape(idm.group(1))
        model = re.sub(rf'\s*<object\b[^>]*\bid="{oid}".*?</object>', "",
                       model, count=1, flags=re.S)
        model = re.sub(rf'\s*<item\b[^>]*\bobjectid="{oid}"[^>]*/>', "",
                       model, count=1)
        dropped.append(nm.group(1))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in zin.namelist():
            zout.writestr(n, model if n == MODEL else zin.read(n))
    return out.getvalue(), dropped
