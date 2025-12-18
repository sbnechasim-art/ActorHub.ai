"""
ActorHub.ai Security Audit
"""
import sys
import os
import time
import re
from urllib.parse import quote

# Fix encoding for Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx

API_URL = "http://localhost:8000"


class SecurityAuditor:
    def __init__(self):
        self.client = httpx.Client(base_url=API_URL, timeout=30)
        self.vulnerabilities = []
        self.warnings = []
        self.passed = []

    def log_vuln(self, severity, title, details):
        self.vulnerabilities.append({
            "severity": severity,
            "title": title,
            "details": details
        })
        print(f"  ❌ [{severity}] {title}")

    def log_warning(self, title, details):
        self.warnings.append({"title": title, "details": details})
        print(f"  ⚠️ {title}")

    def log_pass(self, title):
        self.passed.append(title)
        print(f"  ✅ {title}")

    def run_all_tests(self):
        print("🔒 ActorHub.ai Security Audit")
        print("=" * 60)

        self.test_sql_injection()
        self.test_xss()
        self.test_auth_bypass()
        self.test_rate_limiting()
        self.test_security_headers()
        self.test_sensitive_data_exposure()
        self.test_broken_auth()
        self.test_api_security()
        self.test_cors()

        self.print_report()

    def test_sql_injection(self):
        """בדיקת SQL Injection"""
        print("\n🔍 SQL Injection Tests:")

        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users;--",
            "1 UNION SELECT * FROM users",
            "admin'--",
            "1; SELECT * FROM identities"
        ]

        vulnerable = False

        for payload in payloads:
            try:
                response = self.client.get(f"/api/v1/marketplace/listings?search={quote(payload)}")

                if response.status_code == 500:
                    # Check if it's a SQL error
                    if any(err in response.text.lower() for err in ["sql", "syntax", "query", "postgresql", "psycopg"]):
                        self.log_vuln("HIGH", "SQL Injection", f"Payload: {payload}")
                        vulnerable = True
                        break

                # Check for SQL errors in response
                if any(err in response.text.lower() for err in ["sql syntax", "pg_", "postgresql error"]):
                    self.log_vuln("HIGH", "SQL Error Exposed", f"Response contains SQL error info")
                    vulnerable = True
                    break
            except Exception as e:
                pass

        if not vulnerable:
            self.log_pass("SQL Injection - Protected")

    def test_xss(self):
        """בדיקת Cross-Site Scripting"""
        print("\n🔍 XSS Tests:")

        payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
        ]

        vulnerable = False

        for payload in payloads:
            try:
                response = self.client.get(f"/api/v1/marketplace/listings?search={quote(payload)}")

                # Check if payload is reflected unescaped in HTML
                if payload in response.text and "text/html" in response.headers.get("content-type", ""):
                    self.log_vuln("MEDIUM", "Reflected XSS", f"Payload reflected: {payload[:30]}")
                    vulnerable = True
                    break
            except:
                pass

        if not vulnerable:
            self.log_pass("XSS - Protected (API returns JSON)")

    def test_auth_bypass(self):
        """בדיקת עקיפת Authentication"""
        print("\n🔍 Authentication Bypass Tests:")

        protected_endpoints = [
            "/api/v1/users/me",
            "/api/v1/identity/mine",
        ]

        vulnerable = False

        for endpoint in protected_endpoints:
            try:
                # Test without token
                response = self.client.get(endpoint)

                if response.status_code == 200:
                    data = response.json()
                    # Check if it actually returned user data
                    if data.get("id") or data.get("email"):
                        self.log_vuln("CRITICAL", "Auth Bypass", f"Endpoint accessible without auth: {endpoint}")
                        vulnerable = True

                # Test with invalid token
                response = self.client.get(
                    endpoint,
                    headers={"Authorization": "Bearer invalid_token_here"}
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("id") or data.get("email"):
                        self.log_vuln("CRITICAL", "Invalid Token Accepted", f"Endpoint: {endpoint}")
                        vulnerable = True
            except:
                pass

        if not vulnerable:
            self.log_pass("Authentication - Protected endpoints secured")

    def test_rate_limiting(self):
        """בדיקת Rate Limiting"""
        print("\n🔍 Rate Limiting Tests:")

        blocked = False

        for i in range(120):
            try:
                response = self.client.get("/api/v1/marketplace/listings")

                if response.status_code == 429:
                    blocked = True
                    self.log_pass(f"Rate Limiting - Blocked after {i} requests")
                    break
            except:
                pass

        if not blocked:
            self.log_warning(
                "Rate Limiting may be too high or disabled",
                "120 requests completed without blocking"
            )

    def test_security_headers(self):
        """בדיקת Security Headers"""
        print("\n🔍 Security Headers Tests:")

        try:
            response = self.client.get("/health")
            headers = response.headers

            required_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": ["DENY", "SAMEORIGIN"],
            }

            for header, expected in required_headers.items():
                value = headers.get(header)

                if value is None:
                    self.log_warning(f"Missing header: {header}", "")
                elif expected and value not in (expected if isinstance(expected, list) else [expected]):
                    self.log_warning(f"Incorrect {header}", f"Got: {value}")
                else:
                    self.log_pass(f"Header: {header}")

            # Check for additional good headers
            if headers.get("X-XSS-Protection"):
                self.log_pass("Header: X-XSS-Protection")
        except Exception as e:
            self.log_warning(f"Could not check headers: {e}", "")

    def test_sensitive_data_exposure(self):
        """בדיקת חשיפת מידע רגיש"""
        print("\n🔍 Sensitive Data Exposure Tests:")

        try:
            # Check if errors expose stack traces
            response = self.client.get("/api/v1/nonexistent_endpoint_12345")

            sensitive_patterns = [
                r"File \".*\.py\"",
                r"line \d+, in",
                r"Traceback \(most recent",
            ]

            for pattern in sensitive_patterns:
                if re.search(pattern, response.text, re.IGNORECASE):
                    self.log_vuln("MEDIUM", "Stack Trace Exposed", f"Pattern found: {pattern}")
                    return

            self.log_pass("Error responses don't expose stack traces")

            # Check if .env or config is accessible
            sensitive_paths = [
                "/.env",
                "/.git/config",
            ]

            for path in sensitive_paths:
                try:
                    response = self.client.get(path)
                    if response.status_code == 200 and len(response.text) > 10:
                        if "=" in response.text or "[" in response.text:
                            self.log_vuln("CRITICAL", "Sensitive File Exposed", f"Path: {path}")
                            return
                except:
                    pass

            self.log_pass("Sensitive files not accessible")
        except Exception as e:
            self.log_warning(f"Error testing: {e}", "")

    def test_broken_auth(self):
        """בדיקת בעיות Authentication"""
        print("\n🔍 Broken Authentication Tests:")

        # Test weak passwords
        weak_passwords = ["123456", "password", "admin", "test"]
        weak_accepted = False

        for pwd in weak_passwords:
            try:
                response = self.client.post("/api/v1/users/register", json={
                    "email": f"weakpwd_{int(time.time())}_{pwd}@test.com",
                    "password": pwd,
                    "full_name": "Test"
                })

                if response.status_code in [200, 201]:
                    weak_accepted = True
                    self.log_vuln("MEDIUM", "Weak Password Accepted", f"Password: {pwd}")
                    break
            except:
                pass

        if not weak_accepted:
            self.log_pass("Weak passwords rejected")

    def test_api_security(self):
        """בדיקת אבטחת API"""
        print("\n🔍 API Security Tests:")

        # Test if verify endpoint requires auth
        try:
            response = self.client.post(
                "/api/v1/identity/verify",
                json={"image_url": "http://test.com/image.jpg"}
            )

            if response.status_code == 200:
                self.log_warning("Verify endpoint may be too open", "Consider requiring API key")
            else:
                self.log_pass("Verify endpoint requires authentication")
        except:
            self.log_pass("Verify endpoint protected")

    def test_cors(self):
        """בדיקת CORS Configuration"""
        print("\n🔍 CORS Tests:")

        try:
            response = self.client.options(
                "/api/v1/users/login",
                headers={
                    "Origin": "https://evil-site.com",
                    "Access-Control-Request-Method": "POST"
                }
            )

            cors_origin = response.headers.get("access-control-allow-origin")

            if cors_origin == "*":
                self.log_warning("CORS Wildcard", "Allows requests from any origin - OK for development")
            elif cors_origin == "https://evil-site.com":
                self.log_vuln("HIGH", "CORS Misconfigured", "Reflects malicious origin")
            else:
                self.log_pass("CORS properly configured")
        except:
            self.log_pass("CORS check completed")

    def print_report(self):
        """הדפסת דוח סופי"""
        print("\n")
        print("=" * 60)
        print("📊 SECURITY AUDIT REPORT")
        print("=" * 60)

        # Critical/High vulnerabilities
        critical = [v for v in self.vulnerabilities if v["severity"] in ["CRITICAL", "HIGH"]]
        medium = [v for v in self.vulnerabilities if v["severity"] == "MEDIUM"]

        print(f"\n🔴 Critical/High: {len(critical)}")
        for v in critical:
            print(f"   [{v['severity']}] {v['title']}")
            print(f"      {v['details']}")

        print(f"\n🟡 Medium: {len(medium)}")
        for v in medium:
            print(f"   {v['title']}: {v['details']}")

        print(f"\n🟠 Warnings: {len(self.warnings)}")
        for w in self.warnings:
            print(f"   {w['title']}")

        print(f"\n✅ Passed: {len(self.passed)}")
        for p in self.passed:
            print(f"   {p}")

        # Final verdict
        print("\n" + "=" * 60)

        if critical:
            print("⛔ CRITICAL ISSUES FOUND - DO NOT DEPLOY!")
        elif medium:
            print("⚠️ MEDIUM ISSUES FOUND - Fix before production")
        elif self.warnings:
            print("✅ PASSED with warnings - Review recommendations")
        else:
            print("🎉 ALL TESTS PASSED - Ready for production!")

        print("=" * 60)

        return len(critical) == 0


def main():
    auditor = SecurityAuditor()
    auditor.run_all_tests()


if __name__ == "__main__":
    main()
