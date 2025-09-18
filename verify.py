import sys
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature


def verify_certificate(cert_file: str, sig_file: str, pubkey_file: str):
    # Load certificate JSON
    with open(cert_file, "rb") as f:
        cert_data = f.read()

    # Load signature
    with open(sig_file, "rb") as f:
        signature = f.read()

    # Load public key
    with open(pubkey_file, "rb") as f:
        pubkey = serialization.load_pem_public_key(f.read())

    try:
        # Verify signature
        pubkey.verify(
            signature,
            cert_data,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print("[PASS] Signature valid for", cert_file)
        return True
    except InvalidSignature:
        print("[FAIL] Invalid signature for", cert_file)
        return False


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python verify.py <cert.json> <cert.sig> <operator_public.pem>")
        sys.exit(1)

    cert_file, sig_file, pubkey_file = sys.argv[1:]
    verify_certificate(cert_file, sig_file, pubkey_file)
