# Creates the local deno-ibmi CA and the IBMI server certificate (PASE openssl)
exec > /tmp/rustpoc/tls.log 2>&1
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
T=/QOpenSys/opt/denoibmi/tls
mkdir -p $T && cd $T
which openssl; openssl version
# local deno-ibmi CA (10 years), then IBMI server certificate (2 years), SAN name + IP
[ -f ca.key ] || openssl req -x509 -newkey rsa:3072 -sha256 -days 3650 -nodes -keyout ca.key -out ca.crt -subj "/CN=deno-ibmi CA locale"
cat > serveur.cnf <<'CNF'
[req]
distinguished_name = dn
prompt = no
[dn]
O = deno-ibmi
CN = ibmi
[ext]
subjectAltName = DNS:ibmi, DNS:IBMI, DNS:localhost, IP:192.0.2.82, IP:127.0.0.1
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
CNF
openssl req -newkey rsa:2048 -sha256 -nodes -keyout serveur.key -out serveur.csr -config serveur.cnf
openssl x509 -req -in serveur.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 730 -sha256 -extfile serveur.cnf -extensions ext -out serveur.crt
openssl x509 -in serveur.crt -noout -subject -issuer -enddate -ext subjectAltName
# PKCS#12 for a possible import into DCM (Apache)
openssl pkcs12 -export -inkey serveur.key -in serveur.crt -certfile ca.crt -name deno-ibmi-ibmi -out serveur.p12 -passout pass:denoibmi
chown DENOAPP serveur.key; chmod 600 serveur.key ca.key; chmod 644 serveur.crt ca.crt
ls -l $T
echo DONE
