import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import requests
from requests import Session
import json
from pathlib import Path
import re

# ========== CONFIGURAÇÕES DOS 3 BANCOS ORACLE ==========
DBS = [
    {
        "USER": "BonanzaPRDREAD",
        "PASS": "eajsy84153NWYJU@!",
        "DSN": "45.6.153.115:2070/C1PCXH_180377_P_high.paas.oracle.com",
        "QUERY": """
            SELECT
                r.ra_filial,
                r.ra_mat,
                r.ra_nome,
                r.ra_nasc,
                r.ra_cic,
                r.ra_codfunc,
                r.ra_proces,
                r.ra_msblql,
                r.ra_estado,
                r.ra_municip,
                r.ra_bairro,
                r.ra_enderec,
                r.ra_numende,
                r.ra_sexo,
                r.ra_cep,
                r.ra_dddcelu,
                r.ra_numcelu,
                r.ra_telefon,
                r.ra_rg,
                CASE
                    WHEN TRIM(r.ra_numcelu) IS NULL OR TRIM(r.ra_numcelu) = '' THEN NULL
                    WHEN length(trim(regexp_replace(r.ra_numcelu, '[^0-9]', ''))) < 8 THEN NULL
                    ELSE
                        CASE 
                            WHEN length(regexp_replace(r.ra_numcelu, '[^0-9]', '')) = 8 THEN
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 1, 4) || '-' ||
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 5, 4)
                            WHEN length(regexp_replace(r.ra_numcelu, '[^0-9]', '')) = 9 THEN
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 1, 5) || '-' ||
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 6, 4)
                            ELSE regexp_replace(r.ra_numcelu, '[^0-9]', '')
                        END
                END AS telefone_formatado
            FROM u_c1pcxh_pr.sra010 r
            WHERE r.ra_demissa <> ' '
              AND r.d_e_l_e_t_ = ' '
              AND r.ra_demissa >= '20150101'
              AND r.ra_rescrai NOT IN ('30', '31')
              AND {in_clause}
            ORDER BY r.ra_filial
        """
    }
    ,
    {
        "USER": "MultiPRDREAD",
        "PASS": "fmglw49538EIRWK?!",
        "DSN": "45.6.153.115:2020/C1PCXH_180376_P_high.paas.oracle.com",
        "QUERY": """
            SELECT
                r.ra_filial,
                r.ra_mat,
                r.ra_nome,
                r.ra_nasc,
                r.ra_cic,
                r.ra_codfunc,
                r.ra_proces,
                r.ra_msblql,
                r.ra_estado,
                r.ra_municip,
                r.ra_bairro,
                r.ra_enderec,
                r.ra_numende,
                r.ra_sexo,
                r.ra_cep,
                r.ra_dddcelu,
                r.ra_numcelu,
                r.ra_telefon,
                r.ra_rg,
                CASE
                    WHEN TRIM(r.ra_numcelu) IS NULL OR TRIM(r.ra_numcelu) = '' THEN NULL
                    WHEN length(trim(regexp_replace(r.ra_numcelu, '[^0-9]', ''))) < 8 THEN NULL
                    ELSE
                        CASE 
                            WHEN length(regexp_replace(r.ra_numcelu, '[^0-9]', '')) = 8 THEN
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 1, 4) || '-' ||
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 5, 4)
                            WHEN length(regexp_replace(r.ra_numcelu, '[^0-9]', '')) = 9 THEN
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 1, 5) || '-' ||
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 6, 4)
                            ELSE regexp_replace(r.ra_numcelu, '[^0-9]', '')
                        END
                END AS telefone_formatado
            FROM u_c1pcxh_pr.sra020 r
            WHERE r.ra_demissa <> ' '
              AND r.d_e_l_e_t_ = ' '
              AND r.ra_demissa >= '20150101'
              AND r.ra_rescrai NOT IN ('30', '31')
              AND {in_clause}
            ORDER BY r.ra_filial
        """
    }
    ,
    {
        "USER": "AliancaPRDREAD",
        "PASS": "nrvkj02374WZTIE!@",
        "DSN": "45.6.153.115:2120/C1PCXH_180375_P_medium.paas.oracle.com",
        "QUERY": """
            SELECT
                r.ra_filial,
                r.ra_mat,
                r.ra_nome,
                r.ra_nasc,
                r.ra_cic,
                r.ra_codfunc,
                r.ra_proces,
                r.ra_msblql,
                r.ra_estado,
                r.ra_municip,
                r.ra_bairro,
                r.ra_enderec,
                r.ra_numende,
                r.ra_sexo,
                r.ra_cep,
                r.ra_dddcelu,
                r.ra_numcelu,
                r.ra_telefon,
                r.ra_rg,
                CASE
                    WHEN TRIM(r.ra_numcelu) IS NULL OR TRIM(r.ra_numcelu) = '' THEN NULL
                    WHEN length(trim(regexp_replace(r.ra_numcelu, '[^0-9]', ''))) < 8 THEN NULL
                    ELSE
                        CASE 
                            WHEN length(regexp_replace(r.ra_numcelu, '[^0-9]', '')) = 8 THEN
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 1, 4) || '-' ||
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 5, 4)
                            WHEN length(regexp_replace(r.ra_numcelu, '[^0-9]', '')) = 9 THEN
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 1, 5) || '-' ||
                                substr(regexp_replace(r.ra_numcelu, '[^0-9]', ''), 6, 4)
                            ELSE regexp_replace(r.ra_numcelu, '[^0-9]', '')
                        END
                END AS telefone_formatado
            FROM u_c1pcxh_pr.sra040 r
            WHERE r.ra_demissa <> ' '
              AND r.d_e_l_e_t_ = ' '
              AND r.ra_demissa >= '20150101'
              AND r.ra_rescrai NOT IN ('30', '31')
              AND {in_clause}
            ORDER BY r.ra_filial
        """
    }
]

