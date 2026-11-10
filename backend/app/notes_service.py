"""Logika catatan Markdown: templat bawaan, pembuatan catatan, versi."""
from .models import Engagement, Note, NoteTemplate, NoteVersion, User

MAX_VERSIONS = 100
MAX_PERSONAL_NOTES = 20

BUILTIN_NOTE_TEMPLATE = """# Catatan Pentester

> Gunakan data fiktif/izin tertulis saja. Catat hanya target yang tercantum pada ruang lingkup.

## 1. Ruang lingkup & izin
- [ ] RoE sudah disetujui
- [ ] Target dikonfirmasi sesuai ruang lingkup
- [ ] Jendela waktu pengujian dipahami

## 2. Recon / pengumpulan informasi
-

## 3. Enumerasi
| Target | Layanan/Port | Catatan |
|---|---|---|
| | | |

## 4. Pengujian & hasil
### Hipotesis
-
### Langkah yang dijalankan
1.

## 5. Bukti (nama berkas / tangkapan layar)
-

## 6. Calon temuan
| Judul | Perkiraan CVSS | Status |
|---|---|---|
| | | |

## 7. To-do
- [ ]
"""


def clean_text(text: str) -> str:
    return (text or "").replace("\x00", "").replace("\r\n", "\n")


def default_template_content(db) -> str:
    tpl = db.query(NoteTemplate).filter(NoteTemplate.is_default.is_(True)).first()
    return tpl.content if tpl else BUILTIN_NOTE_TEMPLATE


def create_note(db, engagement: Engagement, owner: User | None, title: str, content: str, actor: User) -> Note:
    note = Note(engagement_id=engagement.id, owner_id=owner.id if owner else None, title=title[:200],
                content=content, version=1, updated_by_id=actor.id)
    db.add(note)
    db.flush()
    db.add(NoteVersion(note_id=note.id, version=1, content=content, edited_by_id=actor.id))
    return note


def ensure_team_note(db, engagement: Engagement, actor: User) -> None:
    exists = db.query(Note.id).filter(Note.engagement_id == engagement.id, Note.owner_id.is_(None)).first()
    if not exists:
        create_note(db, engagement, None, "Catatan tim", default_template_content(db), actor)


def ensure_personal_note(db, engagement: Engagement, member: User, actor: User) -> None:
    exists = db.query(Note.id).filter(Note.engagement_id == engagement.id, Note.owner_id == member.id).first()
    if not exists:
        create_note(db, engagement, member, f"Catatan {member.full_name}"[:200], default_template_content(db), actor)


def save_version(db, note: Note, content: str, actor: User) -> None:
    note.version += 1
    note.content = content
    note.updated_by_id = actor.id
    db.add(NoteVersion(note_id=note.id, version=note.version, content=content, edited_by_id=actor.id))
    db.flush()
    old = [v for v in note.versions if v.version <= note.version - MAX_VERSIONS]
    for v in old:
        db.delete(v)
