def validate_access_code(code):
    import json, os
    codes_file = 'access_codes.json'
    if not os.path.exists(codes_file):
        return None
    with open(codes_file, 'r') as f:
        codes = json.load(f)
    code = code.strip().upper()
    return codes.get(code) if codes.get(code, {}).get('active') else None	
