"""Halaman sampul, pengesahan, abstrak, dan kerangka daftar (isi, tabel, gambar, lampiran)."""
from __future__ import annotations

import os

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from docs.docx_kit import TEXT_W_CM, add_runs
from docs.lap_common import DIREKTUR, JUDUL, NIDN_KETUA, ROOT, SP3, TIM, f, rp

LOGO = os.path.join(ROOT, "docs", "template", "logo_pem.png")


def cpar(doc, text="", size=12, bold=False, align="c", before=0, after=0, single=True, caps=False):
    p = doc.add_paragraph()
    add_runs(p, text.upper() if caps else text, size=size, bold=bold)
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0)
    pf.alignment = {"c": WD_ALIGN_PARAGRAPH.CENTER, "l": WD_ALIGN_PARAGRAPH.LEFT,
                    "j": WD_ALIGN_PARAGRAPH.JUSTIFY, "r": WD_ALIGN_PARAGRAPH.RIGHT}[align]
    pf.space_before = Pt(before); pf.space_after = Pt(after)
    if single:
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    return p


def _no_borders(tbl):
    tblPr = tbl._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement(f"w:{e}"); x.set(qn("w:val"), "nil"); b.append(x)
    tblPr.append(b)


def _widths(tbl, widths):
    from docs.docx_kit import _fixed_layout
    _fixed_layout(tbl._tbl, widths)
    for row in tbl.rows:
        for c, w in zip(row.cells, widths):
            c.width = Cm(w)


def kv_table(doc, rows, widths=(5.2, 0.5, 8.3), size=12):
    t = doc.add_table(rows=len(rows), cols=3)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_borders(t); _widths(t, list(widths))
    for i, (k, v) in enumerate(rows):
        for j, txt in enumerate((k, ":" if k.strip() else "", v)):
            par = t.rows[i].cells[j].paragraphs[0]
            add_runs(par, txt, size=size)
            par.paragraph_format.first_line_indent = Cm(0)
            par.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            par.paragraph_format.space_after = Pt(3)
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return t


# ---------------------------------------------------------------------------
def cover(doc):
    cpar(doc, "LAPORAN AKHIR", 14, True, before=0, after=2)
    cpar(doc, "PENELITIAN TERAPAN PEM AKAMIGAS", 14, True, after=24)
    p = cpar(doc, after=24)
    p.add_run().add_picture(LOGO, width=Cm(4.2))
    cpar(doc, JUDUL.upper(), 14, True, after=36)
    cpar(doc, "Tim Peneliti:", 12, True, after=6)
    for role, nama, nip in TIM:
        cpar(doc, f"{nama}", 12, False, after=0)
        cpar(doc, f"NIP {nip}", 12, False, after=6)
    cpar(doc, f"Nomor SP3: {SP3}", 12, False, before=18, after=48)
    cpar(doc, "POLITEKNIK ENERGI DAN MINERAL AKAMIGAS", 14, True, after=0)
    cpar(doc, "BADAN PENGEMBANGAN SUMBER DAYA MANUSIA ENERGI DAN SUMBER DAYA MINERAL", 12, True, after=0)
    cpar(doc, "KEMENTERIAN ENERGI DAN SUMBER DAYA MINERAL", 12, True, after=0)
    cpar(doc, "CEPU, DESEMBER 2026", 12, True, after=0)


def pengesahan(doc, W):
    W.front_heading("HALAMAN PENGESAHAN")
    cpar(doc, "LAPORAN AKHIR PENELITIAN TERAPAN", 12, True, after=0)
    cpar(doc, "PEM AKAMIGAS TAHUN 2026", 12, True, after=12)
    kv_table(doc, [("Judul Penelitian", JUDUL)], size=11)
    cpar(doc, "Ketua Peneliti", 11, True, align="l", before=6, after=2)
    kv_table(doc, [("a. Nama Lengkap", TIM[0][1]), ("b. NIP/NIDN", f"{TIM[0][2]} / {NIDN_KETUA}"),
                   ("c. Jabatan Fungsional", "Lektor Kepala"), ("d. Nomor HP", "……………………………")], size=11)
    for k, (_, nama, nip) in enumerate(TIM[1:], 1):
        cpar(doc, f"Anggota Peneliti ({k})", 11, True, align="l", before=4, after=2)
        kv_table(doc, [("a. Nama Lengkap", nama), ("b. NIP", nip)], size=11)
    kv_table(doc, [("Nomor SP3", SP3)], size=11)
    cpar(doc, "Cepu, ….. Desember 2026", 11, align="r", before=12, after=6)
    t = doc.add_table(rows=4, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_borders(t); _widths(t, [7.0, 7.0])
    cells = [("Mengetahui,\nKetua UPPM", "Ketua Peneliti,"), ("", ""),
             (f"({TIM[1][1]})", f"({TIM[0][1]})"), (f"NIP {TIM[1][2]}", f"NIP {TIM[0][2]}")]
    for i, (a, b) in enumerate(cells):
        for j, txt in enumerate((a, b)):
            par = t.rows[i].cells[j].paragraphs[0]
            for k, line in enumerate(txt.split("\n")):
                if k:
                    par.add_run().add_break()
                add_runs(par, line, size=11)
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            par.paragraph_format.first_line_indent = Cm(0)
            par.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            if i == 1:
                par.paragraph_format.space_after = Pt(42)
    cpar(doc, "Menyetujui,", 11, before=12, after=0)
    cpar(doc, "Direktur Politeknik Energi dan Mineral Akamigas", 11, after=48)
    cpar(doc, f"({DIREKTUR})", 11, after=0)
    cpar(doc, "NIP ……………………………", 11, after=0)


def abstrak(doc, W, R, lang):
    """Abstrak satu halaman, spasi tunggal. Seluruh angka dibaca dari results/."""
    from docs.lap_text import abstract_text
    title = "ABSTRAK" if lang == "id" else "ABSTRACT"
    W.front_heading(title)
    body, kw = abstract_text(R, lang)
    for k, para in enumerate(body):
        p = doc.add_paragraph()
        add_runs(p, para, italic=(lang == "en"))
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.first_line_indent = Cm(1.25); pf.space_after = Pt(6)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p = doc.add_paragraph()
    add_runs(p, ("**Kata kunci:** " if lang == "id" else "**Keywords:** ") + kw, italic=(lang == "en"))
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    p.paragraph_format.first_line_indent = Cm(0); p.paragraph_format.space_before = Pt(6)
