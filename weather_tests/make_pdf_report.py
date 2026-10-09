import os
import re
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#1F4E78")
LIGHT = colors.HexColor("#EAF1F8")
GREY = colors.HexColor("#999999")
GREEN = "#2E7D32"
RED = "#C62828"
AMBER = "#EF6C00"
SEVERITY_COLORS = {"Critical": "#C0392B", "Major": "#E67E22", "Minor": "#B7950B"}

DEFECTS = {
    12: ("D1", "In the 7-day cards, Min shows the higher temperature and Max the lower one", "Data accuracy", "Major"),
    16: ("D2", "After an error, a valid search never shows weather again until the page is reloaded", "Functional", "Major"),
    20: ("D3", "Pressing Enter in the search box does not start a search", "UI / usability", "Minor"),
    21: ("D4", "A city with no state is shown with the word 'undefined' in its name", "Data display", "Minor"),
    23: ("D5", "The name from 'Use my current location' ends with ', ,'", "Data display", "Minor"),
    24: ("D6", "When location permission is denied the button stays on 'Searching..' and the search button stays hidden", "Error handling", "Major"),
    25: ("D7", "No error is shown to the user when the forecast service fails", "Error handling", "Major"),
    27: ("D8", "An API key is written in source.js and visible to every visitor", "Security", "Critical"),
    28: ("D9", "Search, previous and next buttons have no accessible name", "Accessibility", "Minor"),
    10: ("D10", "Previous and Next buttons never look disabled", "UI / usability", "Minor"),
}

CHARTERS = [
    ("E1", "Search with unusual inputs", "Very long names, accents, & and # characters, upper and lower case, repeated and quick searches"),
    ("E2", "Forecast screens", "Compare values with another weather site, switch parameters quickly, search another city with the 7-day view open"),
    ("E3", "Location and permissions", "Allow, block and allow again; desktop without GPS; offline mode"),
    ("E4", "Screen sizes and browsers", "320, 375, 768 and 1366 px, zoom 150 percent, Edge and Brave"),
    ("E5", "Failure situations", "Network off after load, slow connection, blocked services"),
]

OBSERVATIONS = [
    ("The '24-Hour Forecast' always starts at 00:00 of today instead of the current hour", "Functional", "Minor"),
    ("Heading says 'Relative humidity' while the button says 'Relative Humidity'", "UI / usability", "Minor"),
    ("Dates in the 7-day view appear as 2026-10-08 while the page design uses 27/08/2025", "UI / usability", "Minor"),
    ("The city name is put in the request URL without encoding, so names with & or # may be cut short", "Functional", "Minor"),
    ("Hourly button handlers are added again after every search", "Code quality", "Minor"),
    ("'country' is used without being declared and 'findHistoryElem' is called but never defined", "Code quality", "Minor"),
    ("The HTML has a head element inside body and a meta http-equiv tag with no content", "Code quality", "Minor"),
    ("About 14 Google font families are loaded, which slows the first page load", "Performance", "Minor"),
]

SESSION_NOTES = []

styles = getSampleStyleSheet()
body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5, leading=13, spaceAfter=4)
cell = ParagraphStyle("Cell", parent=body, fontSize=8.5, leading=11, spaceAfter=0)
cell_bold = ParagraphStyle("CellBold", parent=cell, fontName="Helvetica-Bold")
cell_head = ParagraphStyle("CellHead", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=22, textColor=NAVY, spaceAfter=2)
sub_style = ParagraphStyle("Sub", parent=body, fontSize=10.5, textColor=colors.HexColor("#555555"), alignment=1, spaceAfter=10)
h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, textColor=NAVY, spaceBefore=12, spaceAfter=6, keepWithNext=1)
h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, textColor=NAVY, spaceBefore=8, spaceAfter=4, keepWithNext=1)


def esc(text):
    return escape(str(text))


def p(text, style=cell):
    return Paragraph(text, style)


