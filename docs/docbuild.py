"""Helper kecil python-docx untuk menyisipkan blok konten ke dokumen/template."""
from __future__ import annotations

import copy
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph
from docx.table import Table

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class Cursor:
    """Menyisipkan blok secara berurutan setelah elemen anchor."""

    def __init__(self, doc: Document, anchor_el, numbering=True):
        self.doc = doc
        self.el = anchor_el
        self.fig_no = 0
        self.tab_no = 0
        self.eq_no = 0
        self.numbering = numbering
        self.fig_prefix = ""
        self.figures = []
        self.tables = []

    # -- dasar ---------------------------------------------------------------
    def _add_el(self, el):
        self.el.addnext(el)
        self.el = el
        return el

    def para(self, text="", style="Normal", align=None, bold=False, italic=False, size=None,
             indent_first=None, space_after=None, keep_next=False):
        p = self.doc.add_paragraph(style=style)  # dibuat di akhir lalu dipindah
        self._add_el(p._p)
        if text:
            self._runs(p, text, bold=bold, italic=italic, size=size)
        if align == "j":
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif align == "c":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "r":
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if indent_first is not None:
            p.paragraph_format.first_line_indent = Cm(indent_first)
        if space_after is not None:
            p.paragraph_format.space_after = Pt(space_after)
        if keep_next:
            p.paragraph_format.keep_with_next = True
        return p

    @staticmethod
    def _runs(p, text, bold=False, italic=False, size=None):
        """Mendukung markup ringan: **tebal**, _miring_ (diapit garis bawah tunggal), ^sup^, ~sub~."""
        import re
        tokens = re.split(r"(\*\*[^*]+\*\*|(?<![\w])_[^_]+_(?![\w])|\^[^^]+\^|~[^~]+~)", text)
        for tok in tokens:
            if not tok:
                continue
            b, it, sup, sub = bold, italic, False, False
            if tok.startswith("**") and tok.endswith("**"):
                tok, b = tok[2:-2], True
            elif tok.startswith("_") and tok.endswith("_") and len(tok) > 2:
                tok, it = tok[1:-1], True
            elif tok.startswith("^") and tok.endswith("^"):
                tok, sup = tok[1:-1], True
            elif tok.startswith("~") and tok.endswith("~") and len(tok) > 2:
                tok, sub = tok[1:-1], True
            r = p.add_run(tok)
            r.bold = b or None
            r.italic = it or None
            if sup:
                r.font.superscript = True
            if sub:
                r.font.subscript = True
            if size:
                r.font.size = Pt(size)

    def p(self, text, **kw):
        kw.setdefault("align", "j")
        kw.setdefault("indent_first", 1.0)
        return self.para(text, **kw)

    h2_prefix = ""
    h2_count = 0

    def h(self, text, style="Heading 2"):
        if style == "Heading 2" and self.h2_prefix:
            self.h2_count += 1
            text = f"{self.h2_prefix}{self.h2_count} {text}"
        return self.para(text, style=style, keep_next=True)

    def sub(self, text):
        return self.para(text, bold=True, keep_next=True, space_after=3)

    def bullets(self, items, numbered=False, align="j"):
        for k, it in enumerate(items, 1):
            mark = f"{k}." if numbered else "•"
            p = self.para(f"{mark}\t{it}", align=align)
            p.paragraph_format.left_indent = Cm(1.0)
            p.paragraph_format.first_line_indent = Cm(-0.6)
            p.paragraph_format.space_after = Pt(2)

    def eq(self, text):
        self.eq_no += 1
        p = self.para("", align=None)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(7.8), alignment=1)  # center
        p.paragraph_format.tab_stops.add_tab_stop(Cm(15.5), alignment=2)  # right
        self._runs(p, "\t" + text + f"\t({self.eq_no})", italic=False)
        return self.eq_no

    def page_break(self):
        p = self.para("")
        p.add_run().add_break(WD_BREAK.PAGE)

    def caption(self, text):
        p = self.para(text, align="c", size=10)
        p.paragraph_format.space_after = Pt(8)
        return p

    def figure(self, path, caption, width_cm=15.0, label="Gambar"):
        if not os.path.exists(path):
            self.para(f"[{label} tidak tersedia: {os.path.basename(path)}]", italic=True, align="c")
            return None
        self.fig_no += 1
        p = self.para("", align="c", keep_next=True)
        p.add_run().add_picture(path, width=Cm(width_cm))
        cap = f"{label} {self.fig_prefix}{self.fig_no}. {caption}"
        self.caption(cap)
        self.figures.append(cap)
        return self.fig_no

    def table(self, header, rows, caption=None, widths=None, label="Tabel", size=9, note=None):
        if caption:
            self.tab_no += 1
            cap = f"{label} {self.fig_prefix}{self.tab_no}. {caption}"
            c = self.caption(cap)
            c.paragraph_format.keep_with_next = True
            c.paragraph_format.space_after = Pt(2)
            self.tables.append(cap)
        t = self.doc.add_table(rows=1 + len(rows), cols=len(header))
        try:
            t.style = self.doc.styles["Table Grid"]
        except KeyError:
            _grid(t)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, hd in enumerate(header):
            cell = t.rows[0].cells[j]
            cell.text = ""
            self._runs(cell.paragraphs[0], str(hd), bold=True, size=size)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            _shade(cell, "D9E2F3")
        for i, r in enumerate(rows, 1):
            for j, v in enumerate(r):
                cell = t.rows[i].cells[j]
                cell.text = ""
                self._runs(cell.paragraphs[0], str(v), size=size)
                if j > 0:
                    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for row in t.rows:
            for cell in row.cells:
                for pp in cell.paragraphs:
                    pp.paragraph_format.space_after = Pt(0)
                    pp.paragraph_format.first_line_indent = None
        if widths:
            for row in t.rows:
                for j, wd in enumerate(widths):
                    row.cells[j].width = Cm(wd)
        self._add_el(t._tbl)
        if note:
            n = self.para(note, size=8, italic=True)
            n.paragraph_format.space_after = Pt(8)
        else:
            sp = self.para("")
            sp.paragraph_format.space_after = Pt(4)
        return t


def _grid(t):
    tbl = t._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{e}")
        b.set(qn("w:val"), "single"); b.set(qn("w:sz"), "4"); b.set(qn("w:space"), "0"); b.set(qn("w:color"), "000000")
        borders.append(b)
    tblPr.append(borders)


def _shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def remove_el(el):
    el.getparent().remove(el)


def add_toc(paragraph, levels="1-2"):
    """Sisipkan field TOC (diperbarui saat dokumen dibuka/di-update di Word)."""
    run = paragraph.add_run()
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f'TOC \\o "{levels}" \\h \\z \\u'
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "Klik kanan > Update Field untuk memperbarui daftar isi."
    f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end")
    run._r.append(f1); run._r.append(it); run._r.append(f2); run._r.append(t); run._r.append(f3)


def set_update_fields_on_open(doc):
    settings = doc.settings.element
    u = OxmlElement("w:updateFields"); u.set(qn("w:val"), "true")
    settings.append(u)
