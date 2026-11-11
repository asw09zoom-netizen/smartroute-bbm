"""Perangkat python-docx untuk laporan resmi: gaya seragam, bagian bernomor halaman,
daftar isi berbasis field Word, keterangan tabel/gambar, dan persamaan Word (OMML) bernomor."""
from __future__ import annotations

import copy
import os
import re
from typing import List, Optional, Sequence

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"
BODY_PT = 12
TABLE_PT = 10
TEXT_W_CM = 14.0          # A4 21 cm - kiri 4 cm - kanan 3 cm
CAP_TAB = "Keterangan Tabel"
CAP_FIG = "Keterangan Gambar"
CAP_APP = "Judul Lampiran"


# ---------------------------------------------------------------------------
def _rfonts(el, name=FONT):
    rpr = el.get_or_add_rPr() if hasattr(el, "get_or_add_rPr") else el
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]


def new_document() -> Document:
    doc = Document()
    st = doc.styles
    normal = st["Normal"]
    normal.font.name = FONT; normal.font.size = Pt(BODY_PT)
    _rfonts(normal.element)
    pf = normal.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_before = Pt(0); pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.widow_control = True
    # Heading 1: judul bab (tengah, kapital, tebal, 12 pt)
    for name, size, align, before, after in [("Heading 1", BODY_PT, WD_ALIGN_PARAGRAPH.CENTER, 0, 18),
                                             ("Heading 2", BODY_PT, WD_ALIGN_PARAGRAPH.LEFT, 12, 6),
                                             ("Heading 3", BODY_PT, WD_ALIGN_PARAGRAPH.LEFT, 10, 4)]:
        h = st[name]
        h.font.name = FONT; h.font.size = Pt(size); h.font.bold = True; h.font.italic = False
        h.font.color.rgb = RGBColor(0, 0, 0)
        _rfonts(h.element)
        hp = h.paragraph_format
        hp.alignment = align; hp.space_before = Pt(before); hp.space_after = Pt(after)
        hp.keep_with_next = True; hp.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        hp.first_line_indent = Cm(0); hp.left_indent = Cm(0)
        if name == "Heading 1":
            hp.page_break_before = True
    for name in (CAP_TAB, CAP_FIG, CAP_APP):
        s = st.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        s.base_style = normal
        s.font.name = FONT; s.font.size = Pt(BODY_PT)
        _rfonts(s.element)
        sp = s.paragraph_format
        sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sp.line_spacing_rule = WD_LINE_SPACING.SINGLE
        sp.first_line_indent = Cm(0)
        sp.space_before = Pt(6 if name == CAP_TAB else 4)
        sp.space_after = Pt(4 if name == CAP_TAB else 10)
        sp.keep_with_next = name == CAP_TAB
    tc = st.add_style("Isi Tabel", WD_STYLE_TYPE.PARAGRAPH)
    tc.base_style = normal; tc.font.size = Pt(TABLE_PT); tc.font.name = FONT; _rfonts(tc.element)
    tp = tc.paragraph_format
    tp.line_spacing_rule = WD_LINE_SPACING.SINGLE; tp.first_line_indent = Cm(0)
    tp.alignment = WD_ALIGN_PARAGRAPH.LEFT; tp.space_before = Pt(1); tp.space_after = Pt(1)
    for lvl in (1, 2, 3):
        try:
            t = st[f"TOC {lvl}"]
        except KeyError:
            t = st.add_style(f"TOC {lvl}", WD_STYLE_TYPE.PARAGRAPH)
        t.base_style = normal; t.font.name = FONT; t.font.size = Pt(BODY_PT); _rfonts(t.element)
        t.font.bold = lvl == 1
        p = t.paragraph_format
        p.line_spacing_rule = WD_LINE_SPACING.SINGLE; p.space_after = Pt(4); p.first_line_indent = Cm(0)
        p.left_indent = Cm(0.6 * (lvl - 1)); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.tab_stops.add_tab_stop(Cm(TEXT_W_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    try:
        tf = st["table of figures"]
    except KeyError:
        tf = st.add_style("table of figures", WD_STYLE_TYPE.PARAGRAPH)
    tf.base_style = normal; tf.font.name = FONT; tf.font.size = Pt(BODY_PT); _rfonts(tf.element)
    p = tf.paragraph_format
    p.line_spacing_rule = WD_LINE_SPACING.SINGLE; p.space_after = Pt(4); p.first_line_indent = Cm(0)
    p.left_indent = Cm(2.0); p.first_line_indent = Cm(-2.0); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.tab_stops.add_tab_stop(Cm(TEXT_W_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    sec = doc.sections[0]
    sec.page_width = Cm(21.0); sec.page_height = Cm(29.7)
    sec.left_margin = Cm(4.0); sec.right_margin = Cm(3.0); sec.top_margin = Cm(3.0); sec.bottom_margin = Cm(3.0)
    sec.header_distance = Cm(1.25); sec.footer_distance = Cm(1.5)
    return doc


# ---------------------------------------------------------------------------
def add_runs(p, text, size=None, bold=False, italic=False):
    """Markup ringan: **tebal**, _miring_, ^sup^, ~sub~."""
    tokens = re.split(r"(\*\*[^*]+\*\*|(?<![\w/])_[^_]+_(?![\w])|\^[^^]+\^|~[^~]+~)", text)
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
        r.bold = b or None; r.italic = it or None
        if sup: r.font.superscript = True
        if sub: r.font.subscript = True
        if size: r.font.size = Pt(size)
    return p


def _field(p, instr, cached=""):
    r = p.add_run()
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f" {instr} "
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate")
    r._r.append(f1); r._r.append(it); r._r.append(f2)
    r2 = p.add_run(cached)
    r3 = p.add_run()
    f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end")
    r3._r.append(f3)
    return r2


def page_number_footer(section, fmt="decimal", start=1, show=True):
    section.footer.is_linked_to_previous = False
    section.header.is_linked_to_previous = False
    ft = section.footer
    p = ft.paragraphs[0] if ft.paragraphs else ft.add_paragraph()
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    if show:
        _field(p, "PAGE", "1")
    sp = section._sectPr
    pg = sp.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType"); sp.append(pg)
    pg.set(qn("w:fmt"), fmt)
    if start is not None:
        pg.set(qn("w:start"), str(start))


def multi_par_field(doc, anchor_p, instr: str, entries: List[tuple], style_for):
    """Field Word (TOC) yang hasil tersimpannya (cache) berupa beberapa paragraf entri.
    entries: [(teks, halaman, level)] ; style_for(level) -> nama gaya.
    Paragraf disisipkan setelah anchor_p. Mengembalikan paragraf terakhir."""
    body = anchor_p._p
    cur = body
    if not entries:
        entries = [("Perbarui field (F9) untuk menampilkan daftar.", "", 1)]
    paras = []
    for k, (text, page, lvl) in enumerate(entries):
        p = doc.add_paragraph(style=style_for(lvl))
        cur.addnext(p._p); cur = p._p
        if k == 0:
            r = p.add_run()
            for tag, val in (("begin", None),):
                f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), "begin"); r._r.append(f)
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f" {instr} "; r._r.append(it)
            f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), "separate"); r._r.append(f)
        add_runs(p, text)
        p.add_run("\t" + str(page))
        paras.append(p)
    r = paras[-1].add_run()
    f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), "end"); r._r.append(f)
    return paras[-1]


