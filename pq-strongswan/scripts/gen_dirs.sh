#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

for dir in moon carol
do
  mkdir -p \
    "$ROOT_DIR/$dir/ecdsa" \
    "$ROOT_DIR/$dir/pkcs12" \
    "$ROOT_DIR/$dir/pkcs8" \
    "$ROOT_DIR/$dir/private" \
    "$ROOT_DIR/$dir/pubkey" \
    "$ROOT_DIR/$dir/rsa" \
    "$ROOT_DIR/$dir/x509" \
    "$ROOT_DIR/$dir/x509aa" \
    "$ROOT_DIR/$dir/x509ac" \
    "$ROOT_DIR/$dir/x509ca" \
    "$ROOT_DIR/$dir/x509crl" \
    "$ROOT_DIR/$dir/x509ocsp"
done
