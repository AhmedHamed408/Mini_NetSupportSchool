from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter


def print_html_report(parent, title: str, html_body: str) -> None:
    printer = QPrinter(QPrinter.HighResolution)
    dialog = QPrintDialog(printer, parent)
    if dialog.exec_():
        doc = QTextDocument()
        doc.setHtml(f"<h2>{title}</h2>{html_body}")
        doc.print_(printer)
