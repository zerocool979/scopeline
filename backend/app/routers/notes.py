import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..deps import NOTE_ROLES, STAFF, current_user, load_engagement, require_roles
from ..models import Note, NoteTemplate, NoteVersion, User
from ..notes_service import (
    BUILTIN_NOTE_TEMPLATE,
    MAX_PERSONAL_NOTES,
    clean_text,
    create_note,
    default_template_content,
    save_version,
)
from ..schemas import NoteCreate, NoteTemplateIn, NoteTemplateUpdate, NoteUpdate

router = APIRouter(prefix="/api", tags=["notes"])
MAX_TEMPLATE_BYTES = 200_000


# ---------------- Templat catatan ----------------
def _tpl_out(t: NoteTemplate, content: bool = False) -> dict:
    out = {"id": t.id, "name": t.name, "is_default": t.is_default, "size": len(t.content or ""),
           "updated_at": t.updated_at}
    if content:
        out["content"] = t.content
    return out


def _unset_defaults(db: Session) -> None:
    db.query(NoteTemplate).filter(NoteTemplate.is_default.is_(True)).update({"is_default": False})


def _get_tpl(db: Session, tid: int) -> NoteTemplate:
    t = db.get(NoteTemplate, tid)
    if not t:
        raise HTTPException(404, "Templat catatan tidak ditemukan")
    return t


def _unique_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    q = db.query(NoteTemplate.id).filter(NoteTemplate.name == name)
    if exclude_id:
        q = q.filter(NoteTemplate.id != exclude_id)
    if q.first():
        raise HTTPException(409, "Nama templat sudah dipakai")


@router.get("/note-templates")
def list_note_templates(db: Session = Depends(get_db), _: User = Depends(require_roles(*NOTE_ROLES))):
    rows = db.query(NoteTemplate).order_by(NoteTemplate.name).all()
    return {"builtin_available": True, "templates": [_tpl_out(t) for t in rows]}


@router.get("/note-templates/builtin")
def builtin_template(_: User = Depends(require_roles(*NOTE_ROLES))):
    return {"name": "Bawaan", "content": BUILTIN_NOTE_TEMPLATE}


@router.get("/note-templates/{tid}")
def get_note_template(tid: int, db: Session = Depends(get_db), _: User = Depends(require_roles(*NOTE_ROLES))):
    return _tpl_out(_get_tpl(db, tid), content=True)


@router.post("/note-templates", status_code=201)
def create_note_template(data: NoteTemplateIn, db: Session = Depends(get_db),
                         user: User = Depends(require_roles(*STAFF))):
    _unique_name(db, data.name)
    if data.make_default:
        _unset_defaults(db)
    t = NoteTemplate(name=data.name, content=clean_text(data.content), is_default=data.make_default,
                     updated_by_id=user.id)
    db.add(t)
    db.flush()
    audit.log(db, user, "note_template_created", "note_template", t.id, t.name)
    db.commit()
    return _tpl_out(t)


