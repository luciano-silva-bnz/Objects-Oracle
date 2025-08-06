import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import requests
import json
from pathlib import Path

# Configurações de API
API_AUTH_URL = "https://bonanza150977.consinco.cloudtotvs.com.br:8343/api/v1/auth/login"
API_TOKEN_URL = "https://bonanza150977.consinco.cloudtotvs.com.br:8343/api/v1/auth/token"
API_COMPANY_ID = "1"
API_URL_BASE = "https://bonanza150977.consinco.cloudtotvs.com.br:8343/CadastrosEstruturaisAPI/api/v1/Pessoa"
application_path = Path(__file__).parent
TOKEN_STORAGE_FILE = application_path / "token_storage.json"

# Gerenciamento de token
def salvar_tokens(data: dict):
    with open(TOKEN_STORAGE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def carregar_refresh_token() -> str | None:
    if TOKEN_STORAGE_FILE.exists():
        try:
            d = json.loads(TOKEN_STORAGE_FILE.read_text())
            return d.get('refreshToken') or d.get('refresh_token')
        except json.JSONDecodeError:
            return None
    return None

def obter_token_com_credenciais(username: str, password: str) -> dict:
    payload = {'company': int(API_COMPANY_ID), 'username': username, 'password': password}
    headers = {'Content-Type': 'application/json'}
    resp = requests.post(API_AUTH_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    token_data = resp.json()
    salvar_tokens(token_data)
    return token_data

def renovar_token(refresh_token: str) -> dict | None:
    payload = {'grant_type': 'refresh_token', 'refresh_token': refresh_token}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    try:
        resp = requests.post(API_TOKEN_URL, data=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        token_data = resp.json()
        salvar_tokens(token_data)
        return token_data
    except requests.RequestException:
        return None

class TotvsAPI:
    def __init__(self):
        self.access_token = None
        self.refresh_token = carregar_refresh_token()

    def autenticar(self, username: str, password: str):
        try:
            data = obter_token_com_credenciais(username, password)
            self.access_token = data.get('accessToken') or data.get('access_token')
            self.refresh_token = data.get('refreshToken') or data.get('refresh_token')
            return True, ''
        except Exception as e:
            return False, str(e)

    def _garantir_token(self) -> bool:
        if not self.access_token and self.refresh_token:
            data = renovar_token(self.refresh_token)
            if data:
                self.access_token = data.get('accessToken') or data.get('access_token')
                self.refresh_token = data.get('refreshToken') or data.get('refresh_token')
        return bool(self.access_token)

    def consultar_pessoa(self, num: str, dig: str) -> tuple[int | None, str | None]:
        if not self._garantir_token():
            return None, None
        params = {'numeroCPFCNPJ': num, 'digitoCPFCNPJ': dig}
        headers = {"Authorization": f"Bearer {self.access_token}"}
        resp = requests.get(API_URL_BASE, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            items = resp.json().get('items', [])
            if items:
                first = items[0]
                return first.get('idPessoa'), first.get('status')
        return None, None

    def incluir_pessoa(self, payload: dict) -> requests.Response:
        if not self._garantir_token():
            raise Exception('Token inválido')
        headers = {"Authorization": f"Bearer {self.access_token}"}
        return requests.post(API_URL_BASE, json=payload, headers=headers, timeout=30)

class App:
    def __init__(self, root):
        self.root = root
        self.api = TotvsAPI()
        self.df = pd.DataFrame()
        self.filter_key = ''
        self.import_path = None
        self._build_login()

    def _build_login(self):
        self.root.withdraw()
        win = tk.Toplevel(self.root)
        win.title('Login TOTVS-CONSINCO')
        win.protocol('WM_DELETE_WINDOW', self.root.destroy)
        win.geometry('300x180')
        self._center(win, 300, 180)

        tk.Label(win, text='Usuário:').pack(pady=5)
        self.ent_user = tk.Entry(win)
        self.ent_user.pack()
        tk.Label(win, text='Senha:').pack(pady=5)
        self.ent_pass = tk.Entry(win, show='*')
        self.ent_pass.pack()
        tk.Button(win, text='Entrar', command=lambda: self._do_login(win)).pack(pady=10)
        win.grab_set(); win.focus_force()

    def _do_login(self, win):
        ok, msg = self.api.autenticar(self.ent_user.get(), self.ent_pass.get())
        if not ok:
            messagebox.showerror('Erro de Login', msg)
        else:
            win.destroy()
            self.root.deiconify()
            self._build_ui()

    def _center(self, win, w, h):
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x, y = (sw-w)//2, (sh-h)//2
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(pady=5, fill='x')
        self.lbl_stats = tk.Label(top, text='Total: 0 | Selecionados: 0 | Cadastrados: 0')
        self.lbl_stats.pack(side='left', padx=10)
        tk.Button(top, text='Importar Planilha', command=self.importar).pack(side='left', padx=5)
        self.ent_filter = tk.Entry(top)
        self.ent_filter.pack(side='left', padx=5)
        tk.Button(top, text='Filtrar', command=self.aplicar_filtro).pack(side='left', padx=5)
        tk.Button(top, text='Selecionar/Desmarcar Todos', command=self.selecionar_todos).pack(side='left', padx=5)
        tk.Button(top, text='Cadastrar Selecionados', command=self.cadastrar).pack(side='left', padx=5)

        frame = tk.Frame(self.root)
        frame.pack(expand=True, fill='both')
        sb = ttk.Scrollbar(frame, orient='vertical')
        sb.pack(side='right', fill='y')
        self.tree = ttk.Treeview(frame, show='headings', selectmode='none', yscrollcommand=sb.set)
        self.tree.pack(expand=True, fill='both')
        sb.config(command=self.tree.yview)
        self.tree.bind('<Double-1>', self._toggle)

        log_frame = tk.Frame(self.root)
        log_frame.pack(fill='x')
        self.txt = tk.Text(log_frame, height=8)
        self.txt.pack(side='left', expand=True, fill='x')
        log_scroll = ttk.Scrollbar(log_frame, orient='vertical', command=self.txt.yview)
        log_scroll.pack(side='right', fill='y')
        self.txt.config(yscrollcommand=log_scroll.set)

    def importar(self):
        file = filedialog.askopenfilename(filetypes=[('Excel', '*.xlsx')])
        if not file:
            return
        self.import_path = Path(file)
        self.df = pd.read_excel(file, dtype=str).fillna('')
        for col in ['Selecionado', 'Status', 'idPessoa', 'ErroDetalhes']:
            self.df[col] = ''
        self.filter_key = ''
        self._refresh(self.df)

    def aplicar_filtro(self):
        if self.df.empty:
            messagebox.showwarning('Aviso', 'Importe antes de filtrar')
            return
        k = self.ent_filter.get().strip().lower()
        self.filter_key = k
        df_show = self.df if not k else self.df[self.df['RA_CIC'].str.contains(k) | self.df['RA_NOME'].str.lower().str.contains(k)]
        self._refresh(df_show)

    def selecionar_todos(self):
        if self.df.empty:
            return
        df_subset = self.df if not self.filter_key else self.df[self.df['RA_CIC'].str.contains(self.filter_key) | self.df['RA_NOME'].str.lower().str.contains(self.filter_key)]
        all_sel = all(df_subset['Selecionado'] == '1')
        self.df.loc[df_subset.index, 'Selecionado'] = '' if all_sel else '1'
        self._refresh(df_subset)

    def _toggle(self, event):
        if self.tree.identify_column(event.x) != '#1':
            return
        row = self.tree.identify_row(event.y)
        if not row:
            return
        idx = int(row)
        val = self.df.at[idx, 'Selecionado']
        self.df.at[idx, 'Selecionado'] = '' if val == '1' else '1'
        df_show = self.df if not self.filter_key else self.df[self.df['RA_CIC'].str.contains(self.filter_key) | self.df['RA_NOME'].str.lower().str.contains(self.filter_key)]
        self._refresh(df_show)

    def _refresh(self, df):
        self.tree.delete(*self.tree.get_children())
        cols = ['Selecionado'] + [c for c in df.columns if c not in ['Selecionado', 'Status', 'idPessoa', 'ErroDetalhes']]
        self.tree['columns'] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100)
        for idx, row in df.iterrows():
            mark = '✅' if row['Selecionado'] == '1' else '☐'
            vals = [mark] + [row[c] for c in cols[1:]]
            self.tree.insert('', 'end', iid=idx, values=vals)
        self._stats()

    def _stats(self):
        total = len(self.df)
        sel = sum(self.df['Selecionado'] == '1')
        cad = sum(self.df['Status'] == 'Sucesso') + sum(self.df['Status'] == 'Existente')
        self.lbl_stats.config(text=f'Total: {total} | Selecionados: {sel} | Cadastrados: {cad}')

    def montar_payload(self, row):
        nome = row['RA_NOME']
        fantasia = nome.split(' ')[0]
        sexo = row.get('RA_SEXO', '')
        ddd = row.get('RA_DDDCELU', '')
        tel = row.get('TELEFONE_FORMATADO', '')
        cep = row.get('RA_CEP', '').replace('.0', '') or None
        uf_cidade = str(row.get('RA_ESTADO', '')).strip() or None
        cpf = row['RA_CIC'].zfill(11)
        num, dig = cpf[:-2], cpf[-2:]
        return {
            'nomeRazaoSocial': nome,
            'fantasia': fantasia,
            'tipo': 'F',
            'status': 'A',
            'sexo': sexo or None,
            'InscricaoEstadualRG': row.get('RA_RG', '') or None,
            'cep': cep,
            'telefoneDDD1': ddd or None,
            'telefoneNumero1': tel or None,
            'numeroCPFCNPJ': num,
            'digitoCPFCNPJ': dig,
            'ufCidade': uf_cidade,
            'numeroLogradouro': row.get('RA_NUMENDE', '').replace('.0', '') or None
        }

    def cadastrar(self):
        self.txt.delete(1.0, tk.END)
        df_sel = self.df[self.df['Selecionado'] == '1']
        count_sel = len(df_sel)
        count_s = 0
        for idx, row in df_sel.iterrows():
            cpf = row['RA_CIC'].zfill(11)
            num, dig = cpf[:-2], cpf[-2:]
            idpessoa, status_api = self.api.consultar_pessoa(num, dig)
            if idpessoa is not None:
                self.df.at[idx, 'idPessoa'] = idpessoa
                self.df.at[idx, 'Status'] = status_api or 'Existente'
                count_s += 1
                self.txt.insert(tk.END, f"[EXISTENTE] {row['RA_NOME']} -> id {idpessoa}, status {status_api}\n")
                continue
            pl = self.montar_payload(row)
            r = self.api.incluir_pessoa(pl)
            if r.status_code == 201:
                new_id = r.json().get('idPessoa')
                self.df.at[idx, 'idPessoa'] = new_id
                self.df.at[idx, 'Status'] = 'Sucesso'
                count_s += 1
                self.txt.insert(tk.END, f"[OK] {row['RA_NOME']} -> id {new_id}\n")
            else:
                self.df.at[idx, 'ErroDetalhes'] = r.text
                self.df.at[idx, 'Status'] = f"Erro {r.status_code}" 
                self.txt.insert(tk.END, f"[ERRO] {row['RA_NOME']} -> {r.status_code} {r.text}\n")
        messagebox.showinfo('Integração', f"Total selecionados: {count_sel}\nProcessados: {count_s}")
        if self.import_path:
            out_file = self.import_path.parent / f"resultado_{self.import_path.stem}.xlsx"
            df_export = self.df.loc[df_sel.index, ['RA_CIC', 'RA_NOME', 'idPessoa', 'Status', 'ErroDetalhes']]
            df_export.to_excel(out_file, index=False)
            self.txt.insert(tk.END, f"[INFO] Resultado exportado em {out_file}\n")
        df_show = self.df if not self.filter_key else self.df[self.df['RA_CIC'].str.contains(self.filter_key) | self.df['RA_NOME'].str.lower().str.contains(self.filter_key)]
        self._refresh(df_show)

if __name__ == '__main__':
    root = tk.Tk()
    root.title('Cadastro de Pessoas(F) Consinco')
    root.geometry('1000x700')
    App(root)
    root.mainloop()
