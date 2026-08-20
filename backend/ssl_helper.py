import os
import socket
import datetime
from typing import Tuple, Dict

def get_local_ip() -> str:
    """Returns the local IPv4 address of this machine on the LAN."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def ensure_ssl_certificates(certs_dir: str = "certs") -> Tuple[str, str]:
    """
    Generates a self-signed TLS certificate with Subject Alternative Names (SAN)
    for localhost and the local LAN IP to allow mobile devices to use cameras and mics.
    """
    os.makedirs(certs_dir, exist_ok=True)
    cert_file = os.path.join(certs_dir, "cert.pem")
    key_file = os.path.join(certs_dir, "key.pem")

    if os.path.exists(cert_file) and os.path.exists(key_file):
        return cert_file, key_file

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import ipaddress

        local_ip = get_local_ip()

        # Generate private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "VLA Studio"),
            x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
        ])

        # Add SANs for localhost, 127.0.0.1, and local LAN IP
        san_list = [
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]
        try:
            san_list.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))
        except Exception:
            pass

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
            .sign(key, hashes.SHA256())
        )

        with open(key_file, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[SSL] Created self-signed TLS certificates for LAN access in '{certs_dir}'.")
        return cert_file, key_file
    except Exception as e:
        print(f"[SSL] Notice: Could not generate TLS certificates ({e}).")
        return "", ""

def get_network_details(port: int = 8000, is_https: bool = True) -> Dict:
    local_ip = get_local_ip()
    protocol = "https" if is_https else "http"
    return {
        "local_ip": local_ip,
        "port": port,
        "protocol": protocol,
        "local_url": f"{protocol}://localhost:{port}",
        "network_url": f"{protocol}://{local_ip}:{port}"
    }
