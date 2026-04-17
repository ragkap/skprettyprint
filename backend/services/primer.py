import os
import io
import base64
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import psycopg2
import yfinance as yf
from bs4 import BeautifulSoup
from weasyprint import HTML, CSS

log = logging.getLogger(__name__)


def _connect():
    return psycopg2.connect(
        database=os.environ["DB_NAME"],
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=os.environ["DB_PORT"],
    )


def search_entities(query: str, limit: int = 10) -> list[dict]:
    q = query.strip()
    if not q:
        return []
    pattern = f"%{q}%"
    conn = _connect()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            select e.pretty_name, e.bloomberg_ticker
            from entities e
            where e.bloomberg_ticker is not null
              and (e.pretty_name ilike %s or e.bloomberg_ticker ilike %s)
            order by
              case when e.bloomberg_ticker ilike %s then 0
                   when e.pretty_name ilike %s then 1
                   else 2 end,
              e.pretty_name
            limit %s
            """,
            (pattern, pattern, f"{q}%", f"{q}%", limit),
        )
        rows = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()
    return [{"name": r[0], "ticker": r[1]} for r in rows]


def fetch_latest_primer(bb_ticker: str) -> dict | None:
    conn = psycopg2.connect(
        database=os.environ["DB_NAME"],
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=os.environ["DB_PORT"],
    )
    try:
        cursor = conn.cursor()
        sql = """
            select
                e.bloomberg_ticker,
                e.pretty_name,
                TO_CHAR(i.published_at, 'DD Mon YYYY') || ' | ' || e.country || ' | ' || ig."name",
                'Smartkarma Primer',
                e.pretty_name || ' (' || e.bloomberg_ticker || ') ' || ' | Smartkarma Primer ' || TO_CHAR(i.published_at, 'YYYYMMDD') || '.pdf',
                '<h2>Executive Summary</h2>' || i.executive_summary || '<h2>Detail</h2>' || i.detail,
                e.yahoo_ticker
            from insights i
            inner join entities e on e.id = i.primary_entity_id
            inner join industry_groups ig on ig.id = e.industry_group_id
            where i.account_id = 76928
              and e.bloomberg_ticker = %s
            order by i.published_at desc
            limit 1
        """
        cursor.execute(sql, (bb_ticker,))
        row = cursor.fetchone()
        cursor.close()
    finally:
        conn.close()

    if not row:
        return None

    return {
        "ticker": row[0],
        "company_name": row[1],
        "date_line": row[2],
        "report_type": row[3],
        "report_name": row[4],
        "insight": row[5],
        "yahoo_ticker": row[6],
    }


def get_stock_chart_base64(ticker_symbol: str) -> str:
    if not ticker_symbol:
        return ""
    try:
        data = yf.download(ticker_symbol, period="5y", interval="1d", progress=False, auto_adjust=False)
        if data.empty:
            log.warning("yfinance returned no data for %s", ticker_symbol)
            return ""
        plt.figure(figsize=(10, 6))
        plt.plot(data.index, data["Close"], color="#24a9a7", linewidth=2)
        plt.axis("off")
        plt.gca().set_position([0, 0, 1, 1])
        buf = io.BytesIO()
        plt.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0)
        plt.close()
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
    except Exception:
        log.exception("Chart generation failed for %s", ticker_symbol)
        return ""


def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for li in soup.find_all("li"):
        if li.find("table"):
            li.unwrap()
    for a in soup.find_all("a"):
        a["target"] = "_blank"
    disclaimer = soup.find("p", string=lambda t: t and "content is AI-generated" in t)
    if disclaimer:
        disclaimer.decompose()
    return str(soup)


def generate_primer_pdf(
    raw_html: str,
    ticker: str,
    company_name: str,
    report_type: str,
    date_line: str,
    yahoo_ticker: str,
) -> bytes:
    inside_title = "At Smartkarma,<br><span class='teal-bold'>We Do Things Differently</span>"
    inside_body = """
    <p>Smartkarma is an AI-augmented investment intelligence platform delivering real-time insight, differentiated alternative data, and direct access to top-ranked analysts through a single, integrated subscription. <span class="teal">We serve global institutional investors, bulge-bracket banks, private accredited investors, and listed and private issuers.</span></p>

    <p>Beyond research, Smartkarma has evolved into a full-stack intelligence and connectivity platform. Through <a class="teal-bold" href="https://www.engageIR.co">engageIR</a> and our broader Corporate Solutions offering, we help corporates sharpen their equity story, deepen investor engagement, and connect with a global network of investors and analysts.</p>

    <p>As part of this evolution, we have launched <a class="teal-bold" href="https://www.pvtiq.com">pvtIQ</a>, our private markets intelligence vertical. pvtIQ delivers structured insight on high-growth companies, covering cap table dynamics, peer benchmarking, and real-time digital signals that are typically inaccessible to investors.</p>

    <p><span class="teal">Our model is built on independence and alignment.</span> Insight Provider content is evaluated on quality, relevance, and market impact, with merit-based monetisation rewarding differentiated, high-conviction research.</p>

    <p>Curation is central. Fewer than 10% of applicants are approved as Insight Providers, ensuring a high signal-to-noise ratio. Today, Smartkarma brings together over 350 independent Insight Providers delivering <span class="teal">actionable intelligence trusted by institutional investors worldwide.</span></p>
    """

    disclaimer_text = (
        "SMARTKARMA RESEARCH: This publication is published by Smartkarma Innovations Pte Ltd "
        "(\u201cSmartkarma\u201d), the operator of the online investment research platform "
        "www.smartkarma.com. The Publication contains content authored by Smartkarma and by selected "
        "third party Insight Providers, which has been republished with their express permission "
        "(collectively, the \u201cContent\u201d). The following disclaimers shall apply to all Content "
        "contained in this Publication. Content is of a general nature only and shall not be construed "
        "as or relied upon in any circumstances as professional, targeted financial or investment advice "
        "or be considered to form part of any offer for sale, subscription, solicitation or invitation to "
        "buy or subscribe for any securities or financial products. Independent advice should be obtained "
        "before reliance is placed upon any Content contained in this Publication. Inclusion of Content "
        "from third party Insight Providers in this Publication shall in no way be construed as an "
        "endorsement or other positive evaluation by Smartkarma of the Insight Providers or the views "
        "expressed in their Content, and Smartkarma disclaims all liability in respect of their Content, "
        "including regarding accuracy and suitability for the recipient\u2019s purposes (if any). Recipients "
        "of this Publication further acknowledge that the Content in the Publication is and remains the "
        "property of, as applicable, Smartkarma and the third party Insight Providers. Use of the "
        "Publication is intended for the registered recipient only, for the purposes of evaluating the "
        "Smartkarma product and generating brand awareness, and any use outside this limited purpose or "
        "any unauthorised redistribution is not permitted."
    )

    chart_src = get_stock_chart_base64(yahoo_ticker)
    chart_html = (
        f'<div class="disclaimer" style="margin-top:40px;">Price History</div>'
        f'<img class="stock-chart" src="{chart_src}">'
        if chart_src else ""
    )

    soup = BeautifulSoup(raw_html, "html.parser")
    for li in soup.find_all("li"):
        if li.find("table"):
            li.unwrap()

    toc_html = []
    headers = soup.find_all(["h2", "h3"])
    for i, header in enumerate(headers):
        header_id = f"section_{i}"
        header["id"] = header_id
        title = header.get_text().strip()
        cls = "toc-h2" if header.name == "h2" else "toc-h3"
        toc_html.append(f'<li class="{cls}"><a href="#{header_id}">{title}</a></li>')
    toc_list_string = "".join(toc_html)

    full_html = f"""
    <html>
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
      </head>
      <body>
        <div id="cover-page">
          <div class="accent-bar"></div>
          <img class="main-logo" src="https://sk-assets.s3.amazonaws.com/online-branding-manual/01-logotypes/smartkarma-primary-logo-smart-teal-1000px.png">
          <div class="cover-content">
            <h1 class="ticker">{ticker}</h1>
            <h2 class="company-name">{company_name}</h2>
            <div class="report-type">{report_type}</div>
            <div class="date-line">{date_line}</div>
            <div class="disclaimer">This content is AI-generated and displayed for general informational purposes only.<br>Please verify independently before use.</div>
            {chart_html}
          </div>
        </div>

        <div id="inside-cover">
          <img class="compass-icon" src="https://sk-assets.s3.amazonaws.com/online-branding-manual/01-logotypes/curation-compass-box-smart-teal-1000px.png">
          <h2 class="inside-head">{inside_title}</h2>
          <div class="inside-body-text">{inside_body}</div>
        </div>

        <div id="toc-page">
          <h2 class="toc-title">Contents</h2>
          <ul class="toc-list">{toc_list_string}</ul>
        </div>

        <div class="content">
          {soup.decode_contents()}
          <div class="disclaimer-text">{disclaimer_text}</div>
        </div>
      </body>
    </html>
    """

    styles = """
    @page {
        size: A4; margin: 1.5cm 5cm 2cm 1.5cm; background-color: #0f0f0f;
        @bottom-right {content: counter(page); font-family: 'Roboto', sans-serif; font-size: 8pt; color: #ddd;}
    }

    body {font-family:'Roboto',sans-serif;font-weight:400;color:#d1d1d1;background-color:#0f0f0f;line-height:1.6;letter-spacing:0!important;}
    ul {list-style-type:square;padding-left:20px;margin-bottom:20px;}
    li {padding-left:15px;margin-bottom:10px;color:#d1d1d1;list-style-type:square;}
    li::marker{color:#24a9a7;font-size:1.2em;list-style-type:square;}
    #cover-page { height: 100vh; page-break-after: always; margin-right: -3.5cm; display: flex; flex-direction: column; justify-content: center; }
    .accent-bar { width: 60px; height: 4px; background: #24a9a7; margin-bottom: 30px; }
    .main-logo { width: 220px; margin-bottom: 60px; }
    .ticker { font-size: 48pt; font-weight: 700; color: #fff; margin: 0; }
    .company-name { font-size: 24pt; font-weight: 300; color: #24a9a7; margin: 0; border: none !important; }
    .report-type { margin-top: 40px; font-size: 10pt; letter-spacing: 3px; color: #888; text-transform: uppercase; }
    .disclaimer { margin-top: 40px; font-size: 8pt; letter-spacing: -0.5px; color: #888; }
    .stock-chart {width: 100%; height: 360px; opacity: 0.8;}

    #inside-cover {page-break-before: always; page-break-after:always; display:block; padding-top:2cm;}
    .compass-icon{width: 100px; border-radius: 50%; position: absolute; right: 0; border: 2px solid #fff;}
    .inside-head { color: #fff; font-weight: 500; font-size: 18pt; margin-top: 1.2cm; border-bottom: 0.5pt solid #333; padding-top: 2cm;}
    .inside-body-text { font-size: 12pt; line-height: 1.5; color: #eee; }
    .teal {color: #24a9a7;}
    .teal-bold {color: #24a9a7; font-weight: 600;}

    #toc-page{page-break-after:always;display:block;padding-top:2cm;}
    .toc-list { list-style: none; padding: 0; }
    .toc-list li{border-bottom:1px dotted #222;display:flex;align-items:baseline;margin-bottom:8px;}
    .toc-list a{ text-decoration: none; color:#24a9a7;flex:1; font-weight:500;}
    .toc-list a::after{content:target-counter(attr(href),page);float:right;color:#24a9a7;font-weight:700;}
    .toc-h3{margin-left:20px;opacity:0.8;}
    .toc-h3 a {font-size: 10pt; font-weight: 500;}

    h2 { color: #fff; font-weight: 500; font-size: 18pt; margin-top: 1.2cm; border-bottom: 0.5pt solid #333; }
    h3 { color: #24a9a7; text-transform: uppercase; font-size: 9pt; letter-spacing: 1.5px; margin-top: 1cm; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; page-break-inside: avoid; font-size: 9pt; background: #161616; }
    th { border-bottom: 2px solid #24a9a7; color: #24a9a7; text-align: left; padding: 8px; font-weight: 500; }
    td { padding: 8px; border-bottom: 1px solid #222; }
    .content-highlight { background: #111; border-left: 5px solid #24a9a7; padding: 20px; margin: 20px 0; page-break-inside: avoid; }
    b, strong { color: #fff; font-weight: 500; }
    a { color: #24a9a7; }
    .disclaimer-text { font-size: 12px; color: #777; text-align: justify; line-height: 1.4; padding-top: 1cm; page-break-inside: avoid;}
    """

    pdf_bytes = HTML(string=full_html).write_pdf(stylesheets=[CSS(string=styles)])
    return pdf_bytes


def build_primer(bb_ticker: str) -> tuple[bytes, str] | None:
    primer = fetch_latest_primer(bb_ticker)
    if not primer:
        return None
    cleaned = clean_html(primer["insight"])
    pdf = generate_primer_pdf(
        cleaned,
        primer["ticker"],
        primer["company_name"],
        primer["report_type"],
        primer["date_line"],
        primer["yahoo_ticker"],
    )
    return pdf, primer["report_name"]
