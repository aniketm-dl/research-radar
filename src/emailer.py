"""
Email sender for research digest using SMTP.
"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional


class EmailSender:
    """Send research digests via SMTP."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_ssl: bool = True
    ):
        """
        Initialize email sender with SMTP configuration.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_username: SMTP authentication username
            smtp_password: SMTP authentication password
            use_ssl: Whether to use SSL/TLS
        """
        self.smtp_host = smtp_host or os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '465'))
        self.smtp_username = smtp_username or os.getenv('SMTP_USERNAME')
        self.smtp_password = smtp_password or os.getenv('SMTP_PASSWORD')
        self.use_ssl = use_ssl

        if not self.smtp_username or not self.smtp_password:
            raise ValueError("SMTP credentials must be provided or set as environment variables")

    def send_digest(
        self,
        recipients: List[str],
        papers_with_summaries: List[Dict],
        from_email: str,
        from_name: str,
        subject_prefix: str = "[Research Digest]"
    ) -> bool:
        """
        Send the research digest to recipients.

        Args:
            recipients: List of recipient email addresses
            papers_with_summaries: List of paper dicts with 'summary' field added
            from_email: Sender email address
            from_name: Sender display name
            subject_prefix: Prefix for email subject

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create subject with date and time
            subject = f"{subject_prefix} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"

            # Generate HTML and plain text versions
            html_content = self._generate_html_content(papers_with_summaries)
            text_content = self._generate_text_content(papers_with_summaries)

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = ', '.join(recipients)

            # Attach parts
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            self._send_email(msg, recipients)

            print(f"Successfully sent digest to {len(recipients)} recipients")
            return True

        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def _send_email(self, msg: MIMEMultipart, recipients: List[str]):
        """Send email using SMTP."""
        if self.use_ssl:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg, to_addrs=recipients)
        else:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg, to_addrs=recipients)

    def _generate_html_content(self, papers: List[Dict]) -> str:
        """Generate HTML email content."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #e0e0e0;
            background: #0a0a0a;
            padding: 20px;
        }
        .container {
            width: 95%;
            max-width: 1200px;
            margin: 0 auto;
            background: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid #2a2a2a;
        }
        .header {
            background: linear-gradient(135deg, #1e1e1e 0%, #121212 100%);
            padding: 40px 30px;
            border-bottom: 2px solid #d4ff00;
            position: relative;
            overflow: hidden;
        }
        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(212,255,0,0.1) 0%, transparent 70%);
            border-radius: 50%;
        }
        .header h1 {
            font-size: 32px;
            font-weight: 900;
            color: #ffffff;
            margin-bottom: 12px;
            letter-spacing: -0.5px;
            text-transform: uppercase;
        }
        .header .accent {
            color: #d4ff00;
        }
        .subtitle {
            color: #888;
            font-size: 14px;
            line-height: 1.5;
            max-width: 600px;
        }
        .content {
            padding: 30px;
        }
        .paper {
            margin-bottom: 30px;
            padding: 24px;
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 12px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .paper::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            height: 100%;
            width: 4px;
            background: linear-gradient(180deg, #d4ff00 0%, #a0c000 100%);
        }
        .paper-number {
            display: inline-block;
            background: #d4ff00;
            color: #000;
            font-size: 11px;
            font-weight: 900;
            padding: 4px 10px;
            border-radius: 4px;
            margin-bottom: 12px;
            letter-spacing: 0.5px;
        }
        .paper-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 12px;
            line-height: 1.4;
        }
        .paper-title a {
            color: #ffffff;
            text-decoration: none;
            transition: color 0.2s ease;
        }
        .paper-title a:hover {
            color: #d4ff00;
        }
        .metadata {
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 16px;
            padding-bottom: 16px;
            border-bottom: 1px solid #2a2a2a;
        }
        .metadata-item {
            color: #888;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .metadata-item strong {
            color: #d4ff00;
            font-weight: 600;
        }
        .summary {
            color: #b0b0b0;
            line-height: 1.7;
            font-size: 14px;
        }
        .summary p {
            margin-bottom: 12px;
        }
        .practical-application {
            margin-top: 16px;
            padding: 16px;
            background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #d4ff00;
            border-left: 4px solid #d4ff00;
            border-radius: 8px;
        }
        .section-label {
            color: #d4ff00;
            font-size: 10px;
            font-weight: 900;
            letter-spacing: 1px;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .practical-application p {
            color: #b0b0b0;
            line-height: 1.7;
            font-size: 13px;
            margin: 0;
        }
        .footer {
            background: #0f0f0f;
            padding: 30px;
            text-align: center;
            border-top: 1px solid #2a2a2a;
        }
        .footer-stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        .footer-stat {
            font-size: 12px;
            color: #666;
        }
        .footer-stat strong {
            color: #d4ff00;
            font-weight: 700;
            font-size: 18px;
            display: block;
            margin-bottom: 4px;
        }
        .footer-text {
            color: #666;
            font-size: 11px;
            margin-top: 16px;
        }
        .badge {
            display: inline-block;
            background: #2a2a2a;
            color: #d4ff00;
            font-size: 10px;
            padding: 3px 8px;
            border-radius: 3px;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><span class="accent">DARPAN</span> RESEARCH RADAR</h1>
            <p class="subtitle">
                Latest research on digital twins, synthetic users, and LLM agents for consumer research
            </p>
        </div>
        <div class="content">
"""

        for i, paper in enumerate(papers, 1):
            html += self._format_paper_html(paper, i)

        html += f"""
        </div>
        <div class="footer">
            <div class="footer-stats">
                <div class="footer-stat">
                    <strong>{len(papers)}</strong>
                    <span>Papers</span>
                </div>
                <div class="footer-stat">
                    <strong>{datetime.utcnow().strftime('%H:%M')}</strong>
                    <span>UTC</span>
                </div>
                <div class="footer-stat">
                    <strong>{datetime.utcnow().strftime('%d %b')}</strong>
                    <span>{datetime.utcnow().strftime('%Y')}</span>
                </div>
            </div>
            <p class="footer-text">
                Automated research digest from arXiv and Crossref • Powered by Gemini AI
            </p>
        </div>
    </div>
</body>
</html>"""

        return html

    def _format_paper_html(self, paper: Dict, index: int) -> str:
        """Format a single paper for HTML email."""
        authors = paper.get('authors', [])
        if isinstance(authors, list):
            authors_str = ', '.join(authors[:3])
            if len(authors) > 3:
                authors_str += f" et al."
        else:
            authors_str = str(authors)

        summary = paper.get('summary', 'Summary not available.')

        # Parse the summary to extract structured parts if present
        if 'TITLE:' in summary and 'SUMMARY:' in summary:
            # Extract just the summary part
            summary_parts = summary.split('SUMMARY:')
            if len(summary_parts) > 1:
                summary_text = summary_parts[1].strip()
            else:
                summary_text = summary
        else:
            summary_text = summary

        # Convert line breaks to paragraphs
        paragraphs = [p.strip() for p in summary_text.split('\n\n') if p.strip()]
        formatted_summary = ''.join([f'<p>{p}</p>' for p in paragraphs])

        # Format practical application if present
        practical_app = paper.get('practical_application', '')
        practical_app_html = ''
        if practical_app:
            practical_app_html = f'''
            <div class="practical-application">
                <div class="section-label">RELEVANCE TO DARPAN LABS</div>
                <p>{practical_app}</p>
            </div>'''

        return f"""
        <div class="paper">
            <span class="paper-number">PAPER {index:02d}</span>
            <div class="paper-title">
                <a href="{paper.get('url', '#')}" target="_blank">{paper.get('title', 'Title not available')}</a>
            </div>
            <div class="metadata">
                <span class="metadata-item"><strong>Authors:</strong> {authors_str}</span>
                <span class="metadata-item"><strong>Date:</strong> {paper.get('date', 'Date not available')}</span>
                <span class="metadata-item"><strong>Source:</strong> {paper.get('source', 'Unknown').upper()}</span>
            </div>
            <div class="summary">
                {formatted_summary}
            </div>{practical_app_html}
        </div>
"""

    def _generate_text_content(self, papers: List[Dict]) -> str:
        """Generate plain text email content."""
        text = "DARPAN RESEARCH RADAR\n"
        text += "=" * 40 + "\n\n"
        text += f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
        text += f"This digest includes {len(papers)} paper{'s' if len(papers) != 1 else ''}.\n\n"
        text += "-" * 40 + "\n\n"

        for i, paper in enumerate(papers, 1):
            text += self._format_paper_text(paper, i)
            text += "\n" + "-" * 40 + "\n\n"

        return text

    def _format_paper_text(self, paper: Dict, index: int) -> str:
        """Format a single paper for plain text email."""
        authors = paper.get('authors', [])
        if isinstance(authors, list):
            authors_str = ', '.join(authors[:3])
            if len(authors) > 3:
                authors_str += f" et al."
        else:
            authors_str = str(authors)

        summary = paper.get('summary', 'Summary not available.')

        # Parse the summary to extract structured parts if present
        if 'TITLE:' in summary and 'SUMMARY:' in summary:
            # Extract just the summary part
            summary_parts = summary.split('SUMMARY:')
            if len(summary_parts) > 1:
                summary_text = summary_parts[1].strip()
            else:
                summary_text = summary
        else:
            summary_text = summary

        # Include practical application if present
        practical_app = paper.get('practical_application', '')
        practical_app_text = ''
        if practical_app:
            practical_app_text = f"\n\nRelevance to Darpan Labs:\n{practical_app}"

        return f"""[{index}] {paper.get('title', 'Title not available')}

Authors: {authors_str}
Date: {paper.get('date', 'Date not available')}
Source: {paper.get('source', 'Unknown').upper()}
Link: {paper.get('url', 'URL not available')}

Summary:
{summary_text}{practical_app_text}
"""