def set_update_fields_on_open(doc):
    settings = doc.settings.element
    u = settings.find(qn("w:updateFields"))
    if u is None:
        u = OxmlElement("w:updateFields"); settings.append(u)
    u.set(qn("w:val"), "true")


# ---------------------------------------------------------------------------
def omml(latex: str):
    """LaTeX -> elemen m:oMath (Word equation)."""
    import latex2mathml.converter
    import mathml2omml
    mml = latex2mathml.converter.convert(latex)
    xml = mathml2omml.convert(mml)
    el = parse_xml(f'<m:oMath {nsdecls("m", "w")}>' + xml[len("<m:oMath>"):] if xml.startswith("<m:oMath>")
                   else f'<w:r {nsdecls("w")}/>')
    # pakai Times New Roman / Cambria Math bawaan Word
    return el


def _shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def _borders(tbl, outer=8, inner=4):
    tblPr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement(f"w:{e}")
        x.set(qn("w:val"), "single"); x.set(qn("w:sz"), str(outer if e in ("top", "bottom") else inner))
        x.set(qn("w:space"), "0"); x.set(qn("w:color"), "000000")
        b.append(x)
    tblPr.append(b)


def _fixed_layout(tbl, widths_cm):
    tblPr = tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    tw = tblPr.find(qn("w:tblW"))
    if tw is None:
        tw = OxmlElement("w:tblW"); tblPr.append(tw)
    tw.set(qn("w:type"), "dxa"); tw.set(qn("w:w"), str(int(sum(widths_cm) * 567)))
    grid = tbl.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths_cm):
        gc.set(qn("w:w"), str(int(w * 567)))
    mar = OxmlElement("w:tblCellMar")
    for side in ("left", "right"):
        m = OxmlElement(f"w:{side}"); m.set(qn("w:w"), "70"); m.set(qn("w:type"), "dxa"); mar.append(m)
    tblPr.append(mar)


