from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .scanner import run_full_scan


@api_view(['POST'])
def scan_website(request):
    url = request.data.get('url', '').strip()

    if not url:
        return Response(
            {'error': 'Please provide a URL to scan.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(url) > 500:
        return Response(
            {'error': 'URL is too long.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        result = run_full_scan(url)
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Scan failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def health_check(request):
    return Response({'status': 'TrustPulse API is running ✓'})