import re
import ssl
import socket
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from urllib.parse import urlparse


def fetch_page(url):
    try:
        headers = {'User-Agent': 'TrustPulse-Scanner/1.0'}
        resp = requests.get(url, timeout=10, headers=headers)
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        return html, soup
    except Exception:
        return None, None


def check_ssl(url):
    try:
        hostname = urlparse(url).hostname
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
            s.settimeout(5)
            s.connect((hostname, 443))
        return {'id':'ssl','title':'SSL certificate','status':'pass','detail':'Valid SSL certificate found.','points':15}
    except Exception:
        return {'id':'ssl','title':'SSL certificate','status':'fail','detail':'No valid SSL certificate found.','points':0}


def check_privacy_policy(soup):
    if soup is None:
        return {'id':'privacy','title':'Privacy policy','status':'warn','detail':'Could not scan page.','points':5}
    text = soup.get_text().lower()
    links = [a.get_text().lower() for a in soup.find_all('a')]
    all_text = text + ' '.join(links)
    if 'privacy policy' in all_text or 'privacy notice' in all_text:
        return {'id':'privacy','title':'Privacy policy','status':'pass','detail':'Privacy policy link found.','points':10}
    return {'id':'privacy','title':'Privacy policy','status':'fail','detail':'No privacy policy found. Required under UK GDPR.','points':0}


def check_dark_patterns(soup, html):
    if soup is None or html is None:
        return {'id':'dark_patterns','title':'Dark patterns','status':'warn','detail':'Could not scan page.','points':5}
    issues_found = []
    text = soup.get_text().lower()
    urgency_phrases = ['only \d+ left','limited time','expires in','hurry','selling fast','last chance','today only','offer ends']
    for phrase in urgency_phrases:
        if re.search(phrase, text):
            issues_found.append(f'Urgency phrase: "{phrase}"')
    if re.search(r'countdown|timer|setinterval.*\d{2}:\d{2}', html.lower()):
        issues_found.append('Countdown timer detected')
    negative_framing = ["no, i don't want", "no thanks", "no, i hate"]
    for phrase in negative_framing:
        if phrase in text:
            issues_found.append(f'Negative framing: "{phrase}"')
    if issues_found:
        return {'id':'dark_patterns','title':'Dark patterns','status':'fail','detail':f'{len(issues_found)} dark pattern(s) found: '+'; '.join(issues_found[:2]),'points':0,'issues':issues_found}
    return {'id':'dark_patterns','title':'Dark patterns','status':'pass','detail':'No dark patterns detected.','points':15}


def check_cookie_consent(soup, html):
    if soup is None:
        return {'id':'cookies','title':'Cookie consent','status':'warn','detail':'Could not scan page.','points':5}
    preticked = soup.find_all('input', {'type':'checkbox','checked':True})
    cookie_text = 'cookie' in soup.get_text().lower()
    if preticked:
        return {'id':'cookies','title':'Cookie consent','status':'fail','detail':f'{len(preticked)} pre-ticked checkbox(es) found. Violates GDPR.','points':0}
    if cookie_text:
        return {'id':'cookies','title':'Cookie consent','status':'pass','detail':'Cookie consent notice found.','points':10}
    return {'id':'cookies','title':'Cookie consent','status':'warn','detail':'No cookie consent notice detected.','points':5}


def check_contact_info(soup):
    if soup is None:
        return {'id':'contact','title':'Contact information','status':'warn','detail':'Could not scan page.','points':5}
    text = soup.get_text().lower()
    has_email = bool(re.search(r'[\w.-]+@[\w.-]+\.\w+', text))
    has_phone = bool(re.search(r'(\+44|0\d{3,4})[\s\-]?\d{3,4}[\s\-]?\d{3,4}', text))
    has_address = 'address' in text or 'street' in text or 'postcode' in text
    score = sum([has_email, has_phone, has_address])
    if score >= 2:
        return {'id':'contact','title':'Contact information','status':'pass','detail':'Good contact information found.','points':10}
    elif score == 1:
        return {'id':'contact','title':'Contact information','status':'warn','detail':'Only one contact method found.','points':5}
    return {'id':'contact','title':'Contact information','status':'fail','detail':'No contact information found.','points':0}


def check_sentiment(soup):
    if soup is None:
        return {'id':'sentiment','title':'Page tone','status':'warn','detail':'Could not scan page.','points':5}
    text = soup.get_text()[:3000]
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity >= 0.1:
        return {'id':'sentiment','title':'Page tone','status':'pass','detail':f'Positive tone detected (score: {polarity:.2f}).','points':10}
    elif polarity >= -0.1:
        return {'id':'sentiment','title':'Page tone','status':'warn','detail':'Neutral tone. Consider more positive language.','points':5}
    return {'id':'sentiment','title':'Page tone','status':'fail','detail':f'Negative tone detected (score: {polarity:.2f}).','points':0}


def check_returns_policy(soup):
    if soup is None:
        return {'id':'returns','title':'Returns policy','status':'warn','detail':'Could not scan page.','points':5}
    text = soup.get_text().lower()
    if any(p in text for p in ['return policy','returns policy','refund policy','money back','30-day','14 day return']):
        return {'id':'returns','title':'Returns policy','status':'pass','detail':'Returns policy found.','points':10}
    return {'id':'returns','title':'Returns policy','status':'fail','detail':'No returns policy found. Required by UK law.','points':0}


def run_full_scan(url):
    if not url.startswith('http'):
        url = 'https://' + url
    html, soup = fetch_page(url)
    checks = [
        check_ssl(url),
        check_privacy_policy(soup),
        check_dark_patterns(soup, html),
        check_cookie_consent(soup, html),
        check_contact_info(soup),
        check_sentiment(soup),
        check_returns_policy(soup),
    ]
    max_points = 80
    earned = sum(c['points'] for c in checks)
    score = round((earned / max_points) * 100)
    score = max(0, min(100, score))
    if score >= 80:
        grade = 'High Trust'
        grade_desc = 'Strong trust signals. Keep maintaining these standards.'
    elif score >= 55:
        grade = 'Moderate Trust'
        grade_desc = 'Decent foundation but several trust issues need attention.'
    else:
        grade = 'Low Trust'
        grade_desc = 'Significant trust issues found. Fixing these will improve conversions.'
    issues = []
    for check in checks:
        if check['status'] == 'fail':
            issues.append({'severity':'high' if check['points'] >= 10 else 'medium','title':check['title']+' — action required','detail':check['detail']})
        elif check['status'] == 'warn':
            issues.append({'severity':'low','title':check['title']+' — improvement suggested','detail':check['detail']})
    return {
        'url':url,'score':score,'grade':grade,'grade_desc':grade_desc,
        'checks':checks,'issues':issues,
        'passed_count':len([c for c in checks if c['status']=='pass']),
        'issues_count':len([c for c in checks if c['status']=='fail']),
        'warnings_count':len([c for c in checks if c['status']=='warn']),
    }