def _repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)


def _cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    c = OxmlElement("w:cantSplit"); c.set(qn("w:val"), "true"); trPr.append(c)


class Writer:
    """Menulis isi laporan secara berurutan di akhir dokumen."""

    def __init__(self, doc):
        self.doc = doc
        self.chapter = 0
        self.h2 = self.h3 = 0
        self.tab = self.fig = 0
        self.eq = 0
        self.tables: List[str] = []
        self.figures: List[str] = []
        self.headings: List[tuple] = []

    # -- teks ---------------------------------------------------------------
    def p(self, text, indent=True, align="j", keep_next=False, size=None, space_after=0):
        p = self.doc.add_paragraph()
        add_runs(p, text, size=size)
        pf = p.paragraph_format
        pf.first_line_indent = Cm(1.25) if indent else Cm(0)
        pf.alignment = {"j": WD_ALIGN_PARAGRAPH.JUSTIFY, "c": WD_ALIGN_PARAGRAPH.CENTER,
                        "l": WD_ALIGN_PARAGRAPH.LEFT, "r": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        pf.keep_with_next = keep_next or None
        if space_after:
            pf.space_after = Pt(space_after)
        return p

    def bullets(self, items, numbered=False, letters=False, left=False):
        for k, it in enumerate(items, 1):
            mark = (f"{chr(96 + k)}." if letters else f"{k}.") if (numbered or letters) else "•"
            p = self.doc.add_paragraph()
            add_runs(p, f"{mark}\t{it}")
            pf = p.paragraph_format
            pf.left_indent = Cm(0.75); pf.first_line_indent = Cm(-0.75)
            pf.tab_stops.add_tab_stop(Cm(0.75))
            if left:
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                pf.alignment = WD_ALIGN_PARAGRAPH.LEFT

    def chapter_title(self, num_label, title):
        """BAB n. JUDUL (Heading 1)."""
        self.chapter += 1 if num_label else 0
        self.h2 = self.h3 = 0
        self.tab = self.fig = 0
        txt = f"{num_label}. {title}".strip(". ") if num_label else title
        h = self.doc.add_paragraph(txt, style="Heading 1")
        self.headings.append((txt, 1))
        return h

    def front_title(self, title, toc=True):
        h = self.doc.add_paragraph(title, style="Heading 1")
        if not toc:
            # tetap Heading 1 agar format sama, tetapi keluarkan dari daftar isi lewat outline level body
            pPr = h._p.get_or_add_pPr()
            ol = OxmlElement("w:outlineLvl"); ol.set(qn("w:val"), "9"); pPr.append(ol)
        else:
            self.headings.append((title, 1))
        return h

    def h(self, title):
        self.h2 += 1; self.h3 = 0
        txt = f"{self.chapter}.{self.h2} {title}"
        self.doc.add_paragraph(txt, style="Heading 2")
        self.headings.append((txt, 2))

    def hh(self, title):
        self.h3 += 1
        txt = f"{self.chapter}.{self.h2}.{self.h3} {title}"
        self.doc.add_paragraph(txt, style="Heading 3")
        self.headings.append((txt, 3))

    # -- persamaan -----------------------------------------------------------
    def eqn(self, latex, label=None):
        self.eq += 1
        p = self.doc.add_paragraph()
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0); pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.space_before = Pt(3); pf.space_after = Pt(3)
        pf.tab_stops.add_tab_stop(Cm(TEXT_W_CM / 2), WD_TAB_ALIGNMENT.CENTER)
        pf.tab_stops.add_tab_stop(Cm(TEXT_W_CM), WD_TAB_ALIGNMENT.RIGHT)
        p.add_run("\t")
        p._p.append(omml(latex))
        p.add_run(f"\t({self.eq})")
        return self.eq

    # -- tabel & gambar -----------------------------------------------------
    def table(self, header, rows, caption, widths, align=None, note=None, font=TABLE_PT, bold_last=False):
        assert abs(sum(widths) - min(sum(widths), TEXT_W_CM)) < 1e-6, f"tabel terlalu lebar: {sum(widths)} cm"
        self.tab += 1
        cap = f"Tabel {self.chapter}.{self.tab} {caption}"
        cp = self.doc.add_paragraph(style=CAP_TAB)
        add_runs(cp, f"**Tabel {self.chapter}.{self.tab}** {caption}")
        self.tables.append(cap)
        t = self.doc.add_table(rows=1 + len(rows), cols=len(header))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        _borders(t._tbl)
        _fixed_layout(t._tbl, widths)
        align = align or (["l"] + ["c"] * (len(header) - 1))
        AL = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER, "r": WD_ALIGN_PARAGRAPH.RIGHT,
              "j": WD_ALIGN_PARAGRAPH.LEFT}
        for i, row in enumerate([header] + [list(r) for r in rows]):
            tr = t.rows[i]
            _cant_split(tr)
            if i == 0:
                _repeat_header(tr)
            for j, v in enumerate(row):
                cell = tr.cells[j]
                cell.width = Cm(widths[j])
                par = cell.paragraphs[0]
                par.style = self.doc.styles["Isi Tabel"]
                add_runs(par, str(v), size=font, bold=(i == 0) or (bold_last and i == len(rows)))
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else AL[align[j]]
                if i == 0:
                    _shade(cell, "D9D9D9")
        # baris kecuali terakhir ikut tabel; catatan setelah tabel
        if note:
            n = self.doc.add_paragraph()
            add_runs(n, note, size=TABLE_PT, italic=False)
            n.paragraph_format.first_line_indent = Cm(0)
            n.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            n.paragraph_format.space_before = Pt(2); n.paragraph_format.space_after = Pt(10)
            n.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        else:
            sp = self.doc.add_paragraph()
            sp.paragraph_format.space_after = Pt(4)
            sp.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            for r in sp.runs:
                pass
            sp.paragraph_format.first_line_indent = Cm(0)
        return t

    def figure(self, path, caption, width_cm=TEXT_W_CM, source=None):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        width_cm = min(width_cm, TEXT_W_CM)
        self.fig += 1
        p = self.doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        p.paragraph_format.space_before = Pt(6)
        from PIL import Image
        w, h = Image.open(path).size
        hcm = width_cm * h / w
        if hcm > 19.0:  # batasi tinggi agar gambar + keterangan muat satu halaman
            width_cm = width_cm * 19.0 / hcm
        p.add_run().add_picture(path, width=Cm(width_cm))
        cap = f"Gambar {self.chapter}.{self.fig} {caption}"
        cp = self.doc.add_paragraph(style=CAP_FIG)
        add_runs(cp, f"**Gambar {self.chapter}.{self.fig}** {caption}" + (f" ({source})" if source else ""))
        self.figures.append(cap)
        return self.fig

    def page_break(self):
        p = self.doc.add_paragraph()
        p.add_run().add_break(WD_BREAK.PAGE)
        return p

    def new_section(self, fmt="decimal", start=1, show=True):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        page_number_footer(sec, fmt, start, show)
        return sec