def make_table(header, rows, widths, repeat=True):
    data = [[p(esc(h), cell_head) for h in header]] + rows
    table = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if repeat else 0)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, GREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def parse_name(name):
    match = re.match(r"test_tc(\d+)([a-z]?)_(.*?)(?:\[(.*)\])?$", name)
    if not match:
        return 0, name, name
    number = int(match.group(1))
    text = match.group(3).replace("_", " ").strip()
    text = text[:1].upper() + text[1:]
    param = match.group(4)
    if param:
        param = param.replace("\\xb0", "\u00b0")
    label = f"TC{number:02d}{match.group(2)}"
    return number, label, text + (f" [{param}]" if param else "")


def status_text(outcome):
    label, color = {"passed": ("PASS", GREEN), "failed": ("FAIL", RED), "skipped": ("SKIP", AMBER)}[outcome]
    return f'<font color="{color}"><b>{label}</b></font>'


def severity_text(severity):
    return f'<font color="{SEVERITY_COLORS.get(severity, "#000000")}"><b>{esc(severity)}</b></font>'


def summary_bar(passed, failed, skipped):
    total = max(passed + failed + skipped, 1)
    width, height = 170 * mm, 7 * mm
    drawing = Drawing(width, height)
    x = 0
    for count, color in ((passed, GREEN), (failed, RED), (skipped, AMBER)):
        w = width * count / total
        if w:
            drawing.add(Rect(x, 0, w, height, fillColor=colors.HexColor(color), strokeColor=None))
            x += w
    return drawing


