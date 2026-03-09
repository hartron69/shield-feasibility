"""
Board-Ready PDF Report Generator.

Layout (13 pages)
-----------------
  P1   Cover page
  P2   Executive Summary + Verdict banner
  P3   Operator Risk Profile
  P4   Monte Carlo Simulation Results
  P5   Strategy Comparison Matrix
  P6   Chart – Loss Distribution
  P7   Chart – Cumulative Cost Curves + Annual Comparison
  P8   SCR Analysis Table + Chart
  P9   Chart – Cost–Risk Frontier + Box & Whisker
  P10  Suitability Assessment – Criteria Scores
  P11  Chart – Radar + Recommendation
  P12  Implementation Roadmap & Next Steps
  P13  Assumptions, Methodology & Disclaimer
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether, HRFlowable, PageBreak, NextPageTemplate,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from data.input_schema import OperatorInput
from models.monte_carlo import SimulationResults
from models.strategies.base_strategy import StrategyResult
from analysis.scr_calculator import SCRResult
from analysis.cost_analyzer import CostAnalysis
from analysis.volatility_metrics import VolatilityAnalysis
from analysis.suitability_engine import Recommendation
from reporting.chart_generator import generate_all_charts
from reporting.correlated_risk_analytics import (
    build_correlated_risk_summary, CorrelatedRiskSummary,
    DOMAIN_LABELS, DOMAIN_COLOURS, fmt_corr_label,
)
from config.settings import SETTINGS


# ─────────────────────────────────────────────────────────────────────────────
# Colours (ReportLab HexColor)
# ─────────────────────────────────────────────────────────────────────────────
NAVY  = colors.HexColor("#172D5A")
TEAL  = colors.HexColor("#0D8F99")
GOLD  = colors.HexColor("#CC9A1A")
LGREY = colors.HexColor("#F0F0F0")
MGREY = colors.HexColor("#CCCCCC")
DGREY = colors.HexColor("#4D4D4D")
WHITE = colors.white
BLACK = colors.black

VERDICT_COLOURS = {
    "STRONGLY RECOMMENDED": colors.HexColor("#1B5E20"),
    "RECOMMENDED":          colors.HexColor("#2E7D32"),
    "POTENTIALLY SUITABLE": colors.HexColor("#E65100"),
    "NOT RECOMMENDED":      colors.HexColor("#B71C1C"),
    "NOT SUITABLE":         colors.HexColor("#880E4F"),
}

STRATEGY_COLOURS_RL = {
    "Full Insurance":    colors.HexColor("#1565C0"),
    "Hybrid":            colors.HexColor("#00897B"),
    "PCC Captive Cell":  colors.HexColor("#F9A825"),
    "Self-Insurance":    colors.HexColor("#C62828"),
}

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm


# ─────────────────────────────────────────────────────────────────────────────
# Helper: format money
# ─────────────────────────────────────────────────────────────────────────────
def _m(v: float, decimals: int = 1) -> str:
    """Formater beløp i NOK – store tall vises i millioner."""
    if abs(v) >= 1_000_000_000:
        return f"NOK {v/1_000_000_000:,.{decimals}f} Mrd"
    elif abs(v) >= 1_000_000:
        return f"NOK {v/1_000_000:,.{decimals}f} M"
    elif abs(v) >= 1_000:
        return f"NOK {v/1_000:,.0f} k"
    return f"NOK {v:,.0f}"


def _pct(v: float) -> str:
    return f"{v:.1%}"


# ─────────────────────────────────────────────────────────────────────────────
# Style sheet
# ─────────────────────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()
    S = {}

    def add(name, **kwargs):
        S[name] = ParagraphStyle(name, **kwargs)

    add("cover_title",    fontSize=28, leading=34, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_LEFT, spaceAfter=6)
    add("cover_sub",      fontSize=14, leading=18, textColor=GOLD,
        fontName="Helvetica-Bold", alignment=TA_LEFT, spaceAfter=4)
    add("cover_meta",     fontSize=9,  leading=13, textColor=LGREY,
        fontName="Helvetica", alignment=TA_LEFT)
    add("section_head",   fontSize=13, leading=17, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_LEFT, spaceAfter=4,
        spaceBefore=2, leftIndent=6)
    add("sub_head",       fontSize=10, leading=14, textColor=NAVY,
        fontName="Helvetica-Bold", alignment=TA_LEFT, spaceBefore=8, spaceAfter=4)
    add("body",           fontSize=8.5, leading=12.5, textColor=DGREY,
        fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=5)
    add("body_small",     fontSize=7.5, leading=11, textColor=DGREY,
        fontName="Helvetica", alignment=TA_LEFT)
    add("table_header",   fontSize=8, leading=10, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER)
    add("table_cell",     fontSize=8, leading=10, textColor=DGREY,
        fontName="Helvetica", alignment=TA_CENTER)
    add("table_cell_l",   fontSize=8, leading=10, textColor=DGREY,
        fontName="Helvetica", alignment=TA_LEFT)
    add("verdict_text",   fontSize=18, leading=22, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER)
    add("score_label",    fontSize=8.5, leading=12, textColor=DGREY,
        fontName="Helvetica-Bold", alignment=TA_LEFT)
    add("bullet",         fontSize=8.5, leading=12, textColor=DGREY,
        fontName="Helvetica", alignment=TA_LEFT,
        leftIndent=12, firstLineIndent=-8, spaceAfter=3)
    add("caption",        fontSize=7.5, leading=10, textColor=DGREY,
        fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=4)
    add("disclaimer",     fontSize=7, leading=10, textColor=MGREY,
        fontName="Helvetica", alignment=TA_JUSTIFY)

    return S


# ─────────────────────────────────────────────────────────────────────────────
# Page decorators (header/footer called by ReportLab)
# ─────────────────────────────────────────────────────────────────────────────

class _PageCanvas:
    """Mixin that draws header band and footer on every page except cover."""

    def __init__(self, operator_name: str, report_date: str):
        self.op_name = operator_name
        self.report_date = report_date

    def draw_header(self, canvas, doc):
        if doc.page == 1:
            return
        canvas.saveState()
        # Header band
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - 1.3 * cm, PAGE_W, 1.3 * cm, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(MARGIN, PAGE_H - 0.85 * cm,
                          f"PCC Feasibility & Suitability Analysis  |  {self.op_name}")
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.85 * cm,
                               f"{SETTINGS.report_classification}")
        canvas.restoreState()

    def draw_footer(self, canvas, doc):
        if doc.page == 1:
            return
        canvas.saveState()
        canvas.setStrokeColor(MGREY)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, 1.1 * cm, PAGE_W - MARGIN, 1.1 * cm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MGREY)
        canvas.drawString(MARGIN, 0.65 * cm,
                          f"Prepared by {SETTINGS.report_author}  •  {self.report_date}")
        canvas.drawRightString(PAGE_W - MARGIN, 0.65 * cm, f"Page {doc.page}")
        canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# Main PDF generator
# ─────────────────────────────────────────────────────────────────────────────

class PDFReportGenerator:
    """
    Orchestrates the full PDF build pipeline.

    Usage::
        gen = PDFReportGenerator(operator, sim, strategy_results,
                                 scr_results, cost_analysis, vol_metrics,
                                 recommendation, "output.pdf")
        gen.generate()
    """

    def __init__(
        self,
        operator: OperatorInput,
        simulation_results: SimulationResults,
        strategy_results: Dict[str, StrategyResult],
        scr_results: Dict[str, SCRResult],
        cost_analysis: CostAnalysis,
        vol_metrics: VolatilityAnalysis,
        recommendation: Recommendation,
        output_path: str,
        domain_loss_breakdown=None,   # Optional[DomainLossBreakdown] – Sprint 7
        domain_correlation=None,      # Optional[DomainCorrelationMatrix] – Sprint 7
    ):
        self.op = operator
        self.sim = simulation_results
        self.strategies = strategy_results
        self.scr = scr_results
        self.cost = cost_analysis
        self.vol = vol_metrics
        self.rec = recommendation
        self.output_path = output_path
        self.report_date = datetime.now().strftime("%d %B %Y")
        self.S = _build_styles()
        self.domain_correlation = domain_correlation

        # Sprint 7 – build correlated risk analytics (graceful if dbd is None)
        self.corr_summary: Optional[CorrelatedRiskSummary] = build_correlated_risk_summary(
            annual_losses=simulation_results.annual_losses,
            dbd=domain_loss_breakdown,
        )

        # Pre-render all charts
        print("      Rendering charts...", end="", flush=True)
        self.charts = generate_all_charts(
            sim=simulation_results,
            strategy_results=strategy_results,
            scr_results=scr_results,
            cost_analysis=cost_analysis,
            vol_analysis=vol_metrics,
            recommendation=recommendation,
            correlated_risk_summary=self.corr_summary,
            domain_correlation=domain_correlation,
        )
        print(" done.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _p(self, text: str, style: str = "body") -> Paragraph:
        return Paragraph(text, self.S[style])

    def _section_banner(self, title: str) -> Table:
        """Navy banner with white section title."""
        t = Table([[Paragraph(title, self.S["section_head"])]], colWidths=[PAGE_W - 2 * MARGIN])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return t

    def _chart_image(self, key: str, width: float = 16 * cm) -> Image:
        buf = self.charts[key]
        buf.seek(0)
        img = Image(buf, width=width, height=width * 0.5, kind="proportional")
        return img

    def _chart_image_safe(self, key: str, width: float = 16 * cm) -> Optional[Image]:
        """Return chart Image if available, None otherwise (graceful fallback)."""
        if key not in self.charts:
            return None
        return self._chart_image(key, width=width)

    def _hr(self) -> HRFlowable:
        return HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=4, spaceBefore=4)

    def _bullet_list(self, items, style="bullet") -> list:
        return [Paragraph(f"• {item}", self.S[style]) for item in items]

    # ── Page 1: Cover ─────────────────────────────────────────────────────────

    def _cover_page(self, canvas, doc):
        canvas.saveState()

        # Full-page navy background
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

        # Gold accent bar (left edge)
        canvas.setFillColor(GOLD)
        canvas.rect(0, 0, 0.6 * cm, PAGE_H, fill=1, stroke=0)

        # Teal accent stripe
        canvas.setFillColor(TEAL)
        canvas.rect(0, PAGE_H * 0.38, PAGE_W, 0.15 * cm, fill=1, stroke=0)

        # Title text
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 28)
        canvas.drawString(2.2 * cm, PAGE_H * 0.72, "PCC Feasibility &")
        canvas.drawString(2.2 * cm, PAGE_H * 0.65, "Suitability Analysis")

        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(2.2 * cm, PAGE_H * 0.60, "Fish Farming Risk Management Platform")

        # Operator block
        canvas.setFillColor(colors.HexColor("#1E3A6E"))
        canvas.rect(2.0 * cm, PAGE_H * 0.43, PAGE_W - 4 * cm, 0.15 * cm * 7, fill=1, stroke=0)

        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(2.4 * cm, PAGE_H * 0.475, f"Operator:  {self.op.name}")
        canvas.setFont("Helvetica", 9.5)
        canvas.drawString(2.4 * cm, PAGE_H * 0.448, f"Registration:  {self.op.registration_number}  |  {self.op.country}")
        canvas.drawString(2.4 * cm, PAGE_H * 0.423, f"Date of Report:  {self.report_date}")
        canvas.drawString(2.4 * cm, PAGE_H * 0.399, f"Simulations:  {self.sim.n_simulations:,}  |  Horizon:  {self.sim.projection_years} Years")

        # Verdict badge
        verdict = self.rec.verdict
        v_col = VERDICT_COLOURS.get(verdict.split("–")[0].strip(), colors.HexColor("#1B5E20"))
        canvas.setFillColor(v_col)
        badge_y = PAGE_H * 0.28
        canvas.roundRect(2.0 * cm, badge_y, PAGE_W - 4 * cm, 1.6 * cm, 0.3 * cm, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawCentredString(PAGE_W / 2, badge_y + 0.5 * cm, verdict)
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(PAGE_W / 2, badge_y + 0.2 * cm,
                                 f"Composite Suitability Score:  {self.rec.composite_score:.1f} / 100")

        # Footer
        canvas.setFillColor(MGREY)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(2.2 * cm, 1.2 * cm,
                          f"{SETTINGS.report_classification}  |  Prepared by {SETTINGS.report_author}")
        canvas.drawRightString(PAGE_W - 2.2 * cm, 1.2 * cm, "Page 1")

        canvas.restoreState()

    # ── Page build methods ────────────────────────────────────────────────────

    def _build_exec_summary(self) -> list:
        S = self.S
        story = []
        story.append(self._section_banner("EXECUTIVE SUMMARY"))
        story.append(Spacer(1, 0.3 * cm))

        # Verdict banner
        verdict = self.rec.verdict
        v_col = VERDICT_COLOURS.get(verdict.split("–")[0].strip(), colors.HexColor("#1B5E20"))

        verdict_table = Table(
            [[Paragraph(f"VERDICT:  {verdict}  |  Score: {self.rec.composite_score:.1f}/100",
                        S["verdict_text"])]],
            colWidths=[PAGE_W - 2 * MARGIN],
        )
        verdict_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), v_col),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(verdict_table)
        story.append(Spacer(1, 0.4 * cm))

        story.append(self._p(self.rec.executive_summary))
        story.append(Spacer(1, 0.3 * cm))

        # Strengths / Barriers two-column
        col_w = (PAGE_W - 2 * MARGIN - 0.4 * cm) / 2

        def _col_block(title, items, bg):
            rows = [[Paragraph(title, S["sub_head"])]] + \
                   [[Paragraph(f"✓  {i}", S["body_small"])] for i in items] if items else \
                   [[Paragraph(title, S["sub_head"])], [Paragraph("None identified.", S["body_small"])]]
            t = Table(rows, colWidths=[col_w])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), bg),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
            ]))
            return t

        str_block = _col_block("Key Strengths", self.rec.key_strengths, colors.HexColor("#1B5E20"))
        bar_block = _col_block("Key Barriers", self.rec.key_barriers, colors.HexColor("#B71C1C"))

        two_col = Table([[str_block, bar_block]], colWidths=[col_w, col_w])
        two_col.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(two_col)
        story.append(Spacer(1, 0.4 * cm))

        if self.rec.conditions:
            story.append(self._p("Prerequisites & Conditions", "sub_head"))
            story.extend(self._bullet_list(self.rec.conditions))

        return story

    def _build_risk_profile(self) -> list:
        S = self.S
        story = [self._section_banner("OPERATOR RISK PROFILE"), Spacer(1, 0.3 * cm)]

        # Site table
        story.append(self._p("Production Sites", "sub_head"))
        headers = ["Anlegg", "Art", "Sted", "Biomasse (t)", "Verdi/t (NOK)", "TIV (M NOK)", "Omsetning (M NOK)"]
        rows = [headers]
        for site in self.op.sites:
            rows.append([
                site.name, site.species, site.location,
                f"{site.biomass_tonnes:,.0f}",
                f"{site.biomass_value_per_tonne:,.0f} NOK",
                _m(site.total_insured_value),
                _m(site.annual_revenue),
            ])
        # Total row
        rows.append([
            "TOTAL", "", "",
            f"{sum(s.biomass_tonnes for s in self.op.sites):,.0f}", "",
            _m(self.op.total_insured_value),
            _m(self.op.total_annual_revenue),
        ])

        col_ws = [3.5*cm, 3*cm, 3*cm, 1.6*cm, 1.6*cm, 1.8*cm, 1.8*cm]
        t = Table(rows, colWidths=col_ws)
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (3, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (2, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LGREY]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1E3A6E")),
            ("TEXTCOLOR", (0, -1), (-1, -1), WHITE),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ])
        t.setStyle(style)
        story.append(t)
        story.append(Spacer(1, 0.4 * cm))

        # Financial profile
        story.append(self._p("Financial Profile", "sub_head"))
        fin = self.op.financials
        fin_data = [
            ["Annual Revenue", _m(fin.annual_revenue), "EBITDA", _m(fin.ebitda)],
            ["Total Assets", _m(fin.total_assets), "Net Equity", _m(fin.net_equity)],
            ["Free Cash Flow", _m(fin.free_cash_flow), "Credit Rating", fin.credit_rating or "N/R"],
            ["Years Operating", str(fin.years_in_operation), "EBITDA Margin", _pct(fin.ebitda / max(fin.annual_revenue, 1))],
        ]
        col_w2 = (PAGE_W - 2 * MARGIN) / 4
        ft = Table(fin_data, colWidths=[col_w2] * 4)
        ft.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
            ("TEXTCOLOR", (2, 0), (2, -1), NAVY),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LGREY]),
            ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(ft)
        story.append(Spacer(1, 0.4 * cm))

        # Current insurance
        story.append(self._p("Current Insurance Programme", "sub_head"))
        ins = self.op.current_insurance
        ins_data = [
            ["Annual Premium", _m(ins.annual_premium), "Per-Occurrence Deductible", _m(ins.per_occurrence_deductible)],
            ["Annual Aggregate Deductible", _m(ins.annual_aggregate_deductible), "Coverage Limit", _m(ins.coverage_limit)],
            ["Historical Loss Ratio", _pct(ins.current_loss_ratio), "Market Rating Trend (p.a.)", _pct(ins.market_rating_trend)],
            ["Coverage Lines", ", ".join(ins.coverage_lines[:3]), "Insurers", ", ".join(ins.insurer_names[:2])],
        ]
        it = Table(ins_data, colWidths=[col_w2] * 4)
        it.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
            ("TEXTCOLOR", (2, 0), (2, -1), NAVY),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LGREY]),
            ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (1, -1), (-1, -1), "LEFT"),
        ]))
        story.append(it)

        return story

    def _build_simulation_results(self) -> list:
        S = self.S
        story = [self._section_banner("MONTE CARLO SIMULATION RESULTS"), Spacer(1, 0.3 * cm)]

        story.append(self._p(
            f"The loss model uses a compound Poisson–LogNormal distribution with "
            f"{self.sim.n_simulations:,} independent simulations per year across a "
            f"{self.sim.projection_years}-year projection horizon. "
            f"Catastrophic events are modelled as an independent overlay process with "
            f"annual probability {_pct(self.op.risk_params.catastrophe_probability)}."
        ))
        story.append(Spacer(1, 0.3 * cm))

        # Key statistics table
        stat_data = [
            ["Metric", "Value", "Interpretation"],
            ["Mean Annual Loss", _m(self.sim.mean_annual_loss), "Long-run average annual gross loss"],
            ["Median Annual Loss", _m(self.sim.median_annual_loss), "50th percentile outcome"],
            ["Std Dev of Annual Loss", _m(self.sim.std_annual_loss), "Year-to-year variability"],
            ["Loss CV (σ/μ)", f"{self.sim.std_annual_loss/max(self.sim.mean_annual_loss,1):.2f}", "Volatility index"],
            ["VaR 90% (1-year)", _m(self.sim.var_90), "1-in-10 year loss level"],
            ["VaR 95% (1-year)", _m(self.sim.var_95), "1-in-20 year loss level"],
            ["VaR 99% (1-year)", _m(self.sim.var_99), "1-in-100 year loss level"],
            ["VaR 99.5% (SCR) (1-year)", _m(self.sim.var_995), "Solvency II SCR anchor"],
            ["TVaR 95% (1-year)", _m(self.sim.tvar_95), "Expected loss beyond 95th pctl"],
            ["Mean Avg Annual Events", f"{self.sim.mean_event_count:.1f}", "Expected loss-producing events/yr"],
            ["Mean Severity per Event", _m(self.sim.mean_event_severity), "Average cost per claim event"],
            ["5-Year Aggregate VaR 99.5%", _m(self.sim.var_5yr_995), "Worst-case 5-yr cumulative loss"],
        ]

        col_ws = [5.5 * cm, 3.5 * cm, 8.5 * cm]
        st = Table(stat_data, colWidths=col_ws)
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 7), (-1, 7), colors.HexColor("#FFF8E1")),
            ("FONTNAME", (0, 7), (-1, 7), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 7), (-1, 7), colors.HexColor("#B71C1C")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGREY]),
            ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(st)
        story.append(Spacer(1, 0.4 * cm))
        story.append(self._chart_image("loss_distribution", width=16 * cm))
        story.append(self._p(
            "Figure 1 – Simulated annual gross loss distribution with key VaR thresholds. "
            "The heavy right tail reflects catastrophic mortality / property events.",
            "caption",
        ))
        return story

    def _build_strategy_comparison(self) -> list:
        S = self.S
        story = [self._section_banner("STRATEGY COMPARISON MATRIX"), Spacer(1, 0.3 * cm)]

        story.append(self._p(
            "Four risk-transfer structures are modelled: Full Market Insurance (baseline), "
            "Hybrid Large-Deductible Programme, PCC Protected Cell Company, and Full "
            "Selvforsikring. Alle kostnader er oppgitt i nominelle NOK (millioner) om ikke annet er angitt."
        ))
        story.append(Spacer(1, 0.3 * cm))

        # Main comparison table
        names = list(self.strategies.keys())
        headers = ["Metric"] + names

        def _row(label, vals):
            return [label] + vals

        rows = [headers,
            _row("5-Yr Total Cost (nominal)", [_m(self.strategies[n].total_5yr_cost) for n in names]),
            _row("5-Yr Total Cost (NPV)", [_m(self.strategies[n].total_5yr_cost_npv) for n in names]),
            _row("Mean Annual Cost", [_m(self.strategies[n].total_5yr_cost / 5) for n in names]),
            _row("vs. Full Insurance (5-yr save)", [
                _m(self.cost.summaries[n].vs_baseline_savings_5yr) for n in names
            ]),
            _row("vs. Full Insurance (%)", [
                _pct(self.cost.summaries[n].vs_baseline_savings_pct) for n in names
            ]),
            _row("Annual Cost Std Dev", [_m(self.strategies[n].cost_std) for n in names]),
            _row("Annual Cost VaR 99.5%", [_m(self.strategies[n].cost_var_995) for n in names]),
            _row("Required Capital", [_m(self.strategies[n].required_capital) for n in names]),
            _row("Break-Even Year", [
                str(self.strategies[n].breakeven_year or "—") for n in names
            ]),
        ]

        col_ws = [4.5 * cm] + [(PAGE_W - 2 * MARGIN - 4.5 * cm) / len(names)] * len(names)
        ct = Table(rows, colWidths=col_ws)
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 1), (0, -1), NAVY),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGREY]),
            # Highlight PCC column
            ("BACKGROUND", (3, 1), (3, -1), colors.HexColor("#FFFDE7")),
            ("TEXTCOLOR", (3, 1), (3, -1), colors.HexColor("#F57F17")),
            ("FONTNAME", (3, 1), (3, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(ct)
        story.append(Spacer(1, 0.3 * cm))
        story.append(self._p(
            "Merknad: PCC Captive Cell-kolonnen er uthevet. "
            "Besparelser vs. full forsikring er nominelle 5-årsaggregater i NOK. "
            "NPV diskontert med risikofri rente "
            f"{_pct(SETTINGS.risk_free_rate)}.",
            "body_small",
        ))

        return story

    def _build_pcc_cost_breakdown(self) -> list:
        """
        Transparent annual cost breakdown for the PCC Captive Cell strategy.

        Shows each cost component separately so readers can verify the economics:
        net premium (to cell), fronting fee, RI premium, admin, capital opportunity
        cost, and investment income.  The RI premium row is highlighted in amber
        when it exceeds 30% of the net premium (i.e. a meaningful cost driver).
        """
        pcc_result = self.strategies.get("PCC Captive Cell")
        if not pcc_result or not pcc_result.annual_breakdown:
            return []

        S = self.S
        story = [self._section_banner("PCC CAPTIVE CELL – ANNUAL COST BREAKDOWN"),
                 Spacer(1, 0.3 * cm)]

        story.append(self._p(
            "The table below disaggregates each cost component of the PCC Captive Cell "
            "over the 5-year projection horizon. All amounts in NOK millions. "
            "Amounts in parentheses are income items (deducted from net cost). "
            "RI Premium = annual-aggregate XL reinsurance cost (burning-cost × loading factor). "
            "Capital Opp Cost = tied cell capital × cost-of-capital rate "
            f"({_pct(SETTINGS.cost_of_capital_rate)}).",
        ))
        story.append(Spacer(1, 0.25 * cm))

        headers = [
            "Year",
            "Net Premium\n(to cell)",
            "Fronting\nFee",
            "RI\nPremium",
            "Admin\nFee",
            "Capital\nOpp Cost",
            "Inv\nIncome",
            "Setup\nCost",
            "Net\nCost",
        ]
        rows = [headers]
        ri_highlight_rows = []  # row indices where RI is a dominant cost

        for i, bd in enumerate(pcc_result.annual_breakdown):
            setup_str = _m(bd.setup_or_exit_cost) if bd.setup_or_exit_cost > 0 else "—"
            inv_str = f"({_m(bd.investment_income)})"
            row_data = [
                str(bd.year),
                _m(bd.premium_paid),
                _m(bd.fronting_fee_paid),
                _m(bd.reinsurance_cost),
                _m(bd.admin_costs),
                _m(bd.capital_opportunity_cost),
                inv_str,
                setup_str,
                _m(bd.net_cost),
            ]
            rows.append(row_data)
            # Flag RI as dominant when it exceeds 30% of net premium
            if bd.premium_paid > 0 and bd.reinsurance_cost / bd.premium_paid > 0.30:
                ri_highlight_rows.append(i + 1)  # +1 for header row

        col_ws = [0.8*cm, 2.1*cm, 1.6*cm, 2.0*cm, 1.5*cm, 2.1*cm, 2.0*cm, 1.5*cm, 2.4*cm]
        bt = Table(rows, colWidths=col_ws)
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGREY]),
            ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            # Net Cost column bold
            ("FONTNAME", (8, 1), (8, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (8, 1), (8, -1), NAVY),
        ]
        # Highlight RI Premium column header
        style_cmds.append(("BACKGROUND", (3, 0), (3, 0), GOLD))
        style_cmds.append(("TEXTCOLOR", (3, 0), (3, 0), BLACK))
        # Amber highlight on RI cells where it dominates cost
        AMBER = colors.HexColor("#FFF8E1")
        for row_idx in ri_highlight_rows:
            style_cmds.append(("BACKGROUND", (3, row_idx), (3, row_idx), AMBER))
            style_cmds.append(("FONTNAME", (3, row_idx), (3, row_idx), "Helvetica-Bold"))

        bt.setStyle(TableStyle(style_cmds))
        story.append(bt)
        story.append(Spacer(1, 0.25 * cm))

        # ── Cost composition note ──────────────────────────────────────────────
        bd1 = pcc_result.annual_breakdown[0]
        total_yr1 = bd1.net_cost
        ri_pct_yr1 = bd1.reinsurance_cost / max(total_yr1, 1) * 100
        story.append(self._p(
            f"Year 1 net cost composition: RI Premium represents "
            f"{ri_pct_yr1:.0f}% of total. "
            f"Net premium to cell = {_m(bd1.premium_paid)} "
            f"({_pct(1 - SETTINGS.pcc_premium_discount)} of gross premium). "
            f"Investment income on reserves offsets part of the capital cost.",
            "body_small",
        ))
        return story

    def _build_scr_analysis(self) -> list:
        S = self.S
        story = [self._section_banner("SOLVENCY CAPITAL REQUIREMENT (SCR) ANALYSIS"),
                 Spacer(1, 0.3 * cm)]

        story.append(self._p(
            "The SCR is calculated using a simplified Solvency II framework: "
            "SCR = max(0, VaR₉₉.₅% − Technical Provisions), where Technical Provisions "
            "= Best Estimate Liability × (1 + prudence load) + Risk Margin. "
            "A solvency ratio ≥ 100% (provided capital ≥ SCR) is required for cell viability."
        ))
        story.append(Spacer(1, 0.3 * cm))

        headers = ["Strategi", "BEL (M NOK)", "Tekniske avsetninger (M NOK)", "Risikomargin (M NOK)",
                   "SCR brutto (M NOK)", "SCR netto (M NOK)", "Stilt kapital (M NOK)", "Solvensgrad", "Status"]
        rows = [headers]
        for name, scr in self.scr.items():
            sol_ratio = scr.solvency_ratio
            sol_str = f"{sol_ratio:.1%}" if scr.scr_net > 0 else "N/A"
            rows.append([
                name,
                _m(scr.best_estimate_liability),
                _m(scr.technical_provisions),
                _m(scr.risk_margin),
                _m(scr.scr_gross),
                _m(scr.scr_net),
                _m(scr.required_capital),
                sol_str,
                "✓" if sol_ratio >= 1.0 else "⚠",
            ])

        col_ws = [3.2*cm, 1.9*cm, 2.2*cm, 1.9*cm, 1.9*cm, 1.9*cm, 2.2*cm, 1.5*cm, 0.9*cm]
        st = Table(rows, colWidths=col_ws)
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGREY]),
            ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(st)
        story.append(Spacer(1, 0.3 * cm))

        # Interpretations
        for name, scr in self.scr.items():
            story.append(self._p(f"<b>{name}:</b> {scr.interpretation}", "body_small"))

        story.append(Spacer(1, 0.3 * cm))
        story.append(self._chart_image("scr_comparison", width=15 * cm))
        story.append(self._p(
            "Figure 2 – SCR required vs. capital provided per strategy. "
            "Solid bars = SCR requirement; hatched bars = operator capital commitment.",
            "caption",
        ))

        return story

    def _build_cost_charts(self) -> list:
        story = [self._section_banner("5-YEAR COST ANALYSIS"), Spacer(1, 0.3 * cm)]
        story.append(self._chart_image("cumulative_costs", width=16 * cm))
        story.append(self._p(
            "Figure 3 – Cumulative expected total cost of risk over the 5-year projection "
            "horizon. The PCC Captive Cell curve (gold) reflects higher Year 1 costs "
            "due to formation expenses, with increasing savings thereafter.",
            "caption",
        ))
        story.append(Spacer(1, 0.3 * cm))
        story.append(self._chart_image("annual_comparison", width=16 * cm))
        story.append(self._p(
            "Figure 4 – Expected annual net cost by strategy and year. Premium escalation "
            f"({_pct(self.op.current_insurance.market_rating_trend)}/yr) drives Full Insurance "
            "costs upward while the captive cell premium is partially decoupled from market cycles.",
            "caption",
        ))
        return story

    def _build_risk_frontier(self) -> list:
        story = [self._section_banner("COST–RISK FRONTIER & DISTRIBUTION ANALYSIS"),
                 Spacer(1, 0.3 * cm)]
        story.append(self._chart_image("risk_return_frontier", width=13 * cm))
        story.append(self._p(
            "Figure 5 – Cost–Risk frontier. The ideal quadrant is lower-left (low cost, "
            "low volatility). Full Insurance anchors the low-risk/high-cost position; "
            "Self-Insurance sits high-risk/low-expected-cost.",
            "caption",
        ))
        story.append(Spacer(1, 0.3 * cm))
        story.append(self._chart_image("cost_box_whisker", width=16 * cm))
        story.append(self._p(
            "Figure 6 – Box-and-whisker plot of annualised 5-year cost distribution across "
            f"{self.sim.n_simulations:,} simulations. Whiskers extend to the 5th/95th percentile; "
            "outliers shown as dots.",
            "caption",
        ))
        return story

    def _build_suitability_detail(self) -> list:
        S = self.S
        story = [self._section_banner("SUITABILITY ASSESSMENT – CRITERION DETAIL"),
                 Spacer(1, 0.3 * cm)]

        for c in self.rec.criterion_scores:
            score_pct = c.raw_score / 100
            if score_pct >= 0.65:
                badge_col = colors.HexColor("#2E7D32")
            elif score_pct >= 0.40:
                badge_col = colors.HexColor("#E65100")
            else:
                badge_col = colors.HexColor("#B71C1C")

            # Criterion header row
            header_data = [[
                Paragraph(f"<b>{c.name}</b>", S["body"]),
                Paragraph(f"Weight: {c.weight:.0%}", S["body_small"]),
                Paragraph(f"Score: {c.raw_score:.0f}/100  |  Weighted: {c.weighted_score:.1f}",
                          ParagraphStyle("badge", fontSize=8.5, textColor=WHITE,
                                         fontName="Helvetica-Bold", alignment=TA_RIGHT)),
            ]]
            hw = [(PAGE_W - 2 * MARGIN) * p for p in (0.45, 0.20, 0.35)]
            ht = Table(header_data, colWidths=hw)
            ht.setStyle(TableStyle([
                ("BACKGROUND", (2, 0), (2, 0), badge_col),
                ("BACKGROUND", (0, 0), (1, 0), LGREY),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(KeepTogether([
                ht,
                Paragraph(f"<i>Finding: {c.finding}</i>", S["body_small"]),
                Paragraph(c.rationale, S["body"]),
                self._hr(),
            ]))
            story.append(Spacer(1, 0.15 * cm))

        return story

    def _build_recommendation(self) -> list:
        S = self.S
        story = [self._section_banner("RECOMMENDATION & NEXT STEPS"), Spacer(1, 0.3 * cm)]

        # Radar chart
        story.append(self._chart_image("suitability_radar", width=11 * cm))
        story.append(self._p(
            "Figure 7 – PCC Suitability Radar. Scores closer to the outer edge indicate "
            "stronger captive suitability. The gold dashed ring marks the 60/100 target.",
            "caption",
        ))
        story.append(Spacer(1, 0.3 * cm))

        # ── Correlated risk context for recommendation (Sprint 7) ─────────────
        corr_active = (self.corr_summary is not None
                       and self.corr_summary.domain_correlation_applied)

        story.append(self._p("Risk Profile: Isolated Events or Correlated Stress?", "sub_head"))
        if corr_active and self.corr_summary.tail_analysis is not None:
            tail = self.corr_summary.tail_analysis
            struct_frac = tail.mean_domain_fractions.get("structural", 0)
            env_frac    = tail.mean_domain_fractions.get("environmental", 0)
            bio_frac    = tail.mean_domain_fractions.get("biological", 0)
            multi_domain_share = struct_frac + env_frac
            if multi_domain_share > 0.35:
                risk_profile = (
                    f"This operator's tail loss profile is characterised by <b>correlated "
                    f"multi-domain stress</b>. In the worst 5% of simulated years, structural "
                    f"and environmental losses combined account for {multi_domain_share:.0%} "
                    f"of total losses — materially above their long-run average. "
                    f"This means diversification assumptions based on biological risk alone "
                    f"will understate peak-year capital requirements and reinsurance needs."
                )
            else:
                risk_profile = (
                    f"This operator's tail loss profile is primarily <b>biological-driven</b>. "
                    f"Biological losses account for {bio_frac:.0%} of worst-5% years, "
                    f"with limited structural and environmental amplification. "
                    f"A PCC cell can manage this profile with standard biological "
                    f"reinsurance attachment design."
                )
            story.append(self._p(risk_profile))
        else:
            story.append(self._p(
                "Domain-level tail analysis was not available in this run. "
                "Enable domain correlation (DomainCorrelationMatrix.expert_default()) "
                "to obtain a detailed correlated risk profile for this section."
            ))

        story.append(Spacer(1, 0.2 * cm))

        # ── PCC Structure Implications ────────────────────────────────────────
        story.append(self._p("Implications for PCC Structure", "sub_head"))
        verdict = self.rec.verdict
        score = self.rec.composite_score

        if "STRONGLY" in verdict or "RECOMMENDED" in verdict and "NOT" not in verdict:
            pcc_readiness = "ready-now"
        elif "POTENTIALLY" in verdict:
            pcc_readiness = "conditional"
        else:
            pcc_readiness = "not-ready"

        pcc_bullets = []
        if pcc_readiness == "ready-now":
            pcc_bullets += [
                "The operator's financial profile and risk parameters support direct entry "
                "into a PCC protected cell structure.",
                "A standalone PCC cell is appropriate given the suitability score. Pooled "
                "entry may accelerate diversification but is not required.",
            ]
        elif pcc_readiness == "conditional":
            pcc_bullets += [
                "Direct PCC entry carries conditional risk. A phased hybrid structure "
                "(large-deductible programme with a managed cell reserve) is recommended "
                "as a transition pathway.",
                "Pooled cell entry (sharing a PCC with other aquaculture operators) can "
                "reduce capital requirements and improve solvency ratios during the build-up phase.",
            ]
        else:
            pcc_bullets += [
                "The operator is not yet PCC-ready. Market insurance with enhanced "
                "deductibles and a structured reserve account provides the most practical "
                "near-term risk financing strategy.",
                "A 3-year preparatory programme (governance, risk management, loss data "
                "collection) is recommended before revisiting captive feasibility.",
            ]

        if corr_active:
            pcc_bullets.append(
                "Correlated domain losses reduce the diversification benefit of a standalone "
                "cell. Reinsurance should be structured to attach at the 1-in-20 year level "
                "to protect the cell from multi-domain stress events."
            )
            pcc_bullets.append(
                "Storm and temperature-stress years produce concurrent structural and "
                "environmental claims. Reinsurance treaties should avoid excluding "
                "environmental losses as they are structurally correlated with property losses."
            )

        story.extend(self._bullet_list(pcc_bullets))
        story.append(Spacer(1, 0.2 * cm))

        # ── Mitigation Implications ───────────────────────────────────────────
        story.append(self._p("Implications for Risk Mitigation", "sub_head"))
        story.append(self._p(
            "Cross-domain correlation makes prevention more valuable than in a "
            "single-domain model. Actions that reduce structural or environmental "
            "stress have cascading benefits across correlated domains:"
        ))
        mitigation_bullets = [
            "Stronger moorings and net integrity programmes reduce structural losses "
            "and, through reduced structural stress, lower operational incident rates.",
            "Environmental monitoring (oxygen, temperature, current sensors) enables "
            "early biological mortality response, reducing both biological and "
            "operational escalation costs.",
            "Storm contingency planning reduces both environmental and structural losses "
            "in high-wind events — the highest-correlation pair in the domain matrix.",
            "Staff training programmes reduce human-error incidents in high-stress "
            "periods, when structural and operational risks cluster together.",
        ]
        if not corr_active:
            mitigation_bullets.append(
                "Activate the correlated domain model to quantify mitigation impact "
                "across multiple domains in a single scenario."
            )
        story.extend(self._bullet_list(mitigation_bullets))
        story.append(Spacer(1, 0.2 * cm))

        # ── Next Steps ────────────────────────────────────────────────────────
        story.append(self._p("Next Steps", "sub_head"))
        story.extend(self._bullet_list(self.rec.next_steps))

        return story

    def _build_assumptions(self) -> list:
        S = self.S
        story = [self._section_banner("ASSUMPTIONS, METHODOLOGY & DISCLAIMER"),
                 Spacer(1, 0.3 * cm)]

        story.append(self._p("Methodology Overview", "sub_head"))
        story.append(self._p(
            "This report was generated by the PCC Feasibility & Suitability Tool, "
            "a Python-based actuarial modelling platform. Loss distributions are modelled "
            "using a Compound Poisson–LogNormal process calibrated to the operator's "
            f"stated risk parameters. {self.sim.n_simulations:,} Monte Carlo simulations "
            f"are run for each of the {self.sim.projection_years} projection years. "
            "Capital requirements are derived using a simplified Solvency II framework "
            "(99.5% VaR, 1-year horizon). NPV calculations use a risk-free discount rate "
            f"of {_pct(SETTINGS.risk_free_rate)} p.a."
        ))
        story.append(Spacer(1, 0.2 * cm))

        # Strategy assumptions tables
        for name, result in self.strategies.items():
            story.append(self._p(f"Strategy Assumptions – {name}", "sub_head"))
            rows = [[k, v] for k, v in result.assumptions.items()]
            at = Table(rows, colWidths=[9 * cm, 8.5 * cm])
            at.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LGREY]),
                ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(at)
            story.append(Spacer(1, 0.25 * cm))

        story.append(self._p("Disclaimer", "sub_head"))
        story.append(self._p(
            "This report is prepared for the exclusive use of the named operator and their "
            "board of directors. It is based on information provided by the operator and "
            "publicly available market data. The analysis is indicative and for feasibility "
            "purposes only; it does not constitute insurance, legal, tax, or regulatory advice. "
            "All financial projections involve inherent uncertainty. Actual outcomes may differ "
            "materially from those modelled. Independent actuarial review and legal counsel are "
            "recommended before any captive formation decision. "
            f"Prepared by {SETTINGS.report_author} on {self.report_date}.",
            "disclaimer",
        ))

        return story

    # ── Page: Correlated Cross-Domain Risk (Sprint 7, optional) ──────────────

    def _build_correlated_risk(self) -> list:
        """
        New section 5: Correlated Cross-Domain Risk.

        Renders gracefully whether or not domain_loss_breakdown is available.
        """
        S = self.S
        story = [
            self._section_banner("CORRELATED CROSS-DOMAIN RISK"),
            Spacer(1, 0.3 * cm),
        ]

        # ── Introductory narrative ────────────────────────────────────────────
        story.append(self._p("Why Domain Losses Co-Vary", "sub_head"))
        story.append(self._p(
            "Aquaculture losses do not occur in isolation. A severe storm damages "
            "physical structures, degrades water quality, and elevates operational "
            "stress simultaneously. A warm, low-oxygen summer increases biological "
            "mortality risk while also straining feed systems and procedures. "
            "Treating biological, structural, environmental, and operational losses "
            "as independent understates the frequency and severity of multi-domain "
            "events — the exact events that stress a captive cell most."
        ))
        story.append(Spacer(1, 0.15 * cm))
        story.append(self._p(
            "Earlier versions of this model allocated losses using fixed domain "
            "fractions (biological 60%, structural 20%, environmental 10%, "
            "operational 10%). This report activates the Sprint 7 correlated "
            "domain model, which allows domain weight fractions to shift across "
            "simulation years using a multivariate Gaussian perturbation "
            "calibrated to expert-elicited pairwise correlations."
        ))
        story.append(Spacer(1, 0.25 * cm))

        corr_active = (self.corr_summary is not None
                       and self.corr_summary.domain_correlation_applied)

        # ── Correlation Matrix exhibit ────────────────────────────────────────
        story.append(self._p("Domain Correlation Matrix", "sub_head"))

        if self.domain_correlation is not None:
            mat = self.domain_correlation.correlation_matrix
            domains = self.domain_correlation.domains
            d_labels = [DOMAIN_LABELS.get(d, d) for d in domains]

            # Build a readable table: header row + data rows
            header = [""] + d_labels
            rows = [header]
            for i, di in enumerate(domains):
                row = [d_labels[i]]
                for j, dj in enumerate(domains):
                    rho = mat[i, j]
                    if i == j:
                        row.append("1.00")
                    else:
                        qual = fmt_corr_label(rho)
                        row.append(f"{rho:.2f}  ({qual})")
                rows.append(row)

            D = len(domains)
            col_w0 = 3.0 * cm
            col_rest = (PAGE_W - 2 * MARGIN - col_w0) / D
            ct = Table(rows, colWidths=[col_w0] + [col_rest] * D)
            ct.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (0, -1), NAVY),
                ("TEXTCOLOR", (0, 0), (0, -1), WHITE),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ROWBACKGROUNDS", (1, 1), (-1, -1), [WHITE, LGREY]),
                ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(ct)
            story.append(Spacer(1, 0.2 * cm))

            # Heatmap chart
            heatmap = self._chart_image_safe("domain_corr_heatmap", width=10 * cm)
            if heatmap:
                story.append(heatmap)
                story.append(self._p(
                    "Figure A – Domain risk correlation matrix. "
                    "Environmental ↔ Structural (0.60) is the strongest pair: "
                    "storm years damage physical infrastructure and degrade water quality "
                    "simultaneously. Environmental ↔ Biological (0.40) captures the warm-year "
                    "amplification of HAB and lice risk.",
                    "caption",
                ))

            # Key pair explanations
            story.append(Spacer(1, 0.2 * cm))
            story.append(self._p("Key Correlation Pairs", "sub_head"))
            pair_explanations = [
                "Environmental ↔ Structural (ρ = 0.60 – High): Storm events simultaneously "
                "increase wave and current damage to cages and moorings while reducing oxygen "
                "levels and increasing thermal stress.",
                "Environmental ↔ Biological (ρ = 0.40 – Moderate): Warm, low-oxygen summers "
                "directly increase the probability of HAB events and lice infestations, "
                "linking environmental and biological domains.",
                "Structural ↔ Operational (ρ = 0.35 – Moderate): Structural stress elevates "
                "operational incident rates — damaged equipment leads to procedural failures "
                "and elevated human-error risk.",
                "Biological ↔ Structural (ρ = 0.20 – Low): Large biomass events can "
                "stress cage and mooring systems through abnormal loading.",
            ]
            story.extend(self._bullet_list(pair_explanations))
        else:
            story.append(self._p(
                "Domain correlation was not activated in this run. "
                "To enable the correlated loss model, pass a DomainCorrelationMatrix "
                "to the simulation engine. The expert-default matrix is available via "
                "DomainCorrelationMatrix.expert_default().",
                "body_small",
            ))

        story.append(Spacer(1, 0.25 * cm))

        # ── Tail domain analysis ──────────────────────────────────────────────
        if self.corr_summary is not None and self.corr_summary.tail_analysis is not None:
            tail = self.corr_summary.tail_analysis
            story.append(self._p("Tail Year Domain Analysis (Worst 5% of Years)", "sub_head"))
            story.append(self._p(
                f"The {tail.top_pct:.0%} worst simulated years have a mean annual loss of "
                f"{_m(tail.mean_total_loss)}, versus a portfolio mean of "
                f"{_m(self.corr_summary.kpis.get('mean_annual_loss', 0))}. "
                f"In these extreme years the domain composition shifts markedly:"
            ))

            # Tail domain table
            tail_rows = [["Domain", "Avg. Amount", "% of Tail Loss"]]
            for d in ["biological", "structural", "environmental", "operational"]:
                amt = tail.mean_domain_amounts.get(d, 0.0)
                frac = tail.mean_domain_fractions.get(d, 0.0)
                tail_rows.append([
                    DOMAIN_LABELS.get(d, d),
                    _m(amt),
                    f"{frac:.1%}",
                ])

            tw = (PAGE_W - 2 * MARGIN) / 3
            tt = Table(tail_rows, colWidths=[tw, tw, tw])
            tt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGREY]),
                ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(tt)
            story.append(Spacer(1, 0.2 * cm))

            # Tail domain chart
            tail_chart = self._chart_image_safe("tail_domain_composition", width=15 * cm)
            if tail_chart:
                story.append(tail_chart)
                story.append(self._p(
                    "Figure B – Domain composition in average vs. worst 5% of simulated years. "
                    "The shift toward structural and environmental losses in tail years is a "
                    "direct consequence of cross-domain correlation.",
                    "caption",
                ))

            story.append(Spacer(1, 0.2 * cm))
            story.append(self._p("Implications for Captive Design", "sub_head"))
            story.extend(self._bullet_list(self.corr_summary.tail_domain_narratives))

        elif self.corr_summary is not None:
            story.append(self._p(
                "Domain-level tail analysis is not available in this run "
                "(domain_loss_breakdown not computed).",
                "body_small",
            ))

        return story

    # ── Page: Scenario Comparison (Sprint 7, optional) ────────────────────────

    def _build_scenario_comparison(self) -> list:
        """
        New section 6: Scenario Comparison — Normal / Stress / Extreme Year.

        Omitted gracefully if scenario data is unavailable.
        """
        S = self.S
        story = [
            self._section_banner("SCENARIO COMPARISON: NORMAL / STRESS / EXTREME YEAR"),
            Spacer(1, 0.3 * cm),
        ]

        if (self.corr_summary is None
                or not self.corr_summary.scenarios):
            story.append(self._p(
                "Scenario comparison is not available in this run. "
                "Enable domain correlation to activate this section.",
                "body",
            ))
            return story

        scenarios = self.corr_summary.scenarios

        story.append(self._p(
            "Three representative simulation years are selected from the Monte Carlo "
            "output to illustrate how loss composition changes across the severity "
            "spectrum. Each year is the simulation year closest to the stated percentile."
        ))
        story.append(Spacer(1, 0.25 * cm))

        # ── 3-column scenario table ───────────────────────────────────────────
        col_w = (PAGE_W - 2 * MARGIN) / (len(scenarios) + 1)

        header_row = [""] + [s.label for s in scenarios]
        rows = [header_row]

        rows.append(["Percentile"] + [f"~{s.percentile}th" for s in scenarios])
        rows.append(["Total Annual Loss"] + [_m(s.total_loss) for s in scenarios])

        for domain in ["biological", "structural", "environmental", "operational"]:
            label = DOMAIN_LABELS.get(domain, domain) + " Loss"
            rows.append([label] + [
                _m(s.domain_amounts.get(domain, 0)) for s in scenarios
            ])

        rows.append([""] + [""] * len(scenarios))   # spacer

        for domain in ["biological", "structural", "environmental", "operational"]:
            label = DOMAIN_LABELS.get(domain, domain) + " (%)"
            rows.append([label] + [
                f"{s.domain_fractions.get(domain, 0):.0%}" for s in scenarios
            ])

        col_ws = [3.5 * cm] + [col_w] * len(scenarios)
        st = Table(rows, colWidths=col_ws)
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
            # Highlight each column subtly with scenario colours
            ("BACKGROUND", (1, 1), (1, -1), colors.HexColor("#E8F5E9")),  # normal: green tint
            ("BACKGROUND", (2, 1), (2, -1), colors.HexColor("#FFF8E1")),  # stress: amber tint
            ("BACKGROUND", (3, 1), (3, -1), colors.HexColor("#FFEBEE")),  # extreme: red tint
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (0, -1), [WHITE, LGREY]),
            ("GRID", (0, 0), (-1, -1), 0.3, MGREY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(st)
        story.append(Spacer(1, 0.25 * cm))

        # Scenario stacked bar chart
        stack_chart = self._chart_image_safe("scenario_domain_stacks", width=15 * cm)
        if stack_chart:
            story.append(stack_chart)
            story.append(self._p(
                "Figure C – Domain loss composition across representative years. "
                "The shift from biological-dominated normal years to multi-domain "
                "stress events in extreme years illustrates the diversification "
                "reduction effect that drives captive capital requirements.",
                "caption",
            ))

        story.append(Spacer(1, 0.3 * cm))

        # Per-scenario narrative
        story.append(self._p("Scenario Interpretations", "sub_head"))
        for sc in scenarios:
            story.append(self._p(f"<b>{sc.label} (≈{sc.percentile}th percentile)</b>", "score_label"))
            story.append(self._p(sc.narrative, "body"))
            story.append(Spacer(1, 0.1 * cm))

        return story

    # ── Master build ──────────────────────────────────────────────────────────

    def generate(self):
        """Build and save the PDF report."""

        page_decorator = _PageCanvas(self.op.name, self.report_date)

        def on_page(canvas, doc):
            page_decorator.draw_header(canvas, doc)
            page_decorator.draw_footer(canvas, doc)

        def on_first_page(canvas, doc):
            self._cover_page(canvas, doc)

        # Cover frame: slim placeholder so ReportLab can place the cover PageBreak
        cover_frame = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN, id="cover")
        content_frame = Frame(
            MARGIN, MARGIN + 1.2 * cm,
            PAGE_W - 2 * MARGIN,
            PAGE_H - 2 * MARGIN - 2.6 * cm,
            id="body",
        )

        doc = BaseDocTemplate(
            self.output_path,
            pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN + 1.3 * cm, bottomMargin=MARGIN + 1.2 * cm,
            title=f"PCC Feasibility Report - {self.op.name}",
            author=SETTINGS.report_author,
            subject="PCC Captive Suitability Analysis",
            creator="PCC Feasibility Tool",
        )

        cover_template = PageTemplate(
            id="cover", frames=[cover_frame], onPage=on_first_page
        )
        body_template = PageTemplate(
            id="body", frames=[content_frame], onPage=on_page
        )
        doc.addPageTemplates([cover_template, body_template])

        # Assemble story
        story = [
            # Cover page: tiny spacer occupies the cover frame, then switch template
            Spacer(1, 0.1),
            NextPageTemplate("body"),
            PageBreak(),
        ]
        story.extend(self._build_exec_summary());        story.append(PageBreak())
        story.extend(self._build_risk_profile());        story.append(PageBreak())
        story.extend(self._build_simulation_results());  story.append(PageBreak())
        # Sprint 7 – Correlated risk sections (graceful if data unavailable)
        story.extend(self._build_correlated_risk());     story.append(PageBreak())
        story.extend(self._build_scenario_comparison()); story.append(PageBreak())
        story.extend(self._build_strategy_comparison()); story.append(PageBreak())
        story.extend(self._build_pcc_cost_breakdown());  story.append(PageBreak())
        story.extend(self._build_cost_charts());         story.append(PageBreak())
        story.extend(self._build_scr_analysis());        story.append(PageBreak())
        story.extend(self._build_risk_frontier());       story.append(PageBreak())
        story.extend(self._build_suitability_detail());  story.append(PageBreak())
        story.extend(self._build_recommendation());      story.append(PageBreak())
        story.extend(self._build_assumptions())

        doc.build(story)