# ---------------------------------------------------------------------------
# Daftar isi/tabel/gambar yang tahan locale Word (pemisah daftar "," vs ";")
def _fld_run(kind=None, instr=None, text=None):
    r = OxmlElement("w:r")
    if kind:
        f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), kind); r.append(f)
    if instr is not None:
        it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f" {instr} "; r.append(it)
    if text is not None:
        t = OxmlElement("w:t"); t.set(qn("xml:space"), "preserve"); t.text = text; r.append(t)
    return r


def plain(text):
    """Buang markup ringan add_runs."""
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    t = re.sub(r"(?<![\w/])_([^_]+)_(?![\w])", r"\1", t)
    t = re.sub(r"\^([^^]+)\^", r"\1", t)
    return re.sub(r"~([^~]+)~", r"\1", t)


def add_bookmark(p, name, bid):
    s = OxmlElement("w:bookmarkStart"); s.set(qn("w:id"), str(bid)); s.set(qn("w:name"), name)
    e = OxmlElement("w:bookmarkEnd"); e.set(qn("w:id"), str(bid))
    pPr = p._p.find(qn("w:pPr"))
    if pPr is not None:
        pPr.addnext(s)
    else:
        p._p.insert(0, s)
    p._p.append(e)


def add_tc(p, text, ident):
    """Field TC tersembunyi: { TC "teks" \\f X \\l 1 } untuk TOC \\f X."""
    txt = plain(text).replace('"', "”")
    p._p.append(_fld_run("begin"))
    p._p.append(_fld_run(instr=f'TC "{txt}" \\f {ident} \\l 1'))
    p._p.append(_fld_run("end"))


