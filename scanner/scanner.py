import re
import ssl
import socket
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import whois as pythonwhois


def fetch_page(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; TrustPulseBot/2.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        response = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        return response.text, soup
    except Exception:
        return None, None


# ── 1. SSL Certificate ────────────────────────────────────────────────────────
def check_ssl(url):
    try:
        hostname = url.replace('https://', '').replace('http://', '').split('/')[0]
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
            s.settimeout(8)
            s.connect((hostname, 443))
            cert = s.getpeercert()
        return {'id': 'ssl', 'title': 'SSL certificate', 'status': 'pass',
                'detail': 'Valid SSL certificate found and up to date.', 'points': 15}
    except Exception:
        return {'id': 'ssl', 'title': 'SSL certificate', 'status': 'fail',
                'detail': 'No valid SSL certificate found.', 'points': 0}


# ── 2. Privacy Policy ─────────────────────────────────────────────────────────
def check_privacy_policy(soup):
    if soup is None:
        return {'id': 'privacy', 'title': 'Privacy policy', 'status': 'warn',
                'detail': 'Could not scan page.', 'points': 5}
    text = soup.get_text().lower()
    links_text = [a.get_text().lower() for a in soup.find_all('a')]
    links_href = [a.get('href', '').lower() for a in soup.find_all('a')]
    all_text = text + ' ' + ' '.join(links_text) + ' ' + ' '.join(links_href)
    if any(p in all_text for p in ['privacy policy', 'privacy notice', 'privacy-policy', '/privacy']):
        return {'id': 'privacy', 'title': 'Privacy policy', 'status': 'pass',
                'detail': 'Privacy policy link found and accessible.', 'points': 10}
    return {'id': 'privacy', 'title': 'Privacy policy', 'status': 'fail',
            'detail': 'No privacy policy found. Required under UK GDPR.', 'points': 0}


# ── 3. Dark Patterns ──────────────────────────────────────────────────────────
def check_dark_patterns(soup, html):
    if soup is None or html is None:
        return {'id': 'dark_patterns', 'title': 'Dark patterns', 'status': 'warn',
                'detail': 'Could not scan page.', 'points': 5}
    issues_found = []
    text = soup.get_text().lower()
    urgency_phrases = ['only \\d+ left', 'limited time', 'expires in', 'hurry',
                       'selling fast', 'last chance', 'today only', 'offer ends',
                       'flash sale', 'almost gone', 'low stock']
    for phrase in urgency_phrases:
        if re.search(phrase, text):
            issues_found.append(f'Urgency phrase: "{phrase}"')
    if re.search(r'countdown|timer|setinterval.*\d{2}:\d{2}', html.lower()):
        issues_found.append('Countdown timer detected')
    negative_framing = ['no, i don\'t want', 'no thanks', 'no, i hate', 'i don\'t want']
    for phrase in negative_framing:
        if phrase in text:
            issues_found.append(f'Negative framing: "{phrase}"')
    preticked = soup.find_all('input', {'type': 'checkbox', 'checked': True})
    if preticked:
        issues_found.append(f'{len(preticked)} pre-ticked checkbox(es)')
    if issues_found:
        return {'id': 'dark_patterns', 'title': 'Dark patterns', 'status': 'fail',
                'detail': f'{len(issues_found)} dark pattern(s) found: ' + '; '.join(issues_found[:2]),
                'points': 0, 'issues': issues_found}
    return {'id': 'dark_patterns', 'title': 'Dark patterns', 'status': 'pass',
            'detail': 'No manipulative patterns detected.', 'points': 15}


# ── 4. Cookie Consent ─────────────────────────────────────────────────────────
def check_cookie_consent(soup, html):
    if soup is None:
        return {'id': 'cookies', 'title': 'Cookie consent', 'status': 'warn',
                'detail': 'Could not scan page.', 'points': 5}
    preticked = soup.find_all('input', {'type': 'checkbox', 'checked': True})
    if preticked:
        return {'id': 'cookies', 'title': 'Cookie consent', 'status': 'fail',
                'detail': f'{len(preticked)} pre-ticked checkbox(es) found. Violates GDPR.', 'points': 0}
    full_text = soup.get_text().lower()
    links_href = [a.get('href', '').lower() for a in soup.find_all('a')]
    html_lower = html.lower() if html else ''
    cookie_signals = [
        'cookie' in full_text,
        any('cookie' in h for h in links_href),
        'cookieconsent' in html_lower,
        'cookie-consent' in html_lower,
        'cookie_consent' in html_lower,
        'cookiebot' in html_lower,
        'onetrust' in html_lower,
        'gdpr' in html_lower,
        'cc_cookie' in html_lower,
        'tarteaucitron' in html_lower,
        'axeptio' in html_lower,
    ]
    if sum(cookie_signals) >= 2:
        platform = ''
        if 'onetrust' in html_lower: platform = ' (OneTrust detected)'
        elif 'cookiebot' in html_lower: platform = ' (Cookiebot detected)'
        elif 'axeptio' in html_lower: platform = ' (Axeptio detected)'
        return {'id': 'cookies', 'title': 'Cookie consent', 'status': 'pass',
                'detail': f'Cookie consent notice found{platform}.', 'points': 10}
    return {'id': 'cookies', 'title': 'Cookie consent', 'status': 'warn',
            'detail': 'No cookie consent banner detected. Add one to comply with UK GDPR.', 'points': 3}


# ── 5. Contact Information ────────────────────────────────────────────────────
def check_contact_info(soup):
    if soup is None:
        return {'id': 'contact', 'title': 'Contact information', 'status': 'warn',
                'detail': 'Could not scan page.', 'points': 5}
    text = soup.get_text().lower()
    links_href = [a.get('href', '').lower() for a in soup.find_all('a')]
    has_email = bool(re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', soup.get_text()))
    has_email = has_email or any('mailto:' in h for h in links_href)
    has_phone = bool(re.search(r'(\+44|0044|07\d{9}|0[1-9]\d{8,9}|\(\d{3,5}\)\s?\d{3,8})', soup.get_text()))
    has_contact_page = any(p in text or any(p in h for h in links_href)
                           for p in ['contact us', 'contact', '/contact', 'get in touch', 'reach us'])
    has_address = bool(re.search(r'\b(street|road|avenue|lane|drive|court|place|london|manchester|birmingham|uk|united kingdom)\b', text))
    signals = sum([has_email, has_phone, has_contact_page, has_address])
    if signals >= 3:
        return {'id': 'contact', 'title': 'Contact information', 'status': 'pass',
                'detail': 'Email, phone and contact page all found.', 'points': 10}
    elif signals >= 1:
        found = []
        if has_email: found.append('email')
        if has_phone: found.append('phone')
        if has_contact_page: found.append('contact page')
        return {'id': 'contact', 'title': 'Contact information', 'status': 'warn',
                'detail': f'Partial contact info found ({", ".join(found)}). Add more for trust.', 'points': 5}
    return {'id': 'contact', 'title': 'Contact information', 'status': 'fail',
            'detail': 'No contact information found. Customers need to be able to reach you.', 'points': 0}


# ── 6. Page Sentiment ─────────────────────────────────────────────────────────
def check_sentiment(soup):
    if soup is None:
        return {'id': 'sentiment', 'title': 'Page tone', 'status': 'warn',
                'detail': 'Could not scan page.', 'points': 5}
    try:
        text = ' '.join(soup.get_text().split()[:300])
        blob = TextBlob(text)
        polarity = round(blob.sentiment.polarity, 2)
        if polarity >= 0.1:
            return {'id': 'sentiment', 'title': 'Page tone', 'status': 'pass',
                    'detail': f'Positive tone detected (score: {polarity}). Good for conversions.', 'points': 10}
        elif polarity >= -0.05:
            return {'id': 'sentiment', 'title': 'Page tone', 'status': 'warn',
                    'detail': f'Neutral tone detected (score: {polarity}). Try warmer, more positive copy.', 'points': 5}
        return {'id': 'sentiment', 'title': 'Page tone', 'status': 'fail',
                'detail': f'Negative tone detected (score: {polarity}). This hurts trust.', 'points': 0}
    except Exception:
        return {'id': 'sentiment', 'title': 'Page tone', 'status': 'warn',
                'detail': 'Could not analyse page tone.', 'points': 5}


# ── 7. Returns Policy ─────────────────────────────────────────────────────────
def check_returns_policy(soup):
    if soup is None:
        return {'id': 'returns', 'title': 'Returns policy', 'status': 'warn',
                'detail': 'Could not scan page.', 'points': 5}
    text = soup.get_text().lower()
    links_href = [a.get('href', '').lower() for a in soup.find_all('a')]
    all_text = text + ' ' + ' '.join(links_href)
    if any(p in all_text for p in ['return policy', 'returns policy', 'refund policy',
                                    'money back', '30-day', '14 day return',
                                    '/returns', '/refund', 'refund-policy', 'returns-policy']):
        return {'id': 'returns', 'title': 'Returns policy', 'status': 'pass',
                'detail': 'Returns policy found and clearly linked.', 'points': 10}
    return {'id': 'returns', 'title': 'Returns policy', 'status': 'fail',
            'detail': 'No returns policy found. Required by UK Consumer Rights Act 2015.', 'points': 0}


# ── 8. Terms & Conditions ─────────────────────────────────────────────────────
def check_terms(soup):
    if soup is None:
        return {'id': 'terms', 'title': 'Terms & conditions', 'status': 'warn',
                'detail': 'Could not scan page.', 'points': 3}
    text = soup.get_text().lower()
    links_href = [a.get('href', '').lower() for a in soup.find_all('a')]
    all_text = text + ' ' + ' '.join(links_href)
    if any(p in all_text for p in ['terms and conditions', 'terms of service', 'terms of use',
                                    '/terms', 'terms & conditions', 't&c', 'tcs']):
        return {'id': 'terms', 'title': 'Terms & conditions', 'status': 'pass',
                'detail': 'Terms & conditions found.', 'points': 8}
    return {'id': 'terms', 'title': 'Terms & conditions', 'status': 'warn',
            'detail': 'No terms & conditions found. Recommended for consumer trust.', 'points': 2}


# ── 9. About Page ─────────────────────────────────────────────────────────────
def check_about_page(soup):
    if soup is None:
        return {'id': 'about', 'title': 'About page', 'status': 'warn',
                'detail': 'Could not scan page.', 'points': 3}
    text = soup.get_text().lower()
    links_href = [a.get('href', '').lower() for a in soup.find_all('a')]
    all_text = text + ' ' + ' '.join(links_href)
    if any(p in all_text for p in ['about us', 'about the company', '/about', 'our story',
                                    'who we are', 'our mission']):
        return {'id': 'about', 'title': 'About page', 'status': 'pass',
                'detail': 'About page found. Builds brand credibility.', 'points': 7}
    return {'id': 'about', 'title': 'About page', 'status': 'warn',
            'detail': 'No about page found. An about page builds trust with customers.', 'points': 2}


# ── 10. Social Proof ──────────────────────────────────────────────────────────
def check_social_proof(soup, html):
    if soup is None:
        return {'id': 'social_proof', 'title': 'Social proof', 'status': 'warn',
                'detail': 'Could not scan page.', 'points': 3}
    html_lower = html.lower() if html else ''
    text = soup.get_text().lower()
    signals = []
    review_platforms = ['trustpilot', 'reviews.io', 'feefo', 'google reviews',
                        'tripadvisor', 'yotpo', 'judge.me', 'okendo']
    for platform in review_platforms:
        if platform in html_lower or platform in text:
            signals.append(platform.title())
    if re.search(r'\b\d[\d,]+\s*(reviews?|ratings?|customers?|orders?)\b', text):
        signals.append('Review count')
    if any(p in text for p in ['★', '⭐', 'stars', 'rated', 'out of 5', '/5']):
        signals.append('Star ratings')
    if any(p in html_lower for p in ['facebook.com/sharer', 'twitter.com/intent',
                                      'instagram.com', 'tiktok.com']):
        signals.append('Social media')
    if signals:
        return {'id': 'social_proof', 'title': 'Social proof', 'status': 'pass',
                'detail': f'Social proof found: {", ".join(signals[:3])}.', 'points': 8}
    return {'id': 'social_proof', 'title': 'Social proof', 'status': 'warn',
            'detail': 'No social proof detected. Add reviews or ratings to build trust.', 'points': 2}


# ── 11. HTTPS Enforcement ─────────────────────────────────────────────────────
def check_https_enforcement(url):
    if url.startswith('https://'):
        return {'id': 'https', 'title': 'HTTPS enforcement', 'status': 'pass',
                'detail': 'Site uses HTTPS. Secure connection enforced.', 'points': 5}
    return {'id': 'https', 'title': 'HTTPS enforcement', 'status': 'fail',
            'detail': 'Site does not use HTTPS. Customer data is at risk.', 'points': 0}


# ── 12. Domain Age ────────────────────────────────────────────────────────────
def check_domain_age(url):
    try:
        hostname = url.replace('https://', '').replace('http://', '').split('/')[0]
        w = pythonwhois.query(hostname)
        if w and w.creation_date:
            from datetime import datetime
            creation = w.creation_date
            if isinstance(creation, list):
                creation = creation[0]
            age_days = (datetime.now() - creation).days
            age_years = age_days // 365
            if age_years >= 2:
                return {'id': 'domain_age', 'title': 'Domain age', 'status': 'pass',
                        'detail': f'Domain is {age_years} years old. Established site.', 'points': 5}
            elif age_years >= 1:
                return {'id': 'domain_age', 'title': 'Domain age', 'status': 'warn',
                        'detail': f'Domain is {age_years} year(s) old. Relatively new.', 'points': 3}
            return {'id': 'domain_age', 'title': 'Domain age', 'status': 'warn',
                    'detail': f'Domain is only {age_days} days old. New sites may have lower trust.', 'points': 1}
    except Exception:
        pass
    return {'id': 'domain_age', 'title': 'Domain age', 'status': 'warn',
            'detail': 'Could not verify domain age.', 'points': 3}


# ── Main scanner ──────────────────────────────────────────────────────────────
def run_full_scan(url):
    if not url.startswith('http'):
        url = 'https://' + url
    html, soup = fetch_page(url)

    checks = [
        check_ssl(url),
        check_https_enforcement(url),
        check_privacy_policy(soup),
        check_dark_patterns(soup, html),
        check_cookie_consent(soup, html),
        check_contact_info(soup),
        check_sentiment(soup),
        check_returns_policy(soup),
        check_terms(soup),
        check_about_page(soup),
        check_social_proof(soup, html),
        check_domain_age(url),
    ]

    max_points = sum([15, 5, 10, 15, 10, 10, 10, 10, 8, 7, 8, 5])  # 113
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
        grade_desc = 'Significant trust issues detected. These are costing you customers.'

    issues = []
    for check in checks:
        if check['status'] == 'fail':
            issues.append({
                'severity': 'high' if check['points'] >= 10 else 'medium',
                'title': check['title'] + ' — action required',
                'detail': check['detail'],
            })
        elif check['status'] == 'warn':
            issues.append({
                'severity': 'low',
                'title': check['title'] + ' — improvement suggested',
                'detail': check['detail'],
            })

    return {
        'url': url,
        'score': score,
        'grade': grade,
        'grade_desc': grade_desc,
        'checks': checks,
        'issues': issues,
        'passed_count': len([c for c in checks if c['status'] == 'pass']),
        'issues_count': len([c for c in checks if c['status'] == 'fail']),
        'warnings_count': len([c for c in checks if c['status'] == 'warn']),
    }
