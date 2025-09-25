import os
import requests
import msal
from tqdm import tqdm

# ====== CONFIGURAÇÃO ======
CLIENT_ID = "779bbd7d-51f8-431d-8db4-68fa2d4ba743"
TENANT = "704036a0-4ad5-48f5-9d1f-bd1cef6ae38a"  # ou o ID do diretório se for fixo
SCOPES = ["Files.ReadWrite.All"]  # <- sem offline_access


LOCAL_FILE = r"D:\\tds\\python\\arquivo_1.csv"

# Caminho no OneDrive (use o nome EXATO da pasta como aparece)
ONEDRIVE_PATH = (
    "OneDrive - Bonanza Supermercados/"
    "RPA - ARQUIVOS/"
    "OneDrive - Bonanza Supermercados/"
    "RPA - ARQUIVOS/"
    "T.I/integracao/ap_bebidas"
)

GRAPH = "https://graph.microsoft.com/v1.0"

# ====== AUTENTICAÇÃO ======
def get_token():
    app = msal.PublicClientApplication(
        CLIENT_ID, authority=f"https://login.microsoftonline.com/{TENANT}"
    )

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError("Falha ao iniciar device flow.")
    print(flow["message"])  # siga instruções (https://microsoft.com/devicelogin)
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError("Erro ao autenticar: " + result.get("error_description", ""))
    return result["access_token"]

# ====== PASTAS ======
def ensure_folder_by_path(access_token, path):
    """
    Garante que a pasta exista no OneDrive. Cria se não existir.
    Retorna o JSON da pasta final.
    """
    parts = path.strip("/").split("/")
    current = {"id": "root"}

    for i, part in enumerate(parts):
        sub_path = "/".join(parts[: i + 1])
        url = f"{GRAPH}/me/drive/root:/{sub_path}"
        resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})

        if resp.status_code == 200:
            current = resp.json()
            continue
        elif resp.status_code == 404:
            # cria pasta dentro da atual
            parent_id = current["id"]
            url_create = f"{GRAPH}/me/drive/items/{parent_id}/children"
            body = {
                "name": part,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "fail",
            }
            resp_create = requests.post(
                url_create,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp_create.raise_for_status()
            current = resp_create.json()
        else:
            raise RuntimeError(f"Erro ao buscar pasta: {resp.status_code} {resp.text}")

    return current

# ====== UPLOAD ======
def upload_file(access_token, local_path, folder_item):
    filename = os.path.basename(local_path)
    file_size = os.path.getsize(local_path)

    # Usa upload simples (até 250MB). Se for maior, precisaria de upload em partes.
    upload_url = f"{GRAPH}/me/drive/items/{folder_item['id']}:/{filename}:/content"

    with open(local_path, "rb") as f, tqdm(
        total=file_size, unit="B", unit_scale=True, desc="Enviando"
    ) as pbar:
        resp = requests.put(
            upload_url, headers={"Authorization": f"Bearer {access_token}"}, data=f
        )
        pbar.update(file_size)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Erro no upload: {resp.status_code} {resp.text}")
    return resp.json()

# ====== MAIN ======
if __name__ == "__main__":
    token = get_token()
    pasta = ensure_folder_by_path(token, ONEDRIVE_PATH)
    print("Pasta confirmada:", pasta["name"], "| ID:", pasta["id"])

    info = upload_file(token, LOCAL_FILE, pasta)
    print("Upload concluído! Arquivo:", info["name"], "| ID:", info["id"])
