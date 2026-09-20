==================================
``portable-cryptor/`` — AWS↔GCP KMS-portable encryption
==================================

Purpose
=======
Cross-cloud RSA KMS encryption / decryption library. Ciphertexts produced
with **AWS KMS** can be decrypted with **GCP Cloud KMS** (and vice versa)
because both KMS instances are seeded with the **same RSA-4096 key
material** and use ``RSA-OAEP-SHA256`` padding. This is the
disaster-recovery / cross-cloud-migration story for ``gcp_kitt``.

Layout
======
::

    portable-cryptor/
      kms_encrypt_decrypt_esdk.py      # main CLI: aws-encrypt | aws-decrypt | gcp-encrypt | gcp-decrypt
      kms_encrypt_decrypt.py           # legacy KMS wrapper
      rsa_encrypt_decrypt.py           # pure local RSA-OAEP
      generate_rsa_keypair.py          # RSA-4096 key generation
      import_rsa_key.py                # AWS KMS key-import helper
      extract_public_from_private.py   # public-key extraction
      requirements.txt
      key-rotations/                   # version tracking notes

Tech
====
Python 3.10+, ``cryptography``, ``boto3``, ``google-cloud-kms``.

Function signatures (selected)
==============================
- ``get_aws_kms_client()`` / ``aws_encrypt()`` / ``aws_decrypt()``
- ``get_gcp_kms_client()`` / ``gcp_encrypt()`` / ``gcp_decrypt()``
- ``generate_rsa_keypair()`` / ``save_private_key()`` / ``save_public_key()``
- ``encrypt_with_oaep_sha256()`` / ``decrypt_with_oaep_sha256()``

Reference key material
======================
- AWS KMS: ``arn:aws:kms:us-east-2:412306530531:key/e51a3e79-3565-43ac-a167-ee90b5842072``
- GCP KMS: ``cloud-conductor/us-east4/aks/aks-gcp-03:v3``

Key operational commands
========================
.. code-block:: bash

    # AWS encrypt
    python3 kms_encrypt_decrypt_esdk.py aws-encrypt \
      --aws-key-id <arn> \
      --aws-profile Administrator-412306530531 \
      --aws-region us-east-2 \
      "plaintext"

    # GCP decrypt of an AWS-produced ciphertext
    python3 kms_encrypt_decrypt_esdk.py gcp-decrypt \
      --gcp-project cloud-conductor \
      --gcp-location us-east4 \
      --gcp-keyring aks --gcp-key aks-gcp-03 --gcp-version 3 \
      "<base64-ciphertext>"

Gotchas
=======
- AWS and GCP **must** hold identical key material; a version mismatch is
  silent until decrypt fails.
- AWS profile requires SSO login first
  (``aws sso login --profile Administrator-412306530531``).
- Ciphertexts are base64; quoting matters in shells when piping through
  command substitution.