def toc_field(doc, anchor_p, instr, entries, style_for):
    """Field TOC dengan hasil tersimpan seperti buatan Word: tiap entri = hyperlink ke bookmark
    + PAGEREF. entries: [(teks, halaman, level, bookmark)]."""
    cur = anchor_p._p
    paras = []
    for k, (text, page, lvl, bm) in enumerate(entries):
        p = doc.add_paragraph(style=style_for(lvl))
        cur.addnext(p._p); cur = p._p
        if k == 0:
            for el in (_fld_run("begin"), _fld_run(instr=instr), _fld_run("separate")):
                p._p.append(el)
        hl = OxmlElement("w:hyperlink"); hl.set(qn("w:anchor"), bm); hl.set(qn("w:history"), "1")
        tmp = doc.add_paragraph(); add_runs(tmp, text)
        for r in list(tmp._p.findall(qn("w:r"))):
            hl.append(r)
        tmp._p.getparent().remove(tmp._p)
        tab = OxmlElement("w:r"); tab.append(OxmlElement("w:tab")); hl.append(tab)
        for el in (_fld_run("begin"), _fld_run(instr=f"PAGEREF {bm} \\h"), _fld_run("separate"),
                   _fld_run(text=str(page)), _fld_run("end")):
            hl.append(el)
        p._p.append(hl)
        paras.append(p)
    paras[-1]._p.append(_fld_run("end"))
    return paras[-1]
