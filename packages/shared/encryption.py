"""AES-256-GCM encryption for CMS credentials — per-tenant key derivation."""
import os
import base64
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_master_key() -> bytes:
    """Get master encryption key from environment."""
    key_hex = os.environ.get("DOPPLER_MASTER_ENCRYPTION_KEY", "")
    if not key_hex or len(key_hex) < 64:
        raise ValueError(
            "DOPPLER_MASTER_ENCRYPTION_KEY must be set as a 64-char hex string. "
            "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return bytes.fromhex(key_hex)


def derive_tenant_key(org_id: str) -> bytes:
    """Derive a unique encryption key for each organization using HMAC-SHA256."""
    master_key = _get_master_key()
    return hmac.new(master_key, org_id.encode(), hashlib.sha256).digest()


def encrypt_credential(org_id: str, plaintext: str) -> tuple[str, str]:
    """Encrypt a CMS credential for a specific organization.
    
    Returns:
        Tuple of (ciphertext_base64, nonce_base64)
    """
    key = derive_tenant_key(org_id)
    nonce = os.urandom(12)  # 96-bit nonce for AES-GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return (
        base64.b64encode(ciphertext).decode("ascii"),
        base64.b64encode(nonce).decode("ascii"),
    )


def decrypt_credential(org_id: str, ciphertext_b64: str, nonce_b64: str) -> str:
    """Decrypt a CMS credential for a specific organization.
    
    Args:
        org_id: The organization's UUID string
        ciphertext_b64: Base64-encoded ciphertext
        nonce_b64: Base64-encoded nonce/IV
    
    Returns:
        Decrypted plaintext string
    """
    key = derive_tenant_key(org_id)
    aesgcm = AESGCM(key)
    nonce = base64.b64decode(nonce_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
