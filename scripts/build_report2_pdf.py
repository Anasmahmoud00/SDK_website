#!/usr/bin/env python3
"""Build a structured, print-ready PDF for Implementation & Testing Report 2.

Reads screenshots from docs/report2_figures/fig01.png … fig26.png
Writes docs/Implementation_And_Testing_Report_2.pdf

Usage (from repo root):
  python scripts/build_report2_pdf.py
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image as PILImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "docs" / "report2_figures"
OUT_PDF = ROOT / "docs" / "Implementation_And_Testing_Report_2.pdf"

# --- Visual system (academic / technical report) ---
NAVY = colors.HexColor("#0c1a2e")
NAVY_MID = colors.HexColor("#152a45")
ACCENT = colors.HexColor("#b8923a")
RULE = colors.HexColor("#d4dce6")
BODY = colors.HexColor("#1a2332")
MUTED = colors.HexColor("#5c6b7d")
PAPER = colors.HexColor("#f7f9fc")


def setup_times_fonts() -> dict[str, str]:
    """Register Times New Roman from Windows Fonts; fallback to built-in Times-Roman."""
    fd = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    mapping = [
        ("TimesNewRoman", "times.ttf"),
        ("TimesNewRoman-Bold", "timesbd.ttf"),
        ("TimesNewRoman-Italic", "timesi.ttf"),
        ("TimesNewRoman-BoldItalic", "timesbi.ttf"),
    ]
    out = {"reg": "Times-Roman", "bd": "Times-Bold", "it": "Times-Italic", "bi": "Times-BoldItalic"}
    try:
        for logical, fname in mapping:
            fp = fd / fname
            if not fp.exists():
                raise FileNotFoundError(fname)
            pdfmetrics.registerFont(TTFont(logical, str(fp)))
        out = {
            "reg": "TimesNewRoman",
            "bd": "TimesNewRoman-Bold",
            "it": "TimesNewRoman-Italic",
            "bi": "TimesNewRoman-BoldItalic",
        }
    except (OSError, FileNotFoundError):
        pass
    return out


def build_styles(fn: dict[str, str]):
    """fn = register_times_fonts() result."""
    base = getSampleStyleSheet()
    subtitle = ParagraphStyle(
        "Subtitle",
        parent=base["Normal"],
        fontSize=10,
        leading=13,
        alignment=TA_CENTER,
        textColor=BODY,
        spaceAfter=6,
        fontName=fn["reg"],
    )
    h1 = ParagraphStyle(
        "H1",
        parent=base["Heading1"],
        fontSize=14,
        leading=18,
        spaceBefore=18,
        spaceAfter=12,
        textColor=NAVY,
        fontName=fn["bd"],
        borderWidth=0,
        leftIndent=0,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=base["Heading2"],
        fontSize=11,
        leading=14,
        spaceBefore=14,
        spaceAfter=8,
        textColor=NAVY_MID,
        fontName=fn["bd"],
    )
    body = ParagraphStyle(
        "Body",
        parent=base["BodyText"],
        fontSize=10.5,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=9,
        textColor=BODY,
        fontName=fn["reg"],
    )
    cap = ParagraphStyle(
        "Caption",
        parent=base["Normal"],
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=MUTED,
        spaceBefore=5,
        spaceAfter=16,
        fontName=fn["it"],
    )
    small = ParagraphStyle(
        "Small",
        parent=base["Normal"],
        fontSize=8,
        leading=11,
        textColor=MUTED,
        alignment=TA_CENTER,
        fontName=fn["reg"],
    )
    closing = ParagraphStyle(
        "Closing",
        parent=base["BodyText"],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        textColor=BODY,
        spaceBefore=8,
        spaceAfter=6,
        fontName=fn["reg"],
    )
    cover_white_small = ParagraphStyle(
        "CoverWhiteSmall",
        parent=base["Normal"],
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#c8d4e4"),
        fontName=fn["reg"],
    )
    cover_white_title = ParagraphStyle(
        "CoverWhiteTitle",
        parent=base["Normal"],
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.white,
        fontName=fn["bd"],
        spaceBefore=6,
        spaceAfter=8,
    )
    cover_white_sub = ParagraphStyle(
        "CoverWhiteSub",
        parent=base["Normal"],
        fontSize=10.5,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#aebccf"),
        fontName=fn["reg"],
    )
    tbl_head = ParagraphStyle(
        "TblHead",
        parent=base["Normal"],
        fontName=fn["bd"],
        fontSize=9,
        leading=11,
        textColor=colors.white,
    )
    tbl_cell = ParagraphStyle(
        "TblCell",
        parent=base["Normal"],
        fontName=fn["reg"],
        fontSize=8.5,
        leading=11,
        textColor=BODY,
    )
    return {
        "subtitle": subtitle,
        "h1": h1,
        "h2": h2,
        "body": body,
        "cap": cap,
        "small": small,
        "closing": closing,
        "cover_white_small": cover_white_small,
        "cover_white_title": cover_white_title,
        "cover_white_sub": cover_white_sub,
        "tbl_head": tbl_head,
        "tbl_cell": tbl_cell,
        "fn": fn,
    }


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def section_heading(story, styles, number: str, title: str):
    """H1 with left accent rule (formal section marker)."""
    inner_w = 21 * cm - 3.6 * cm
    bd = styles["fn"]["bd"]
    ptext = f"<font name='{bd}' size='14' color='#0c1a2e'>{esc(number)} {esc(title)}</font>"
    cell = Paragraph(ptext, styles["body"])
    t = Table([[cell]], colWidths=[inner_w])
    t.setStyle(
        TableStyle(
            [
                ("LINEBEFORE", (0, 0), (0, 0), 3.5, ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(Spacer(1, 0.15 * cm))
    story.append(t)


def add_figure(story, styles, n: int, caption: str, max_w: float = 16 * cm, max_h: float = 19 * cm):
    path = FIG_DIR / f"fig{n:02d}.png"
    if not path.exists():
        story.append(Paragraph(esc(f"[Missing figure file: {path.name}]"), styles["body"]))
        story.append(Spacer(1, 0.2 * cm))
        return
    pil = PILImage.open(path)
    w, h = pil.size
    tw = float(max_w)
    th = tw * h / w
    if th > max_h:
        th = float(max_h)
        tw = th * w / h
    story.append(Spacer(1, 0.12 * cm))
    story.append(Image(str(path), width=tw, height=th))
    story.append(Paragraph(esc(f"Figure {n}. {caption}"), styles["cap"]))


def add_figure_pair(story, styles, left: tuple[int, str], right: tuple[int, str], max_w_each: float = 7.8 * cm):
    row = []
    for n, _cap in (left, right):
        path = FIG_DIR / f"fig{n:02d}.png"
        if not path.exists():
            row.append(Paragraph(esc(f"[Missing {path.name}]"), styles["small"]))
            continue
        pil = PILImage.open(path)
        w, h = pil.size
        tw = float(max_w_each)
        th = tw * h / w
        max_h = 14 * cm
        if th > max_h:
            th = float(max_h)
            tw = th * w / h
        row.append(Image(str(path), width=tw, height=th))
    if len(row) == 2:
        t = Table([[row[0], row[1]]], colWidths=[max_w_each + 0.2 * cm, max_w_each + 0.2 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(Spacer(1, 0.08 * cm))
        story.append(t)
        story.append(Paragraph(esc(f"Figure {left[0]}. {left[1]}"), styles["cap"]))
        story.append(Paragraph(esc(f"Figure {right[0]}. {right[1]}"), styles["cap"]))


def p(story, styles, text: str):
    story.append(Paragraph(esc(text), styles["body"]))


def px(story, styles, text: str):
    story.append(Paragraph(text, styles["body"]))


def table_frame_style():
    """Grid and fills only — cell text uses Paragraph styles (avoids overlap bugs)."""
    return [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, ACCENT),
        ("GRID", (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]


def paragraph_table(rows: list[list[str]], col_widths: list[float], styles: dict, *, repeat_rows: int = 1):
    """Build a Table with every cell as a Paragraph (correct row heights, no double-drawn text)."""
    th, tc = styles["tbl_head"], styles["tbl_cell"]
    data = []
    for ri, row in enumerate(rows):
        style = th if ri < repeat_rows else tc
        data.append([Paragraph(esc(cell), style) for cell in row])
    tbl = Table(data, colWidths=col_widths, repeatRows=repeat_rows)
    tbl.setStyle(TableStyle(table_frame_style()))
    return tbl


def on_first_page(_can: pdfcanvas.Canvas, _doc: SimpleDocTemplate) -> None:
    """Cover uses a navy banner table; no full-bleed canvas (avoids printer margins)."""
    return


def make_on_later_pages(footer_font: str):
    def on_later_pages(can: pdfcanvas.Canvas, doc: SimpleDocTemplate) -> None:
        can.saveState()
        pw, ph = A4
        can.setStrokeColor(RULE)
        can.setLineWidth(0.55)
        y_line = ph - doc.topMargin + 2
        can.line(doc.leftMargin, y_line, pw - doc.rightMargin, y_line)
        can.setFont(footer_font, 8)
        can.setFillColor(MUTED)
        left_txt = "Implementation & Testing Progress Report 2  ·  Team 16  ·  Narrative AI Framework"
        can.drawString(doc.leftMargin, 1.05 * cm, left_txt)
        can.drawRightString(pw - doc.rightMargin, 1.05 * cm, f"Page {can.getPageNumber()}")
        can.restoreState()

    return on_later_pages


def main():
    fonts = setup_times_fonts()
    styles = build_styles(fonts)
    story: list = []

    pw, _ph = A4
    content_w = pw - 3.6 * cm

    # --- Cover (navy banner + metadata) ---
    cover_rows = [
        [Paragraph("CSAI 499 &nbsp;·&nbsp; Senior Project &nbsp;·&nbsp; Week 12 deliverable", styles["cover_white_small"])],
        [Paragraph("Implementation &amp; Testing Progress Report 2", styles["cover_white_title"])],
        [Paragraph("Narrative AI Framework &nbsp;·&nbsp; Team 16", styles["cover_white_sub"])],
    ]
    cover_banner = Table(cover_rows, colWidths=[content_w])
    cover_banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (0, 0), 26),
                ("BOTTOMPADDING", (-1, -1), (-1, -1), 22),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("LINEBELOW", (0, -1), (-1, -1), 2, ACCENT),
            ]
        )
    )
    story.append(cover_banner)
    story.append(Spacer(1, 0.65 * cm))

    meta_block = Paragraph(
        "<b>Project title.</b> Narrative AI: multi-tenant voice and text diary framework "
        "(Egyptian Arabic).<br/><br/>"
        "<b>Supervisor.</b> Dr. Khaled Mostafa El Sayed<br/><br/>"
        "<b>Repository.</b> github.com/Baher-Nader/narrative-ai-framework (private)",
        styles["subtitle"],
    )
    story.append(meta_block)
    story.append(Spacer(1, 0.65 * cm))

    team_tbl = paragraph_table(
        [
            ["Name", "Program"],
            ["Baher Nader", "DSAI"],
            ["Anas Mahmoud", "DSAI"],
            ["Hossam Amir", "DSAI"],
            ["Yousef Ashour", "DSAI"],
        ],
        [content_w / 2, content_w / 2],
        styles,
        repeat_rows=1,
    )
    story.append(team_tbl)
    story.append(Spacer(1, 0.45 * cm))
    story.append(
        Paragraph(
            "<b>Report date:</b> May 2026 &nbsp;&nbsp;&nbsp; <b>Academic year:</b> October 2025 &ndash; September 2026",
            styles["subtitle"],
        )
    )
    story.append(PageBreak())

    # --- Section 1 ---
    section_heading(story, styles, "1.", "Project status and progress")
    story.append(Paragraph("1.1 Summary since MVP", styles["h2"]))
    p(
        story,
        styles,
        "Since Implementation & Testing Report 1 (March 2026), the project has moved from a feature-complete MVP to "
        "a deployable, test-gated system. The private narrative-ai-framework repository supports multi-branch development, "
        "automated regression testing on the order of one thousand passing tests in continuous integration, and repeatable "
        "release pipelines to Oracle Cloud Infrastructure and to DigitalOcean, each terminating in post-deploy /health "
        "verification. The Hekayti mobile client demonstrates voice sessions, bilingual chat with web-grounded answers, "
        "calendar and journal capture, OCR-assisted scan-to-text, companion voice configuration, and session summaries that "
        "exercise memory-style recall. Model work includes Arabic–English code-switching automatic speech recognition "
        "evaluation (word error rate), multilingual text-to-speech fine-tuning with composite quality metrics, and "
        "vision-language OCR in the scan workflow. Scheduled remote backups and Droplet telemetry complete the operational "
        "picture.",
    )
    story.append(Paragraph("1.2 Completion estimate and residual risks", styles["h2"]))
    px(
        story,
        styles,
        "<b>Estimated completion.</b> Approximately 94%. Remaining work is concentrated in defense preparation: a single "
        "authoritative description of the production host for examination purposes, an optional supplementary ASR evaluation "
        "if a lower word error rate is to be asserted beyond the run documented herein, and reduction of non-blocking "
        "warnings in the automated test logs.",
    )
    px(
        story,
        styles,
        "<b>Risks.</b> Both OCI and DigitalOcean automation appear in the evidence set; the oral defense should state one "
        "primary production deployment while retaining the other as contingency documentation. The ASR figure in this report "
        "records a final WER of 23.78%; reporting a materially lower figure requires a separate, dated evaluation artifact.",
    )

    story.append(Paragraph("1.3 Repository, branching, and continuous integration", styles["h2"]))
    add_figure(
        story,
        styles,
        1,
        "GitHub: private narrative-ai-framework repository, directory layout, recent activity, contributor list.",
    )
    add_figure(
        story,
        styles,
        2,
        "Branch overview: default main with required checks; active feature and integration branches.",
    )
    add_figure(
        story,
        styles,
        3,
        "GitHub Actions: test, deployment, scheduled backup, and infrastructure workflow history.",
    )

    story.append(Paragraph("1.4 Release automation (OCI and DigitalOcean)", styles["h2"]))
    add_figure(
        story,
        styles,
        4,
        "OCI pipeline: automated tests, container build and registry push, compute deployment (successful run).",
    )
    add_figure(
        story,
        styles,
        5,
        "DigitalOcean: secure copy of compose stack and configuration, image build on the Droplet, migrations, health wait.",
    )
    add_figure(
        story,
        styles,
        6,
        "Scheduled production backup: remote execution via SSH action.",
    )

    story.append(Paragraph("1.5 System architecture", styles["h2"]))
    add_figure(
        story,
        styles,
        7,
        "Layered platform: presentation, API gateway (FastAPI), application logic, domain engines, infrastructure services.",
        max_h=17 * cm,
    )
    add_figure(
        story,
        styles,
        23,
        "Retrieval and companion flow: multimodal ingestion, hybrid retrieval, reranking, and streaming response path.",
        max_h=17 * cm,
    )

    story.append(Paragraph("1.6 Mobile application (Hekayti)", styles["h2"]))
    add_figure_pair(
        story,
        styles,
        (8, "Home screen: primary voice entry and journal shortcuts."),
        (9, "Home screen (alternate theme): conversational prompt and navigation."),
    )
    add_figure(
        story,
        styles,
        19,
        "Navigation drawer: voice journal, composition, scan, account, and data portability.",
        max_w=11 * cm,
        max_h=16 * cm,
    )
    add_figure_pair(
        story,
        styles,
        (10, "Companion chat: bilingual reply with cited web sources."),
        (11, "Companion chat: mixed Arabic–English query with structured factual answer."),
    )
    add_figure(
        story,
        styles,
        12,
        "Session summary: quantitative session metadata and excerpted dialogue.",
    )
    add_figure(
        story,
        styles,
        14,
        "Voice session: assistant state, timer, and microphone control.",
    )
    add_figure(
        story,
        styles,
        13,
        "Handwriting OCR: camera capture versus model transcription (processed state).",
    )
    add_figure(
        story,
        styles,
        15,
        "Journal editor: structured entry with media attachments.",
    )
    add_figure_pair(
        story,
        styles,
        (16, "Profile: engagement summary and account management."),
        (17, "Settings: synthetic voice selection, locale, and privacy controls."),
    )
    add_figure(
        story,
        styles,
        18,
        "Calendar: date selection and capture actions (write or record).",
    )

    story.append(PageBreak())

    # --- Section 2 ---
    section_heading(story, styles, "2.", "Feature completion")
    feat_tbl = paragraph_table(
        [
            ["Deliverable", "Owner", "Status", "Evidence"],
            ["Private GitHub repository and collaboration model", "Team", "Complete", "Fig. 1–3"],
            [
                "Continuous integration: automated test suite (1020 passed, captured run)",
                "B. Nader, A. Mahmoud",
                "Complete",
                "Fig. 20, 24",
            ],
            ["CI/CD: Oracle Cloud deployment", "A. Mahmoud, B. Nader", "Complete", "Fig. 4"],
            ["CI/CD: DigitalOcean deployment", "A. Mahmoud, B. Nader", "Complete", "Fig. 5"],
            ["Scheduled production backups", "A. Mahmoud", "Complete", "Fig. 6"],
            ["Architecture documentation (layered stack and RAG pipeline)", "B. Nader, H. Amir", "Complete", "Fig. 7, 23"],
            [
                "Mobile client: navigation, chat, voice, memory, OCR, journal, profile, settings, calendar",
                "Team",
                "Complete",
                "Fig. 8–19",
            ],
            ["ASR evaluation (WER)", "Y. Ashour", "Complete", "Fig. 21"],
            ["TTS fine-tuning evaluation", "Y. Ashour", "Complete", "Fig. 22"],
            ["Cloud host provisioning and monitoring", "A. Mahmoud", "Complete", "Fig. 25–26"],
        ],
        [6.0 * cm, 3.4 * cm, 1.6 * cm, 2.6 * cm],
        styles,
        repeat_rows=1,
    )
    story.append(feat_tbl)
    story.append(PageBreak())

    # --- Section 3 ---
    section_heading(story, styles, "3.", "Remaining work and schedule")
    plan_tbl = paragraph_table(
        [
            ["Item", "Owner", "Priority", "Target", "State"],
            [
                "Finalize single production-host narrative for examination",
                "A. Mahmoud",
                "High",
                "Week 13",
                "Open",
            ],
            [
                "Optional supplementary ASR evaluation if reporting WER below 23.78%",
                "Y. Ashour",
                "High",
                "Week 13",
                "Optional",
            ],
            ["Clear residual CI warnings (mocks, numerical edge cases)", "B. Nader", "Medium", "Week 13", "Planned"],
            ["Defense demonstration rehearsal", "All", "High", "Week 13", "Planned"],
        ],
        [5.4 * cm, 2.0 * cm, 1.7 * cm, 2.0 * cm, 2.3 * cm],
        styles,
        repeat_rows=1,
    )
    story.append(plan_tbl)
    story.append(PageBreak())

    # --- Section 4 ---
    section_heading(story, styles, "4.", "Testing and verification")
    story.append(Paragraph("4.1 Automated regression (continuous integration)", styles["h2"]))
    add_figure(
        story,
        styles,
        20,
        "Excerpt from CI log: speech and vision pipeline tests; aggregate result 1020 passed.",
    )
    add_figure(
        story,
        styles,
        24,
        "Corroborating CI run: same regression gate on the integration branch.",
    )
    story.append(Paragraph("4.2 Model evaluation", styles["h2"]))
    add_figure(
        story,
        styles,
        21,
        "Speech recognition: aggregate WER and reference–hypothesis pairs (code-switching).",
    )
    add_figure(
        story,
        styles,
        22,
        "Speech synthesis: baseline versus fine-tuned acoustic and composite metrics.",
    )
    story.append(Paragraph("4.3 Scope of automated cases and post-fix validation", styles["h2"]))
    p(
        story,
        styles,
        "The logs excerpted above include short and empty audio inputs for emotion-side logic, success and failure paths "
        "for the speech-to-text processor, and a functional exercise of the OCR HTTP surface. Deployment workflows were "
        "iterated until green; the DigitalOcean job includes an explicit wait on the /health endpoint (Figure 5).",
    )
    story.append(PageBreak())

    # --- Section 5 ---
    section_heading(story, styles, "5.", "Individual technical contribution")
    p(
        story,
        styles,
        "Contribution shares follow the equal twenty-five percent allocation established in Implementation & Testing Report 1. "
        "The division below maps each member to the subsystem evidence in Sections 1 and 4.",
    )
    ct = paragraph_table(
        [
            ["Member", "Program", "Primary responsibility", "Share"],
            ["Baher Nader", "DSAI", "Backend services, mobile implementation, CI hardening, DigitalOcean path", "25%"],
            ["Anas Mahmoud", "DSAI", "Cloud automation, GitHub Actions, backups, observability", "25%"],
            ["Hossam Amir", "DSAI", "Retrieval and companion orchestration, grounded dialogue, memory UX", "25%"],
            ["Yousef Ashour", "DSAI", "Acoustic and speech synthesis evaluation, OCR integration", "25%"],
        ],
        [3.0 * cm, 1.9 * cm, 8.3 * cm, 1.5 * cm],
        styles,
        repeat_rows=1,
    )
    story.append(ct)
    story.append(PageBreak())

    # --- Section 6 ---
    section_heading(story, styles, "6.", "Production environment")
    p(
        story,
        styles,
        "The current production virtual machine runs Ubuntu LTS on DigitalOcean. The following captures the instance "
        "summary and seven consecutive days of CPU, load average, and memory utilization.",
    )
    add_figure(
        story,
        styles,
        25,
        "Droplet summary: identifier, region, addressing, and billing tier.",
    )
    add_figure(
        story,
        styles,
        26,
        "Host telemetry: CPU, load, and memory over a one-week window.",
    )

    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            "This submission compiles implementation status, completed deliverables, verification artifacts, and "
            "attribution for Week 12. Factual claims rest on Figures 1–26 and on the version-controlled repository cited on "
            "the cover page.",
            styles["closing"],
        )
    )

    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.65 * cm,
        title="Implementation and Testing Report 2",
        author="Team 16",
    )
    doc.build(story, onFirstPage=on_first_page, onLaterPages=make_on_later_pages(fonts["reg"]))
    print(f"Wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
