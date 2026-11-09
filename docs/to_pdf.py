"""Perbarui daftar isi (indexes) lalu ekspor .docx ke PDF via LibreOffice UNO.

Pemakaian: python3 docs/to_pdf.py berkas.docx [berkas2.docx ...]
"""
import os
import subprocess
import sys
import time

import uno
from com.sun.star.beans import PropertyValue


def prop(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v
    return p


def main(files):
    proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore",
                             '--accept=socket,host=localhost,port=2002;urp;'])
    try:
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        for _ in range(60):
            try:
                ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
                break
            except Exception:
                time.sleep(0.5)
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        for f in files:
            url = uno.systemPathToFileUrl(os.path.abspath(f))
            doc = desktop.loadComponentFromURL(url, "_blank", 0, (prop("Hidden", True),))
            idx = doc.getDocumentIndexes()
            for i in range(idx.getCount()):
                idx.getByIndex(i).update()
            doc.refresh()
            out = uno.systemPathToFileUrl(os.path.abspath(os.path.splitext(f)[0] + ".pdf"))
            doc.storeToURL(out, (prop("FilterName", "writer_pdf_Export"),))
            doc.close(True)
            print("pdf:", os.path.splitext(f)[0] + ".pdf")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main(sys.argv[1:])
