#!/usr/bin/env python
import sys
print('1. Importing dotenv...')
from dotenv import load_dotenv
print('2. Loading .env...')
load_dotenv()
print('3. Importing knowledge...')
from app.knowledge import reload_index
print('4. Knowledge OK')
print('5. Importing database...')
from app.database import init_db
print('6. Database OK')
print('Done - all imports successful')