# ========== API CONSINCO ==========
API_AUTH_URL = "https://bonanza150976.consinco.cloudtotvs.com.br:8343/api/v1/auth/login"
API_TOKEN_URL = "https://bonanza150976.consinco.cloudtotvs.com.br:8343/api/v1/auth/token"
API_COMPANY_ID = "1"
API_URL_BASE = "https://bonanza150976.consinco.cloudtotvs.com.br:8343/CadastrosEstruturaisAPI/api/v1/Pessoa"
application_path = Path(__file__).parent
TOKEN_STORAGE_FILE = application_path / "token_storage.json"

# ========== FUNÇÕES AUXILIARES ==========
def normaliza_cpf(cpf):
    s = re.sub(r'\D', '', str(cpf))  # remove tudo que não for número
    return s.zfill(11) if s else None


def prepara_lista_cpfs(texto):
    import re
    # Corrige literais \n e \r\n para quebras de linha reais
    texto = texto.replace('\\n', '\n').replace('\\r', '\r')
    # Remove aspas se o usuário colar junto
    texto = texto.replace("'", "").replace('"', '')
    # Agora divide por qualquer quebra de linha, vírgula, tab ou ponto e vírgula
    linhas = re.split(r'[\n\r,;\t]+', texto)
    cpfs = [normaliza_cpf(c) for c in linhas if normaliza_cpf(c)]
    return [c for c in cpfs if len(c) == 11]


