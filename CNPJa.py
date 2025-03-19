import pandas as pd
import http.client
import json
from tkinter import filedialog


def get_company_data(cnpj, api_key):
    conn = http.client.HTTPSConnection("api.cnpja.com")
    payload = ''
    headers = {
        "Authorization": api_key
    }

    conn.request(
        "GET", f"/office/{cnpj}?registrations=BR&registrationsStatus=true&simples=true", payload, headers)

    response = conn.getresponse()
    if response.status == 200:
        return response.read()
    else:
        print(
            f"Erro ao acessar a API para o CNPJ {cnpj}: {response.status} Msg: {response.reason}")
        return None


# L� a planilha Excel com os CNPJs
file = filedialog.askopenfile()
df = pd.read_excel(file.name)

cnpjs = df["cnpj"].tolist()
# Cria uma lista para armazenar os resultados
results = []

# Substitua YOUR_API_KEY pela sua chave de API do CNPJ�
api_key = "9dcf511e-5ccd-4320-9335-3d5fca2b8e4c-2d36a0e0-c63c-41c6-a3ff-35ab13304861"

# Itera sobre os CNPJs na planilha
for cnpj in cnpjs:
    data = get_company_data(cnpj, api_key)
    if data:
        data_dict = json.loads(data.decode("utf-8"))
        data_dict['status'] = data_dict['status']['text']
        data_dict['mainActivity'] = data_dict['mainActivity']['text']
        if len(data_dict.get('emails')) > 0:
            for i in range(len(data_dict.get('emails'))):
                data_dict.get('emails')[i].get('address')
        if len(data_dict.get('sideActivities')) > 0:
            for i in range(len(data_dict.get('sideActivities'))):
                data_dict['sideActivities'] = data_dict.get('sideActivities')[
                    i].get('text')

                registrations = data_dict['registrations']
                state_list = [reg['state'] for reg in registrations]
                number_list = [reg['number'] for reg in registrations]
                enabled_list = [reg['enabled'] for reg in registrations]
                statusDate_list = [reg['statusDate'] for reg in registrations]
                status_text_list = [reg['status']['text']
                                    for reg in registrations]
                type_text_list = [reg['type']['text'] for reg in registrations]

                data_dict['registrationStates'] = state_list
                data_dict['registrationNumbers'] = number_list
                data_dict['registrationEnabled'] = enabled_list
                data_dict['registrationStatusDates'] = statusDate_list
                data_dict['registrationStatusTexts'] = status_text_list
                data_dict['registrationTypeTexts'] = type_text_list

        results.append(data_dict)

# Cria um novo DataFrame com os resultados
results_df = pd.DataFrame(results)

# Salva o novo DataFrame em uma planilha Excel
results_df.to_excel("results.xlsx", index=False)
