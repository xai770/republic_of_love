#!/usr/bin/env python3
"""Generate test session token"""
import jwt
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')
from api.config import SECRET_KEY

user_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
payload = {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(hours=24)}
token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
print(token)
