"""
TLS Fingerprinting - Browser fingerprint impersonation.
Like Scrapling's TLS fingerprint spoofing.
"""
import ssl
import socket
from typing import Dict, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class TLSProfile:
    """TLS fingerprint profile."""
    name: str
    protocol_version: str
    cipher_suites: list
    extensions: list
    elliptic_curves: list
    signature_algorithms: list


class TLSFingerprinter:
    """
    TLS fingerprint impersonation.
    Spoofs TLS signatures to appear as real browsers.
    """

    # Browser TLS profiles
    PROFILES = {
        "chrome_120": TLSProfile(
            name="Chrome 120",
            protocol_version="TLS 1.3",
            cipher_suites=[
                0x1301, 0x1302, 0x1303,  # TLS 1.3
                0xc02c, 0xc030, 0x002f,  # TLS 1.2
            ],
            extensions=[
                0x0b, 0x0a, 0x33, 0x2b,  # signature, EC, supported_groups, application_layer_protocol_negotiation
                0xff,
            ],
            elliptic_curves=[29, 23, 25],  # X25519, P-256, P-384
            signature_algorithms=[
                0x0403, 0x0807, 0x0808,  # ecdsa_secp256r1_sha256, rsa_pss_rsae_sha256, rsa_pkcs1_sha256
            ],
        ),
        "firefox_121": TLSProfile(
            name="Firefox 121",
            protocol_version="TLS 1.3",
            cipher_suites=[
                0x1301, 0x1302, 0x1303,
                0xc02c, 0xc030, 0xcca9,
            ],
            extensions=[
                0x0b, 0x0a, 0x33, 0x2b, 0xff,
            ],
            elliptic_curves=[29, 23, 24],  # X25519, P-256, P-521
            signature_algorithms=[
                0x0403, 0x0807, 0x0808, 0x0401,  # + rsa_pkcs1_sha1
            ],
        ),
        "safari_17": TLSProfile(
            name="Safari 17",
            protocol_version="TLS 1.3",
            cipher_suites=[
                0x1301, 0x1302, 0x1303,
                0xc02c, 0xcca9,
            ],
            extensions=[
                0x0b, 0x0a, 0x33, 0x2b,
            ],
            elliptic_curves=[29, 23, 25],
            signature_algorithms=[
                0x0403, 0x0807,
            ],
        ),
    }

    def __init__(self, profile_name: str = "chrome_120"):
        self.profile = self.PROFILES.get(profile_name, self.PROFILES["chrome_120"])

    def get_cipher_suites(self) -> list:
        """Get cipher suites for this profile."""
        return self.profile.cipher_suites

    def get_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with this profile's settings."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        # Set cipher suites
        cipher_list = ":".join(
            hex(c)[2:].upper().zfill(4) for c in self.profile.cipher_suites
        )
        context.set_ciphers(cipher_list)

        # Load default certs
        context.load_default_certs()

        # Set options
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1

        return context

    def create_session(self) -> "TLSClient":
        """Create a TLS client with this profile."""
        return TLSClient(self)


class TLSClient:
    """HTTP client with TLS fingerprinting."""

    def __init__(self, fingerprinter: TLSFingerprinter):
        self.fingerprinter = fingerprinter
        self.session = None

    def get(self, url: str, **kwargs) -> Optional[any]:
        """Make GET request with TLS fingerprint."""
        import requests

        context = self.fingerprinter.get_ssl_context()

        # Create adapter with SSL context
        adapter = requests.adapters.HTTPAdapter()
        adapter.config = {"ssl_context": context}

        session = requests.Session()
        session.mount("https://", adapter)

        # Set headers matching browser profile
        headers = kwargs.pop("headers", {})
        profile = self.fingerprinter.profile

        if "User-Agent" not in headers:
            if "chrome" in profile.name.lower():
                headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            elif "firefox" in profile.name.lower():
                headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
            elif "safari" in profile.name.lower():
                headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"

        kwargs["headers"] = headers

        try:
            return session.get(url, **kwargs)
        except Exception as e:
            logger.error(f"TLS request failed: {e}")
            return None


class TLSFingerprintGenerator:
    """
    Generate custom TLS fingerprints.
    """

    @staticmethod
    def generate_random() -> TLSProfile:
        """Generate a random browser-like TLS profile."""
        import random

        return TLSProfile(
            name=f"Custom_{random.randint(1000, 9999)}",
            protocol_version="TLS 1.3",
            cipher_suites=random.sample([
                0x1301, 0x1302, 0x1303,
                0xc02c, 0xc030, 0xc02b, 0xcca9,
                0x002f, 0x009c, 0x009d,
            ], k=random.randint(4, 8)),
            extensions=[0x0b, 0x0a, 0x33, 0x2b, 0xff][:random.randint(3, 5)],
            elliptic_curves=random.sample([29, 23, 24, 25], k=random.randint(2, 3)),
            signature_algorithms=random.sample([
                0x0403, 0x0807, 0x0808, 0x0401,
            ], k=random.randint(2, 4)),
        )

    @staticmethod
    def generate_from_real_browser() -> Dict[str, str]:
        """Generate fingerprint mimicking real browser headers."""
        import random

        browsers = [
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "accept_language": "en-US,en;q=0.9",
                "accept_encoding": "gzip, deflate, br",
                "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec_ch_ua_mobile": "?0",
                "sec_ch_ua_platform": '"Windows"',
                "sec_fetch_dest": "document",
                "sec_fetch_mode": "navigate",
                "sec_fetch_site": "none",
                "sec_fetch_user": "?1",
                "upgrade_insecure_requests": "1",
            },
            {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "accept_language": "en-US,en;q=0.9",
                "accept_encoding": "gzip, deflate, br",
                "sec_ch_ua": '"Safari";v="17.2", "Not(A:Brand";v="8.0.0.1", "Chromium";v="120.0.6099.109"',
                "sec_ch_ua_mobile": "?0",
                "sec_ch_ua_platform": '"macOS"',
                "sec_fetch_dest": "document",
                "sec_fetch_mode": "navigate",
                "sec_fetch_site": "none",
                "sec_fetch_user": "?1",
                "upgrade_insecure_requests": "1",
            },
        ]

        return random.choice(browsers)
