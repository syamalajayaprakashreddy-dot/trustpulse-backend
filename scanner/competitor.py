import requests
from bs4 import BeautifulSoup
from .scanner import run_full_scan
from urllib.parse import urlparse


def get_domain(url):
    """Extract clean domain from URL."""
    if not url.startswith('http'):
        url = 'https://' + url
    return urlparse(url).netloc.replace('www.', '')


def run_competitor_comparison(main_url, competitor_urls):
    """
    Scan main site and up to 3 competitors.
    Returns comparison data with scores and insights.
    """
    results = []

    # Scan main site
    main_result = run_full_scan(main_url)
    main_result['domain'] = get_domain(main_url)
    main_result['is_main'] = True
    results.append(main_result)

    # Scan competitors
    for url in competitor_urls[:3]:
        if url.strip():
            try:
                comp_result = run_full_scan(url.strip())
                comp_result['domain'] = get_domain(url.strip())
                comp_result['is_main'] = False
                results.append(comp_result)
            except Exception:
                pass

    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)

    # Find main site rank
    main_rank = next((i+1 for i, r in enumerate(results) if r.get('is_main')), 1)

    # Generate insights
    scores = [r['score'] for r in results]
    avg_score = round(sum(scores) / len(scores))
    main_score = next((r['score'] for r in results if r.get('is_main')), 0)
    top_score = max(scores)
    gap = top_score - main_score

    insights = []
    if main_rank == 1:
        insights.append({
            'type': 'positive',
            'text': f'You have the highest trust score among all competitors! You lead by {gap} points.'
        })
    else:
        insights.append({
            'type': 'warning',
            'text': f'You rank #{main_rank} out of {len(results)} sites. You are {gap} points behind the leader.'
        })

    if main_score > avg_score:
        insights.append({
            'type': 'positive',
            'text': f'Your score ({main_score}) is above the industry average ({avg_score}).'
        })
    else:
        insights.append({
            'type': 'warning',
            'text': f'Your score ({main_score}) is below the industry average ({avg_score}). Focus on fixing your issues.'
        })

    # Find what competitors do better
    main_checks = next((r['checks'] for r in results if r.get('is_main')), [])
    main_fails = [c['title'] for c in main_checks if c['status'] == 'fail']
    if main_fails:
        insights.append({
            'type': 'action',
            'text': f'Your biggest trust gaps: {", ".join(main_fails[:2])}. Fixing these could boost your score significantly.'
        })

    return {
        'results': results,
        'main_rank': main_rank,
        'total_sites': len(results),
        'avg_score': avg_score,
        'insights': insights,
    }