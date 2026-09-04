import base64
import binascii

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from OpenSSL import crypto


def get_cert_SANs(cert: bytes):
    cert = x509.load_pem_x509_certificate(cert, default_backend())
    san_list = []
    for extension in cert.extensions:
        if isinstance(extension.value, x509.SubjectAlternativeName):
            san = extension.value
            for name in san:
                san_list.append(name.value)
    return san_list


def _add_base64_padding(value: str) -> str:
    missing_padding = len(value) % 4
    return value + ("=" * (4 - missing_padding)) if missing_padding else value


def validate_wireguard_key(key_b64: str, field_name: str = "wireguard key") -> str:
    """Validate and normalize a standard Base64-encoded 32-byte WireGuard key."""
    try:
        key_bytes = base64.b64decode(_add_base64_padding(key_b64.strip()), validate=True)
    except (AttributeError, ValueError, binascii.Error) as exc:
        raise ValueError(f"Invalid {field_name}.") from exc

    if len(key_bytes) != 32:
        raise ValueError(f"Invalid {field_name}.")

    return base64.b64encode(key_bytes).decode("ascii")


def get_wireguard_public_key(private_key_b64: str) -> str:
    """Derive the WireGuard public key for a Base64-encoded private key."""
    normalized_private_key = validate_wireguard_key(private_key_b64, "wireguard private_key")
    private_key_bytes = base64.b64decode(normalized_private_key, validate=True)
    private_key = x25519.X25519PrivateKey.from_private_bytes(private_key_bytes)
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(public_key_bytes).decode("ascii")


def generate_wireguard_keypair() -> tuple[str, str]:
    """Generate a WireGuard-compatible X25519 private/public key pair."""
    private_key = x25519.X25519PrivateKey.generate()
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return (
        base64.b64encode(private_key_bytes).decode("ascii"),
        base64.b64encode(public_key_bytes).decode("ascii"),
    )


def generate_certificate():
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 4096)
    cert = crypto.X509()
    cert.get_subject().CN = "Gozargah"
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(100 * 365 * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, "sha512")
    cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8")
    key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8")

    return {
        "cert": cert_pem,
        "key": key_pem,
    }
