# Integrity Guard — offline prototype

Python 3.9+ and OpenSSL on PATH are required. Use trusted release files and store the private signing key offline, outside the repository and distributed client. The verifier must receive a trusted public key from an independently authenticated source.

```sh
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out private.pem
openssl pkey -in private.pem -pubout -out public.pem
python Tools/integrity.py create client manifest.json main.exe Data/example.bmd
openssl dgst -sha256 -sign private.pem -out manifest.sig manifest.json
python Tools/integrity.py verify client manifest.json manifest.sig public.pem
```
Replace example paths with actual release files. Exit 0 = listed files verified; 1 = mismatches; 2 = invalid input or verification error. Only explicitly listed files are checked. No automatic sanctions. The tool does not protect against concurrent file changes, rollback to old signed manifests, or a compromised verifier. Use a trusted, non-writable staging directory; runtime enforcement, pinned key, version policy and native DLL integration are future work. Never distribute the private key.
