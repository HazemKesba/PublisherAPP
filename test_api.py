import requests

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0

def test(name, method, url, expected_status, json=None):
    global passed, failed
    try:
        res = requests.request(method, url, json=json, timeout=5)
        status = "✅ PASS" if res.status_code == expected_status else "❌ FAIL"
        if res.status_code != expected_status:
            failed += 1
            print(f"{status} | {name}")
            print(f"       Expected {expected_status}, got {res.status_code} → {res.text[:200]}")
        else:
            passed += 1
            print(f"{status} | {name}")
        return res
    except Exception as e:
        failed += 1
        print(f"❌ FAIL | {name} → {e}")
        return None

print("=" * 55)
print("           PublisherAPP — API Test Suite")
print("=" * 55)

# ── Index ──────────────────────────────────────────────
print("\n📌 Index")
test("GET /", "GET", f"{BASE}/", 200)

# ── Authors ────────────────────────────────────────────
print("\n📌 Authors")
r = test("POST /authors/  (create)", "POST", f"{BASE}/authors/", 201,
         json={"name": "Test Author", "biography": "Bio here", "royalty_percentage": 10.5})

author_id = None
if r and r.status_code == 201:
    author_id = r.json().get("author_id")

test("GET /authors/  (all)", "GET", f"{BASE}/authors/", 200)

if author_id:
    test(f"GET /authors/{author_id}", "GET", f"{BASE}/authors/{author_id}", 200)
    test(f"GET /authors/{author_id}/books", "GET", f"{BASE}/authors/{author_id}/books", 200)
    test("GET /authors/with-books/all", "GET", f"{BASE}/authors/with-books/all", 200)
    test(f"PUT /authors/{author_id}  (update)", "PUT", f"{BASE}/authors/{author_id}", 200,
         json={"name": "Updated Author"})
    test(f"DELETE /authors/{author_id}", "DELETE", f"{BASE}/authors/{author_id}", 200)
    test(f"GET /authors/{author_id} (should 404)", "GET", f"{BASE}/authors/{author_id}", 404)

# ── Formats ────────────────────────────────────────────
print("\n📌 Formats")
test("GET /formats/  (all)", "GET", f"{BASE}/formats/", 200)

# ── Analytics / Books / Retail (placeholder routes) ────
print("\n📌 Other Routes")
test("GET /analytics/", "GET", f"{BASE}/analytics/", 200)
test("GET /books/",     "GET", f"{BASE}/books/", 200)
test("GET /retail/",    "GET", f"{BASE}/retail/", 200)

# ── Summary ────────────────────────────────────────────
print("\n" + "=" * 55)
print(f"  Results: {passed} passed ✅  |  {failed} failed ❌")
print("=" * 55)
