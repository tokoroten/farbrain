"""PDF generation service using ReportLab."""

import logging
from io import BytesIO
import re
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generate PDF reports from Markdown content."""

    def __init__(self):
        """Initialize PDF generator."""
        # Register Japanese CID font
        try:
            # Use built-in CID fonts for Japanese (always available in ReportLab)
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
            self.japanese_font = 'HeiseiKakuGo-W5'  # Gothic font for better readability
            logger.info(f"[PDF] Registered Japanese CID font: {self.japanese_font}")
        except Exception as e:
            logger.warning(f"[PDF] Could not load Japanese CID font: {e}")
            self.japanese_font = 'Helvetica'  # Fallback

    def markdown_to_pdf(self, markdown_content: str) -> bytes:
        """
        Convert Markdown content to PDF.

        Args:
            markdown_content: Markdown-formatted report content

        Returns:
            PDF file as bytes
        """
        try:
            # Create PDF in memory
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm,
            )

            # Create story (content flow)
            story = []

            # Get styles
            styles = getSampleStyleSheet()

            # Custom styles for Japanese text
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=self.japanese_font,
                fontSize=24,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=20,
                alignment=TA_CENTER,
            )

            heading2_style = ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontName=self.japanese_font,
                fontSize=18,
                textColor=colors.HexColor('#2980b9'),
                spaceBefore=20,
                spaceAfter=12,
                borderWidth=0,
                borderColor=colors.HexColor('#3498db'),
                borderPadding=5,
                leftIndent=5,
            )

            heading3_style = ParagraphStyle(
                'CustomHeading3',
                parent=styles['Heading3'],
                fontName=self.japanese_font,
                fontSize=14,
                textColor=colors.HexColor('#34495e'),
                spaceBefore=15,
                spaceAfter=10,
            )

            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontName=self.japanese_font,
                fontSize=11,
                leading=20,
            )

            # Parse markdown line by line
            lines = markdown_content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()

                if not line:
                    i += 1
                    continue

                # Title (# )
                if line.startswith('# '):
                    text = self._escape_html(line[2:])
                    story.append(Paragraph(text, title_style))
                    story.append(Spacer(1, 12))

                # Heading 2 (## )
                elif line.startswith('## '):
                    text = self._escape_html(line[3:])
                    story.append(Spacer(1, 12))
                    story.append(Paragraph(text, heading2_style))
                    story.append(Spacer(1, 8))

                # Heading 3 (### )
                elif line.startswith('### '):
                    text = self._escape_html(line[4:])
                    story.append(Paragraph(text, heading3_style))
                    story.append(Spacer(1, 6))

                # Horizontal rule
                elif line.startswith('━') or line.startswith('---'):
                    from reportlab.platypus import HRFlowable
                    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
                    story.append(Spacer(1, 6))

                # Table
                elif line.startswith('|'):
                    table_lines = []
                    while i < len(lines) and lines[i].strip().startswith('|'):
                        table_lines.append(lines[i].strip())
                        i += 1
                    i -= 1  # Back up one since we'll increment at the end

                    # Parse table
                    table_data = []
                    for table_line in table_lines:
                        # Skip separator lines
                        if re.match(r'\|[\s\-:|]+\|', table_line):
                            continue
                        cells = [cell.strip() for cell in table_line.split('|')[1:-1]]
                        table_data.append(cells)

                    if table_data:
                        # Create table
                        t = Table(table_data)
                        t.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, -1), self.japanese_font),
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                        ]))
                        story.append(t)
                        story.append(Spacer(1, 12))

                # Blockquote (> )
                elif line.startswith('> '):
                    text = self._escape_html(line[2:])
                    blockquote_style = ParagraphStyle(
                        'Blockquote',
                        parent=body_style,
                        fontName=self.japanese_font,
                        leftIndent=20,
                        rightIndent=20,
                        textColor=colors.HexColor('#555'),
                        backColor=colors.HexColor('#f7f7f7'),
                        borderWidth=1,
                        borderColor=colors.HexColor('#3498db'),
                        borderPadding=10,
                    )
                    story.append(Paragraph(text, blockquote_style))
                    story.append(Spacer(1, 6))

                # Bold text (**text**)
                elif '**' in line:
                    text = self._escape_html(line)
                    # Convert markdown bold to HTML bold
                    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                    story.append(Paragraph(text, body_style))
                    story.append(Spacer(1, 4))

                # List item
                elif re.match(r'^\d+\. ', line):
                    text = self._escape_html(line)
                    story.append(Paragraph(text, body_style))
                    story.append(Spacer(1, 2))

                # Regular paragraph
                else:
                    text = self._escape_html(line)
                    if text:
                        story.append(Paragraph(text, body_style))
                        story.append(Spacer(1, 4))

                i += 1

            # Build PDF
            logger.info("[PDF] Building PDF document")
            doc.build(story)

            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()

            logger.info(f"[PDF] PDF generated successfully ({len(pdf_bytes)} bytes)")
            return pdf_bytes

        except Exception as e:
            logger.error(f"[PDF] Failed to generate PDF: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters and remove emojis."""
        # Remove emojis and special characters that reportlab can't handle
        text = text.replace('📊', '[Chart]')
        text = text.replace('🔍', '[Search]')
        text = text.replace('🏆', '[Trophy]')
        text = text.replace('🎨', '[Art]')
        text = text.replace('💎', '[Diamond]')
        text = text.replace('📋', '[Clipboard]')
        text = text.replace('⭐', '[Star]')
        text = text.replace('📄', '')
        text = text.replace('📑', '')
        text = text.replace('📥', '')

        # Escape HTML special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')

        return text
