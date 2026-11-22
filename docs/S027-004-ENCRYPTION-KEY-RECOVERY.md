# S027-004 — Client-Side Encryption & Recovery-Key Runbook

**Status:** DESIGN DOCUMENTED — NOT DEPLOYED OR DRILL-VERIFIED  
**Budget:** INR 0/month  
**Target:** Encrypt verified SQLite backup archives before any off-site transfer.

## 1. Security decisions

- Use authenticated encryption: AES-256-GCM through the Python `cryptography` package.
- Generate a fresh 256-bit random data-encryption key (DEK) for the backup set. Never derive it from a username, project name, date, or password.
- Keep the DEK separate from every ciphertext archive. The DEK must never enter Git, GitHub Issues/Actions/logs/artifacts, Dropbox, the SQLite DB, or this chat.
- Store two independently recoverable copies of the DEK under the account owner's control: (A) an encrypted password-manager secure note or equivalent protected vault, and (B) an offline copy on separately stored removable media or printed recovery material. Do not store both copies in the same physical location.
- Restrict access to the key. Anyone with both the ciphertext and DEK can read the database.
- Do not delete the local verified plaintext backup until the encrypted off-site copy has been downloaded again and verified.

## 2. Preconditions — do not bypass

Before encryption is attempted, all must be true:

1. The exact production DB path has been confirmed in the active runtime without changing it.
2. A new SQLite online backup has been created outside the live DB directory and passes `PRAGMA integrity_check`.
3. The private destination is approved and has enough free space. Dropbox quota is currently UNVERIFIED.
4. The operator has a safe way to download and independently preserve the recovery key.
5. The runtime has the `cryptography` package available. Installing it must not alter the project's pinned/runtime dependency files unless separately approved.

If any precondition fails, stop. Do not upload plaintext or ciphertext as a workaround.

## 3. Key creation and custody

Run only in the already-running, intended Colab session after the preconditions are satisfied. This is a future operator procedure, not an action performed by this documentation commit.

```python
from pathlib import Path
import os, secrets
from google.colab import files

key = secrets.token_bytes(32)
key_path = Path("/content/project_continue_backup.key")
fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "wb") as f:
    f.write(key)

# Download directly to the operator-controlled device.
files.download(str(key_path))
```

Immediately place the downloaded key in the two independent protected recovery locations described in Section 1. Confirm both copies can be retrieved by the authorized operator. Never paste or upload the key. Do not rely on the Colab filesystem as the only key copy; it is ephemeral.

If the key cannot be safely downloaded and independently stored, stop and do not encrypt/upload.

## 4. AES-256-GCM encryption format

The ciphertext file format is:

- 8-byte magic/version header: `PCBK001\0`
- 12-byte fresh random GCM nonce
- AES-256-GCM ciphertext followed by its 16-byte authentication tag

The nonce is not secret and may be stored with the ciphertext. Never reuse a nonce with the same key. A new random nonce is generated for every encryption. Authentication failure must be treated as corruption or a wrong key; never attempt to use partially decrypted bytes.

Reference implementation for an isolated test file (requires `cryptography`):

```python
from pathlib import Path
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"PCBK001\\0"

def encrypt_file(source: str, destination: str, key: bytes) -> None:
    if len(key) != 32:
        raise ValueError("AES-256 key must be exactly 32 bytes")
    src, dst = Path(source), Path(destination)
    if dst.exists():
        raise FileExistsError(dst)
    nonce = secrets.token_bytes(12)
    plaintext = src.read_bytes()
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, MAGIC)
    with dst.open("xb") as f:
        f.write(MAGIC + nonce + ciphertext)

def decrypt_file(source: str, destination: str, key: bytes) -> None:
    if len(key) != 32:
        raise ValueError("AES-256 key must be exactly 32 bytes")
    raw = Path(source).read_bytes()
    if len(raw) < len(MAGIC) + 12 + 16 or raw[:len(MAGIC)] != MAGIC:
        raise ValueError("Unknown or truncated encrypted backup")
    nonce = raw[len(MAGIC):len(MAGIC) + 12]
    ciphertext = raw[len(MAGIC) + 12:]
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, MAGIC)
    # Exclusive creation prevents accidental overwrite of any existing file.
    with Path(destination).open("xb") as f:
        f.write(plaintext)
```

This is a reference format only. It has not yet been executed or security-reviewed against the production backup. For large databases, replace the in-memory reference implementation with a vetted streaming/container format before use; do not assume this example is suitable for arbitrarily large files.

## 5. Required verification drill before production use

Use a synthetic test file first — never the live DB:

1. Create a small synthetic file containing known non-sensitive test bytes.
2. Generate a temporary test key; encrypt the file.
3. Confirm ciphertext differs from plaintext and record SHA-256 of ciphertext.
4. Decrypt using the primary key copy; compare SHA-256 with original plaintext.
5. Decrypt again using the independently stored recovery copy; compare SHA-256.
6. Attempt decryption with a wrong key and with one modified ciphertext byte; both must fail authentication and must not create a destination file.
7. Repeat after starting a fresh runtime/session to prove key recovery is independent of Colab state.
8. Record test date, tool/package version, ciphertext hash, and PASS/FAIL. Do not record the key or plaintext content.

Only after all checks pass may a verified production backup be encrypted and transferred to an approved private destination.

## 6. Recovery procedure

1. Download the encrypted archive from the private destination to a new isolated path.
2. Retrieve the DEK from the independent protected recovery store. Never retrieve it from the archive's folder.
3. Decrypt to a new, empty path. Never target the live DB path.
4. Verify the restored SQLite file with `PRAGMA integrity_check` and foreign-key checks.
5. Run application-level checks/tests against the isolated restored copy.
6. Preserve the original ciphertext and existing production DB until the recovery is accepted.

If the key is lost, AES-GCM ciphertext is unrecoverable. There is no password reset or backdoor. If the key is suspected compromised, create a new key for future backups and assess exposure of all archives encrypted under the old key.

## 7. Current acceptance state

| Control | Status |
|---|---|
| Encryption algorithm and file format selected | DOCUMENTED |
| Key separation and two-copy custody policy | DOCUMENTED |
| Recovery workflow | DOCUMENTED |
| Synthetic encrypt/decrypt drill | NOT RUN |
| Wrong-key/tamper rejection drill | NOT RUN |
| Fresh-session independent recovery drill | NOT RUN |
| Production backup encrypted | NOT DONE |
| Encrypted archive uploaded to Dropbox | NOT DONE |
| Dropbox available quota | UNVERIFIED |

**Do not mark encryption/key-recovery acceptance PASS until Sections 3–5 have been executed and evidenced.** This document does not generate a key, install packages, access Colab, touch the production DB, or upload any file.
