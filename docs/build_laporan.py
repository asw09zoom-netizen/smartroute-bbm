"""Membangun Laporan Akhir SMARTROUTE-BBM (.docx) dengan format laporan resmi.

* A4, margin kiri 4 cm, atas/kanan/bawah 3 cm; Times New Roman 12 pt, spasi 1,5; tabel 10 pt.
* Halaman depan bernomor romawi, isi bernomor arab mulai BAB 1.
* Daftar isi, tabel, gambar, dan lampiran berupa field Word. Nomor halaman awal (cache) diisi dari
  hasil paginasi LibreOffice; Word memperbarui field saat dokumen dibuka.
* Semua angka hasil dibaca dari results/; tidak ada angka hasil yang ditulis tangan.

Jalankan:  python -m docs.build_laporan
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from docx.enum.style import WD_STYLE_TYPE  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER  # noqa: E402
from docx.shared import Cm, Pt  # noqa: E402

from docs import docx_kit as K  # noqa: E402
from docs.lap_bab4 import bab4, bab5, lampiran  # noqa: E402
from docs.lap_common import OUT, load_results  # noqa: E402
from docs.lap_front import abstrak, cover, pengesahan  # noqa: E402
from docs.lap_text import bab1, bab2, bab3  # noqa: E402
from docs.refs import REFS, Citer  # noqa: E402

FNAME = "Laporan_Akhir_SMARTROUTE-BBM_2026.docx"
LIST_STYLE = "TOC 4"


def keep_together(t, max_rows=22):
    """Tabel pendek tidak terpotong halaman: semua baris kecuali terakhir 'keep with next'."""
    if len(t.rows) > max_rows:
        return
    for row in t.rows[:-1]:
        for c in row.cells:
            for par in c.paragraphs:
                par.paragraph_format.keep_with_next = True


class LapWriter(K.Writer):
    def __init__(self, doc):
        super().__init__(doc)
        self.appendices = []

    def bab(self, n, title):
        self.chapter = n
        self.h2 = self.h3 = 0
        self.tab = self.fig = 0
        txt = f"BAB {n} {title}"
        self.doc.add_paragraph(txt, style="Heading 1")
        self.headings.append((txt, 1))

    def h(self, title):
        self.h2 += 1; self.h3 = 0
        txt = f"{self.chapter}.{self.h2} {title}"
        K.add_runs(self.doc.add_paragraph(style="Heading 2"), txt)
        self.headings.append((txt, 2))

    def hh(self, title):
        self.h3 += 1
        txt = f"{self.chapter}.{self.h2}.{self.h3} {title}"
        K.add_runs(self.doc.add_paragraph(style="Heading 3"), txt)
        self.headings.append((txt, 3))

    def front_heading(self, title):
        self.doc.add_paragraph(title, style="Heading 1")
        self.headings.append((title, 1))

    def plain_heading(self, title):
        """Judul halaman depan yang tidak masuk daftar isi."""
        return self.doc.add_paragraph(title, style="Judul Depan")

    def appendix(self, title):
        p = self.doc.add_paragraph(style=K.CAP_APP)
        K.add_runs(p, title)
        self.appendices.append(title)

    def table(self, header, rows, caption, widths, align=None, note=None, font=K.TABLE_PT, bold_last=False):
        if caption is None:  # tabel lampiran tanpa nomor
            n0 = self.tab
            t = super().table(header, rows, "_", widths, align, note, font, bold_last)
            keep_together(t)
            cap_p = t._tbl.getprevious()
            cap_p.getparent().remove(cap_p)
            self.tables.pop(); self.tab = n0
            return t
        t = super().table(header, rows, caption, widths, align, note, font, bold_last)
        keep_together(t)
        return t

    def p(self, text, indent=True, align="j", keep_next=False, size=None, space_after=0):
        return super().p(text, indent, align, keep_next, size, space_after)


def styles(doc):
    st = doc.styles
    from docx.oxml.ns import qn
    rpr = st.element.find(qn("w:docDefaults")).find(qn("w:rPrDefault")).find(qn("w:rPr"))
    K._rfonts(rpr)
    for s0 in st:
        if s0.type == WD_STYLE_TYPE.PARAGRAPH and s0.element.find(qn("w:rPr")) is not None:
            rf = s0.element.find(qn("w:rPr")).find(qn("w:rFonts"))
            if rf is not None:
                K._rfonts(s0.element.find(qn("w:rPr")))
    s = st.add_style("Judul Depan", WD_STYLE_TYPE.PARAGRAPH)
    s.base_style = st["Normal"]; s.font.bold = True; s.font.size = Pt(12)
    pf = s.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER; pf.first_line_indent = Cm(0); pf.space_after = Pt(18)
    pf.page_break_before = True; pf.keep_with_next = True
    # gaya entri daftar tabel/gambar/lampiran
    try:
        t4 = st[LIST_STYLE]
    except KeyError:
        t4 = st.add_style(LIST_STYLE, WD_STYLE_TYPE.PARAGRAPH)
    t4.base_style = st["Normal"]; t4.font.name = K.FONT; t4.font.size = Pt(12); t4.font.bold = False
    K._rfonts(t4.element)
    p = t4.paragraph_format
    p.line_spacing_rule = WD_LINE_SPACING.SINGLE; p.space_after = Pt(6); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.left_indent = Cm(2.2); p.first_line_indent = Cm(-2.2); p.right_indent = Cm(0.8)
    p.tab_stops.add_tab_stop(Cm(K.TEXT_W_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    for lvl in (1, 2, 3):
        st[f"TOC {lvl}"].paragraph_format.right_indent = Cm(0.8)
        st[f"TOC {lvl}"].paragraph_format.space_after = Pt(6 if lvl == 1 else 3)
    la = st[K.CAP_APP]
    la.font.bold = True
    la.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    la.paragraph_format.space_before = Pt(12); la.paragraph_format.space_after = Pt(6)
    la.paragraph_format.keep_with_next = True


# ---------------------------------------------------------------------------
def build(pages=None):
    """pages: dict teks-entri -> label halaman (dari paginasi). None = penanda sementara."""
    R = load_results()
    doc = K.new_document()
    styles(doc)
    W = LapWriter(doc)
    cite = Citer()
    # --- sampul (tanpa nomor halaman)
    cover(doc)
    K.page_number_footer(doc.sections[0], "decimal", None, show=False)
    # --- halaman depan (romawi, mulai ii)
    W.new_section("lowerRoman", 2, True)
    pengesahan(doc, W)
    abstrak(doc, W, R, "id")
    abstrak(doc, W, R, "en")
    W.plain_heading("DAFTAR ISI")
    a_toc = doc.add_paragraph()
    W.front_heading("DAFTAR TABEL"); a_tab = doc.add_paragraph()
    W.front_heading("DAFTAR GAMBAR"); a_fig = doc.add_paragraph()
    W.front_heading("DAFTAR LAMPIRAN"); a_app = doc.add_paragraph()
    # --- isi (arab, mulai 1)
    W.new_section("decimal", 1, True)
    bab1(W, cite, R)
    bab2(W, cite, R)
    bab3(W, cite, R)
    bab4(W, cite, R)
    bab5(W, cite, R)
    W.front_heading("DAFTAR PUSTAKA")
    for ref in cite.bibliography():
        p = doc.add_paragraph()
        ref = re.sub(r'"([^"]*)"', "“\\1”", ref.replace(" [VERIFY]", ""))
        K.add_runs(p, ref)
        pf = p.paragraph_format
        pf.left_indent = Cm(1.0); pf.first_line_indent = Cm(-1.0); pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE; pf.space_after = Pt(6)
    W.front_heading("LAMPIRAN")
    lampiran(W, R)
    # --- daftar (field Word)
    pg = (lambda t: pages.get(t, "")) if pages else (lambda t: "00")
    # bookmark pada judul dan keterangan (urutan dokumen), TC untuk daftar tabel/gambar/lampiran
    hs = {"Heading 1": 1, "Heading 2": 2, "Heading 3": 3}
    groups = {"H": [], K.CAP_TAB: [], K.CAP_FIG: [], K.CAP_APP: []}
    for par in doc.paragraphs:
        sn = par.style.name
        if sn in hs:
            groups["H"].append(par)
        elif sn in groups:
            groups[sn].append(par)
    lists = {"H": W.headings, K.CAP_TAB: W.tables, K.CAP_FIG: W.figures, K.CAP_APP: W.appendices}
    bms, bid = {}, 100
    for key, pars in groups.items():
        items = lists[key]
        assert len(pars) == len(items), (key, len(pars), len(items))
        for par, it in zip(pars, items):
            text = it[0] if isinstance(it, tuple) else it
            bid += 1
            name = f"_Toc{bid:08d}"
            K.add_bookmark(par, name, bid)
            if key != "H":
                K.add_tc(par, text, {K.CAP_TAB: "T", K.CAP_FIG: "G", K.CAP_APP: "L"}[key])
            bms.setdefault(key, []).append((text, name))
    toc_entries = [(t, pg(t), lvl, bm) for (t, lvl), (_, bm) in zip(W.headings, bms["H"])]
    K.toc_field(doc, a_toc, 'TOC \\o "1-3" \\h \\z \\u', toc_entries, lambda l: f"TOC {l}")
    for a, key, ident in ((a_tab, K.CAP_TAB, "T"), (a_fig, K.CAP_FIG, "G"), (a_app, K.CAP_APP, "L")):
        K.toc_field(doc, a, f"TOC \\h \\z \\f {ident}", [(t, pg(t), 4, bm) for t, bm in bms[key]],
                    lambda l: LIST_STYLE)
    for a in (a_toc, a_tab, a_fig, a_app):
        a._p.getparent().remove(a._p)
    # sengaja TIDAK memaksa pembaruan field saat dibuka: nomor halaman tersimpan sudah hasil paginasi
    unused = [k for k in REFS if k not in cite.order]
    return doc, W, cite, unused


# ---------------------------------------------------------------------------
def to_pdf(docx_path, outdir):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", outdir, docx_path],
                   check=True, capture_output=True, timeout=600)
    return os.path.join(outdir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")


def pdf_pages(pdf):
    txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    return txt.split("\f")


def _norm(s):
    s = s.replace("~", "").replace("^", "").replace("**", "").replace("_", "")
    return re.sub(r"\s+", " ", s).strip()


def _roman(n):
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s; n -= v
    return out


def paginate(W, pages_txt):
    """Cari halaman fisik setiap judul/keterangan (urut dokumen) lalu ubah ke label halaman."""
    norm_pages = [[_norm(l) for l in pg.splitlines() if l.strip()] for pg in pages_txt]
    # halaman awal isi: halaman pertama yang baris teratasnya 'BAB 1 ...'
    def first_line_is(i, t):
        return norm_pages[i] and norm_pages[i][0].startswith(t[:40])
    body0 = next(i for i in range(len(norm_pages)) if first_line_is(i, "BAB 1 PENDAHULUAN"))
    label = lambda i: _roman(i + 1) if i < body0 else str(i - body0 + 1)  # noqa: E731
    found, misses = {}, []
    # judul bab/halaman depan: halaman yang baris pertamanya judul tsb
    items = [(t, "h") for t, _ in W.headings] + [(t, "c") for t in W.tables + W.figures] + [(t, "a") for t in W.appendices]
    # urutkan sesuai urutan dokumen: pakai pencarian bertahap
    start_by_chapter = {}
    for t, lvl in W.headings:
        if lvl == 1:
            idx = next((i for i in range(len(norm_pages)) if first_line_is(i, _norm(t))), None)
            if idx is None:
                misses.append(t); continue
            found[t] = idx
    chap_pages = sorted(found.values())
    for t, kind in items:
        if t in found:
            continue
        key = _norm(t)[:45]
        # mulai dari halaman awal isi (setelah daftar-daftar)
        lo = body0
        m = re.match(r"(?:Tabel|Gambar) (\d+)\.", t) or re.match(r"(\d+)\.", t)
        if m:
            bab = f"BAB {m.group(1)} "
            bp = [found[x] for x in found if x.startswith(bab)]
            lo = bp[0] if bp else body0
        if t.startswith("Lampiran"):
            lo = found.get("LAMPIRAN", body0)
        idx = next((i for i in range(lo, len(norm_pages)) if any(l.startswith(key) for l in norm_pages[i])), None)
        if idx is None:
            misses.append(t); continue
        found[t] = idx
    return {t: label(i) for t, i in found.items()}, misses, body0, len(norm_pages)


def main():
    tmp = tempfile.mkdtemp()
    doc, W, cite, unused = build(None)
    p1 = os.path.join(tmp, FNAME); doc.save(p1)
    pages, misses, body0, n = paginate(W, pdf_pages(to_pdf(p1, tmp)))
    print("pass1: halaman", n, "isi mulai fisik", body0 + 1, "tak ditemukan:", misses)
    for it in range(3):
        doc, W, cite, unused = build(pages)
        p2 = os.path.join(tmp, FNAME); doc.save(p2)
        pdf = to_pdf(p2, tmp)
        pages2, misses, body0, n = paginate(W, pdf_pages(pdf))
        diff = {k: (pages[k], v) for k, v in pages2.items() if pages.get(k) != v}
        print(f"pass{it + 2}: halaman {n}, beda {len(diff)}, tak ditemukan {misses}")
        pages = pages2
        if not diff:
            break
    doc, W, cite, unused = build(pages)
    out = os.path.join(OUT, FNAME)
    doc.save(out)
    shutil.copy(pdf, os.path.join(tmp, "final_check.pdf"))
    print("saved", out, "| referensi dipakai:", len(cite.order), "| tidak dipakai:", unused)
    print("pdf cek:", os.path.join(tmp, "final_check.pdf"))
    return out


if __name__ == "__main__":
    main()
