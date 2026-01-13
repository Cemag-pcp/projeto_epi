from ftplib import FTP
from pathlib import Path

HOST = "ftp.mtps.gov.br"
DIR  = "/portal/fiscalizacao/seguranca-e-saude-no-trabalho/caepi"
FILE = "tgg_export_caepi.zip"

dest = Path.home() / "Downloads" / FILE

ftp = FTP(HOST, timeout=60)
ftp.login()  # anonymous
ftp.cwd(DIR)

with open(dest, "wb") as f:
    ftp.retrbinary(f"RETR {FILE}", f.write, blocksize=1024 * 64)

ftp.quit()

# valida assinatura ZIP (PK)
with open(dest, "rb") as f:
    sig = f.read(2)

print("Salvo em:", dest)
print("Tamanho:", dest.stat().st_size)
print("Assinatura:", sig)
print("OK ZIP?" , sig == b"PK")


import zipfile
from pathlib import Path

zip_path = Path.home() / "Downloads" / "tgg_export_caepi.zip"
destino = Path.home() / "Downloads" / "caepi_extraido"

destino.mkdir(exist_ok=True)

with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(destino)

print("Extraído em:", destino)
