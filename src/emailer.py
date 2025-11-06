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
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        .paper {
            margin-bottom: 40px;
            padding: 20px;
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            border-radius: 5px;
        }
        .paper-title {
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        .paper-title a {
            color: #3498db;
            text-decoration: none;
        }
        .paper-title a:hover {
            text-decoration: underline;
        }
        .metadata {
            color: #666;
            font-size: 14px;
            margin-bottom: 15px;
        }
        .metadata span {
            margin-right: 15px;
        }
        .summary {
            color: #444;
            line-height: 1.7;
        }
        .summary p {
            margin-bottom: 12px;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Darpan Research Radar</h1>
        <p style="color: #666; margin-bottom: 30px;">
            Latest research on digital twins, synthetic users, and LLM agents for consumer research.
        </p>
"""

        for paper in papers:
            html += self._format_paper_html(paper)

        html += f"""
        <div class="footer">
            <p>Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
            <p>This digest includes {len(papers)} paper{'s' if len(papers) != 1 else ''} from arXiv and Crossref.</p>
        </div>
    </div>
</body>
</html>"""

        return html

    def _format_paper_html(self, paper: Dict) -> str:
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

        return f"""
        <div class="paper">
            <div class="paper-title">
                <a href="{paper.get('url', '#')}" target="_blank">{paper.get('title', 'Title not available')}</a>
            </div>
            <div class="metadata">
                <span><strong>Authors:</strong> {authors_str}</span><br>
                <span><strong>Date:</strong> {paper.get('date', 'Date not available')}</span><br>
                <span><strong>Source:</strong> {paper.get('source', 'Unknown').upper()}</span>
            </div>
            <div class="summary">
                {formatted_summary}
            </div>
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

        return f"""[{index}] {paper.get('title', 'Title not available')}

Authors: {authors_str}
Date: {paper.get('date', 'Date not available')}
Source: {paper.get('source', 'Unknown').upper()}
Link: {paper.get('url', 'URL not available')}

Summary:
{summary_text}
"""