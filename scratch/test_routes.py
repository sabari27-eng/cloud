import urllib.request
import urllib.parse
import http.cookiejar
import re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. GET login page
res = opener.open('http://127.0.0.1:5000/teacher/login')
html = res.read().decode('utf-8')
m = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html)
csrf = m.group(1) if m else ''
print("CSRF token found:", csrf)

# 2. POST login
data = urllib.parse.urlencode({'email': 'alan.turing@college.edu', 'password': 'Teacher@123', 'csrf_token': csrf}).encode('utf-8')
res = opener.open('http://127.0.0.1:5000/teacher/login', data=data)
print("Login result url:", res.geturl(), "code:", res.getcode())

# 3. GET /teacher/subject/1
try:
    res = opener.open('http://127.0.0.1:5000/teacher/subject/1')
    print("Subject 1:", res.getcode())
except Exception as e:
    print("Subject 1 ERROR:", e)

# 4. GET /teacher/subject/3
try:
    res = opener.open('http://127.0.0.1:5000/teacher/subject/3')
    print("Subject 3:", res.getcode())
except Exception as e:
    print("Subject 3 ERROR:", e)

# 5. GET /teacher/assignment/1/submissions
try:
    res = opener.open('http://127.0.0.1:5000/teacher/assignment/1/submissions')
    print("Assignment 1 submissions:", res.getcode())
except Exception as e:
    print("Assignment 1 submissions ERROR:", e)

# 6. GET /teacher/assignment/2/submissions
try:
    res = opener.open('http://127.0.0.1:5000/teacher/assignment/2/submissions')
    print("Assignment 2 submissions:", res.getcode())
except Exception as e:
    print("Assignment 2 submissions ERROR:", e)
