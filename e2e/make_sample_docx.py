import sys

from docx import Document

d = Document()
d.add_paragraph("LAPORAN {{client}} / {{engagement}} / {{period}} / {{unknown_field}}")
d.add_paragraph("{{content}}")
d.save(sys.argv[1])