def screenshot(path, max_w=150 * mm, max_h=85 * mm):
    if not path or not os.path.exists(path):
        return None
    try:
        from io import BytesIO
        from PIL import Image as PILImage
        img = PILImage.open(path).convert("RGB")
        img.thumbnail((1100, 1100))
        buffer = BytesIO()
        img.save(buffer, "JPEG", quality=80)
        buffer.seek(0)
        source, (w, h) = buffer, img.size
    except Exception:
        source, (w, h) = path, ImageReader(path).getSize()
    scale = min(max_w / w, max_h / h)
    return Image(source, width=w * scale, height=h * scale)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(18 * mm, 10 * mm, "Weather Forecast Web App - Test Report")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build(results, meta, out_path):
    entries = []
    for r in results:
        number, label, text = parse_name(r["name"])
        entries.append({**r, "number": number, "label": label, "text": text})

    passed = sum(e["outcome"] == "passed" for e in entries)
    failed = sum(e["outcome"] == "failed" for e in entries)
    skipped = sum(e["outcome"] == "skipped" for e in entries)
    total = len(entries)
    rate = f"{100 * passed / total:.1f}%" if total else "0%"

    story = [
        Paragraph("Test Report", title_style),
        Paragraph(f"Weather Forecast Web App - {esc(meta.get('app_url', ''))}", sub_style),
        Paragraph("1. Summary", h1),
    ]
    summary = make_table(["Total", "Passed", "Failed", "Skipped", "Pass rate"], [[
        p(f"<b>{total}</b>"), p(f'<font color="{GREEN}"><b>{passed}</b></font>'),
        p(f'<font color="{RED}"><b>{failed}</b></font>'), p(f'<font color="{AMBER}"><b>{skipped}</b></font>'),
        p(f"<b>{rate}</b>"),
    ]], [34, 34, 34, 34, 34], repeat=False)
    story += [summary, Spacer(1, 6), summary_bar(passed, failed, skipped), Spacer(1, 4)]

    defect_entries = [e for e in entries if e["outcome"] == "failed" and e["number"] in DEFECTS]
    other_failures = [e for e in entries if e["outcome"] == "failed" and e["number"] not in DEFECTS]
    counts = {s: sum(DEFECTS[e["number"]][3] == s for e in defect_entries) for s in SEVERITY_COLORS}
    story.append(Paragraph(
        f"{len(defect_entries)} known defect(s) confirmed ({counts['Critical']} critical, {counts['Major']} major, "
        f"{counts['Minor']} minor) and {len(other_failures)} other failure(s) to investigate.", body))

    story.append(Paragraph("2. Test environment", h1))
    env_rows = [
        [p("Application", cell_bold), p(esc(meta.get("app_url", "")))],
        [p("Browser", cell_bold), p(esc(meta.get("browser", "")))],
        [p("Operating system", cell_bold), p(esc(meta.get("os", "")))],
        [p("Python / Selenium / pytest", cell_bold), p(esc(meta.get("tools", "")))],
        [p("Executed on", cell_bold), p(esc(meta.get("started", "")))],
        [p("Total run time", cell_bold), p(esc(meta.get("duration", "")))],
        [p("Test data", cell_bold), p(esc(meta.get("note", "")))],
    ]
    story.append(make_table(["Item", "Detail"], env_rows, [45, 125], repeat=False))

    story.append(Paragraph("3. Test results", h1))
    rows = []
    for e in entries:
        note = ""
        if e["outcome"] == "failed":
            note = esc(e["message"])
            if e["number"] in DEFECTS:
                note = f'<b>{DEFECTS[e["number"]][0]}</b> - ' + note
        elif e["outcome"] == "skipped":
            note = esc(e["message"])
        rows.append([p(esc(e["label"])), p(esc(e["text"])), p(status_text(e["outcome"])),
                     p(f'{e["duration"]:.1f}'), p(note)])
    story.append(make_table(["ID", "Test scenario", "Result", "Time (s)", "Notes"], rows, [14, 52, 15, 14, 75]))

    story.append(Paragraph("4. Defects found", h1))
    if not (defect_entries or other_failures):
        story.append(Paragraph("No defects were found in this run.", body))
    for e in sorted(defect_entries, key=lambda x: int(DEFECTS[x["number"]][0][1:])):
        did, title, category, severity = DEFECTS[e["number"]]
        info = Table([
            [p("Severity", cell_bold), p(severity_text(severity))],
            [p("Category", cell_bold), p(esc(category))],
            [p("Found by", cell_bold), p(esc(f'{e["label"]} - {e["text"]}'))],
            [p("Observed", cell_bold), p(esc(e["message"]))],
        ], colWidths=[28 * mm, 142 * mm])
        info.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, GREY),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        block = [Paragraph(f"{did}: {esc(title)}", h2), info]
        image = screenshot(e.get("screenshot"))
        if image:
            block += [Spacer(1, 4), image]
        block.append(Spacer(1, 6))
        story.append(KeepTogether(block))
    for e in other_failures:
        block = [Paragraph(f"Unexpected failure: {esc(e['label'])} - {esc(e['text'])}", h2), Paragraph(esc(e["message"]), body)]
        image = screenshot(e.get("screenshot"))
        if image:
            block += [Spacer(1, 4), image]
        story.append(KeepTogether(block + [Spacer(1, 6)]))

    story.append(Paragraph("5. Exploratory testing", h1))
    story.append(Paragraph(
        "Exploratory testing was organised in time-boxed sessions, each with a charter. The charters below guide the "
        "manual sessions. The observations list comes from inspecting the application code and behaviour; each one "
        "should be confirmed during a manual session.", body))
    story.append(make_table(["Charter", "Area", "Ideas explored"],
                            [[p(esc(a)), p(esc(b)), p(esc(c))] for a, b, c in CHARTERS], [18, 42, 110]))
    story.append(Paragraph("Observations", h2))
    story.append(make_table(["#", "Observation", "Category", "Severity"],
                            [[p(str(i)), p(esc(t)), p(esc(c)), p(severity_text(s))]
                             for i, (t, c, s) in enumerate(OBSERVATIONS, start=1)], [8, 106, 36, 20]))
    if SESSION_NOTES:
        story.append(Paragraph("Session notes", h2))
        story.append(make_table(["Session", "Charter", "Duration", "Notes and findings"],
                                [[p(esc(s.get("session", ""))), p(esc(s.get("charter", ""))),
                                  p(esc(s.get("duration", ""))), p(esc(s.get("notes", "")))] for s in SESSION_NOTES],
                                [18, 18, 20, 114]))

    story.append(Paragraph("6. Conclusion", h1))
    verdict = ("The application is not ready for release: " if counts["Critical"] or counts["Major"] else "The application can be released: ")
    story.append(Paragraph(
        f"{verdict}{passed} of {total} tests passed ({rate}). "
        f"Open defects: {counts['Critical']} critical, {counts['Major']} major, {counts['Minor']} minor. "
        "Critical and major defects should be fixed and the regression suite repeated before release.", body))

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="Test Report - Weather Forecast Web App")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out_path