def consulta_banco(user, password, dsn, query):
    import oracledb
    conn = oracledb.connect(user=user, password=password, dsn=dsn)
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ========== TOKEN TOTVS ==========
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
    """Cliente simples para comunicação com a API TOTVS."""

    def __init__(self):
        self.session: Session = Session()
        self.access_token: str | None = None
        self.refresh_token: str | None = carregar_refresh_token()

    def autenticar(self, username: str, password: str):
        try:
            data = obter_token_com_credenciais(username, password)
            self.access_token = data.get('accessToken') or data.get('access_token')
            self.refresh_token = data.get('refreshToken') or data.get('refresh_token')
            return True, ''
        except Exception as e:
            return False, str(e)

    def _garantir_token(self) -> bool:
        """Garante que haja um token de acesso válido."""
        if not self.access_token and self.refresh_token:
            data = renovar_token(self.refresh_token)
            if data:
                self.access_token = data.get('accessToken') or data.get('access_token')
                self.refresh_token = data.get('refreshToken') or data.get('refresh_token')
        return bool(self.access_token)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Executa uma requisição autenticada, renovando o token em caso de 401."""
        if not self._garantir_token():
            raise Exception('Token inválido')
        headers = kwargs.pop('headers', {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        resp = self.session.request(method, url, headers=headers, **kwargs)
        if resp.status_code == 401 and self.refresh_token:
            data = renovar_token(self.refresh_token)
            if data:
                self.access_token = data.get('accessToken') or data.get('access_token')
                self.refresh_token = data.get('refreshToken') or data.get('refresh_token')
                headers["Authorization"] = f"Bearer {self.access_token}"
                resp = self.session.request(method, url, headers=headers, **kwargs)
        return resp

    def consultar_pessoa(self, num: str, dig: str) -> tuple[int | None, str | None]:
        if not self._garantir_token():
            return None, None
        params = {'numeroCPFCNPJ': num, 'digitoCPFCNPJ': dig}
        resp = self._request('GET', API_URL_BASE, params=params, timeout=30)
        if resp.status_code == 200:
            items = resp.json().get('items', [])
            if items:
                first = items[0]
                return first.get('idPessoa'), first.get('status')
        return None, None

    def incluir_pessoa(self, payload: dict) -> requests.Response:
        return self._request('POST', API_URL_BASE, json=payload, timeout=30)

# =================== BUSCA CPF MULTIBANCO ====================
class BuscaCPFWindow(tk.Toplevel):
    def __init__(self, master, on_confirm):
        super().__init__(master)
        self.title("Consulta Multibanco por Lista de CPF")
        self.geometry("680x480")
        self.resizable(False, False)
        self.on_confirm = on_confirm

        # NOVO: Fica sempre no topo e centraliza na tela
        self.attributes('-topmost', True)
        self.after(200, lambda: self.attributes('-topmost', False))
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"+{x}+{y}")

        tk.Label(self, text="Cole ou digite CPFs (um por linha, qualquer formato):").pack(pady=5)
        self.txt_cpfs = tk.Text(self, height=7, width=85)
        self.txt_cpfs.pack()

        frame_btns = tk.Frame(self)
        frame_btns.pack(pady=3)
        tk.Button(frame_btns, text="Importar Excel...", command=self.importar_excel).pack(side="left", padx=3)
        tk.Button(frame_btns, text="Buscar em Bancos", command=self.buscar_bancos).pack(side="left", padx=3)
        self.lbl_status = tk.Label(self, text="")
        self.lbl_status.pack()

        self.tree = ttk.Treeview(self, show="headings")
        self.tree.pack(expand=True, fill="both", pady=5)
        self.scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scroll_y.set)
        self.scroll_y.pack(side="right", fill="y")
        self.df_resultado = pd.DataFrame()

        self.btn_usar = tk.Button(self, text="Usar estes dados na tela principal", command=self.usar_dados, state="disabled")
        self.btn_usar.pack(pady=3)
        self.attributes('-topmost', True)
        

    def importar_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.read_excel(path)
            col_cpf = next((c for c in df.columns if 'cpf' in c.lower() or 'cic' in c.lower()), df.columns[0])
            cpfs = df[col_cpf].astype(str).tolist()
            self.txt_cpfs.delete(1.0, tk.END)
            self.txt_cpfs.insert(tk.END, "\n".join(cpfs))
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e))

    def buscar_bancos(self):
        texto = self.txt_cpfs.get(1.0, tk.END)
        lista_cpfs = prepara_lista_cpfs(texto)
        print("CPFs:", lista_cpfs)       # ['13695196807', '06076030461', ...]
        if not lista_cpfs:
            messagebox.showwarning("Atenção", "Nenhum CPF válido informado.")
            return

        self.lbl_status.config(text=f"{len(lista_cpfs)} CPFs preparados para busca... Aguarde.")
        self.update_idletasks()

        in_clause = ",".join(f"'{c}'" for c in lista_cpfs)  # cada CPF vira '00000000000'
        in_clause_sql = f"r.ra_cic IN ({in_clause})"
        print("IN SQL:", in_clause_sql)  # r.ra_cic IN ('13695196807','06076030461',...)
        resultados = []

        for idx, db in enumerate(DBS, 1):
            try:
                query = db["QUERY"].format(in_clause=in_clause_sql)
                df = consulta_banco(db["USER"], db["PASS"], db["DSN"], query)
                df['BANCO_ORIGEM'] = f"Banco {idx}"
                resultados.append(df)
            except Exception as e:
                messagebox.showerror("Erro Banco", f"Erro ao consultar Banco {idx}: {e}")

        if resultados:
            df_final = pd.concat(resultados, ignore_index=True)
            self.show_dataframe(df_final)
            self.df_resultado = df_final.copy()
            self.lbl_status.config(text=f"Busca finalizada. Registros encontrados: {len(df_final)}")
            self.btn_usar.config(state="normal")
        else:
            self.lbl_status.config(text="Nenhum dado retornado dos bancos.")
            self.btn_usar.config(state="disabled")

    def show_dataframe(self, df):
        self.tree.delete(*self.tree.get_children())
        self.tree['columns'] = list(df.columns)
        for c in df.columns:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120)
        for _, row in df.iterrows():
            self.tree.insert('', 'end', values=list(row))

    def usar_dados(self):
        if self.df_resultado.empty:
            messagebox.showwarning("Atenção", "Nenhum dado para usar.")
            return
        self.on_confirm(self.df_resultado)
        self.destroy()

# ======================= APP PRINCIPAL =======================
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
        btn_entrar = tk.Button(win, text='Entrar', command=lambda: self._do_login(win))
        btn_entrar.pack(pady=10)
        win.grab_set()
        win.focus_force()
        self.ent_pass.bind('<Return>', lambda event: self._do_login(win))
        self.ent_user.bind('<Return>', lambda event: self.ent_pass.focus_set())


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
        # --- Botão novo ---
        tk.Button(top, text='Buscar Dados Bancos', command=self.abrir_janela_busca_cpfs).pack(side='left', padx=5)
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
            try:
                r = self.api.incluir_pessoa(pl)
            except Exception as e:
                self.df.at[idx, 'ErroDetalhes'] = str(e)
                self.df.at[idx, 'Status'] = 'Erro'
                self.txt.insert(tk.END, f"[ERRO] {row['RA_NOME']} -> {e}\n")
                continue
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

    def abrir_janela_busca_cpfs(self):
        def integrar_banco(df_encontrado):
            self.df = df_encontrado.copy().fillna('').astype(str)
            for col in ['Selecionado', 'Status', 'idPessoa', 'ErroDetalhes']:
                if col not in self.df.columns:
                    self.df[col] = ''
            self.filter_key = ''
            self._refresh(self.df)
            messagebox.showinfo("Importação", f"{len(self.df)} registros trazidos dos bancos e prontos para cadastro!")

        BuscaCPFWindow(self.root, on_confirm=integrar_banco)

if __name__ == '__main__':
    root = tk.Tk()
    root.title('Cadastro de Pessoas(F) Consinco')
    root.geometry('1000x700')
    App(root)
    # Centralizar após construir toda a interface
    root.update_idletasks()
    w = root.winfo_width() or 1000
    h = root.winfo_height() or 700
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.mainloop()