@router.post("/note-templates/upload", status_code=201)
def upload_note_template(file: UploadFile = File(...), name: str = Form(""), make_default: bool = Form(False),
                         db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    """Unggah templat catatan dalam format Markdown (.md)."""
    fname = file.filename or ""
    if not fname.lower().endswith((".md", ".markdown")):
        raise HTTPException(415, "Templat catatan harus berformat .md")
    raw = file.file.read(MAX_TEMPLATE_BYTES + 1)
    if len(raw) > MAX_TEMPLATE_BYTES:
        raise HTTPException(413, "Templat terlalu besar (maks 200 KB)")
    try:
        content = clean_text(raw.decode("utf-8-sig"))
    except UnicodeDecodeError:
        raise HTTPException(422, "Berkas harus berenkode UTF-8")
    tname = (name.strip() or Path(fname).stem)[:120]
    _unique_name(db, tname)
    if make_default:
        _unset_defaults(db)
    t = NoteTemplate(name=tname, content=content, is_default=make_default, updated_by_id=user.id)
    db.add(t)
    db.flush()
    audit.log(db, user, "note_template_uploaded", "note_template", t.id, f"{tname} ({len(raw)} B)")
    db.commit()
    return _tpl_out(t)


@router.put("/note-templates/{tid}")
def update_note_template(tid: int, data: NoteTemplateUpdate, db: Session = Depends(get_db),
                         user: User = Depends(require_roles(*STAFF))):
    t = _get_tpl(db, tid)
    if data.name is not None:
        _unique_name(db, data.name, t.id)
        t.name = data.name
    if data.content is not None:
        t.content = clean_text(data.content)
    t.updated_by_id = user.id
    audit.log(db, user, "note_template_updated", "note_template", t.id, t.name)
    db.commit()
    return _tpl_out(t)


@router.post("/note-templates/{tid}/default")
def set_default_note_template(tid: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    t = _get_tpl(db, tid)
    _unset_defaults(db)
    t.is_default = True
    audit.log(db, user, "note_template_default", "note_template", t.id, t.name)
    db.commit()
    return _tpl_out(t)


@router.delete("/note-templates/{tid}", status_code=204)
def delete_note_template(tid: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    t = _get_tpl(db, tid)
    audit.log(db, user, "note_template_deleted", "note_template", t.id, t.name)
    db.delete(t)
    db.commit()
    return Response(status_code=204)


# ---------------- Catatan engagement ----------------
def _can_read(user: User, note: Note) -> bool:
    if note.owner_id is None:
        return True  # catatan tim: seluruh anggota (peran NOTE_ROLES)
    return note.owner_id == user.id or user.role in STAFF


def _can_write(user: User, note: Note) -> bool:
    if note.owner_id is None:
        return user.role in ("admin", "lead", "tester")
    return note.owner_id == user.id and user.role in ("admin", "lead", "tester")


def _note_out(n: Note, user: User, content: bool = True) -> dict:
    out = {"id": n.id, "engagement_id": n.engagement_id, "title": n.title, "version": n.version,
           "scope": "team" if n.owner_id is None else "personal",
           "owner": n.owner.full_name if n.owner else None, "owner_id": n.owner_id,
           "updated_at": n.updated_at, "writable": _can_write(user, n)}
    if content:
        out["content"] = n.content
    return out


def _load_note(db: Session, user: User, nid: int) -> Note:
    n = db.get(Note, nid)
    if not n or user.role not in NOTE_ROLES:
        raise HTTPException(404, "Catatan tidak ditemukan")
    load_engagement(db, user, n.engagement_id)  # 404 bila bukan anggota
    if not _can_read(user, n):
        raise HTTPException(404, "Catatan tidak ditemukan")
    return n


@router.get("/engagements/{eid}/notes")
def list_notes(eid: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*NOTE_ROLES))):
    load_engagement(db, user, eid)
    rows = db.query(Note).filter(Note.engagement_id == eid).order_by(Note.owner_id.is_not(None), Note.id).all()
    return [_note_out(n, user, content=False) for n in rows if _can_read(user, n)]


@router.post("/engagements/{eid}/notes", status_code=201)
def create_personal_note(eid: int, data: NoteCreate, db: Session = Depends(get_db),
                         user: User = Depends(require_roles("admin", "lead", "tester"))):
    e = load_engagement(db, user, eid)
    if db.query(Note).filter(Note.engagement_id == eid, Note.owner_id == user.id).count() >= MAX_PERSONAL_NOTES:
        raise HTTPException(409, "Jumlah catatan pribadi sudah maksimum")
    if data.template_id:
        content = _get_tpl(db, data.template_id).content
    else:
        content = default_template_content(db)
    n = create_note(db, e, user, data.title, content, user)
    audit.log(db, user, "note_created", "note", n.id, f"engagement {e.id}: {n.title}")
    db.commit()
    return _note_out(n, user)


@router.get("/notes/{nid}")
def get_note(nid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _note_out(_load_note(db, user, nid), user)


@router.put("/notes/{nid}")
def update_note(nid: int, data: NoteUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = _load_note(db, user, nid)
    if not _can_write(user, n):
        raise HTTPException(403, "Anda tidak dapat mengubah catatan ini")
    if data.base_version != n.version:
        raise HTTPException(409, f"Catatan sudah diubah pihak lain (versi {n.version}). Muat ulang sebelum menyimpan.")
    content = clean_text(data.content)
    if data.title and data.title != n.title:
        n.title = data.title
    if content != n.content:
        save_version(db, n, content, user)
        audit.log(db, user, "note_updated", "note", n.id, f"v{n.version}")
    db.commit()
    return _note_out(n, user)


@router.delete("/notes/{nid}", status_code=204)
def delete_note(nid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = _load_note(db, user, nid)
    if n.owner_id is None or not (n.owner_id == user.id or user.role in STAFF):
        raise HTTPException(403, "Catatan tim tidak dapat dihapus")
    audit.log(db, user, "note_deleted", "note", n.id, n.title)
    db.delete(n)
    db.commit()
    return Response(status_code=204)


@router.get("/notes/{nid}/versions")
def note_versions(nid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = _load_note(db, user, nid)
    rows = db.query(NoteVersion).filter(NoteVersion.note_id == n.id).order_by(NoteVersion.version.desc()).all()
    return [{"version": v.version, "edited_by": v.editor.full_name if v.editor else None,
             "created_at": v.created_at, "size": len(v.content or "")} for v in rows]


@router.get("/notes/{nid}/versions/{ver}")
def note_version(nid: int, ver: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = _load_note(db, user, nid)
    v = db.query(NoteVersion).filter(NoteVersion.note_id == n.id, NoteVersion.version == ver).first()
    if not v:
        raise HTTPException(404, "Versi tidak ditemukan")
    return {"version": v.version, "content": v.content, "created_at": v.created_at}


@router.get("/notes/{nid}/export")
def export_note(nid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = _load_note(db, user, nid)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", n.title).strip("-")[:50] or f"catatan-{n.id}"
    audit.log(db, user, "note_exported", "note", n.id)
    db.commit()
    return Response(n.content.encode("utf-8"), media_type="text/markdown; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{slug}.md"', "X-Content-Type-Options": "nosniff"})
