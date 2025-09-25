# -*- coding: utf-8 -*-
# Validador de Impressora Godex — "Aguarde..." + progressbar, "Ver detalhes" em texto (linhas)
# Sem mostrar a sequência no status | Sem quadrados brancos | Texto alinhado à esquerda

import tkinter as tk
from tkinter import ttk
import subprocess
import json
import os
import datetime
import threading
import ctypes, ctypes.wintypes as wt

# ======= Configurações =======
KEYWORD_BPX = "bpx"
SHARE_TARGET = "MB"        # nome do compartilhamento da impressora
PRINTER_NAME = "MB"        # nome lógico instalado no Windows
CHECK_INTERVAL_MS = 5000   # 5s
CMD_TIMEOUT_SEC = 8        # timeout p/ comandos externos

# Paleta
GREEN = "#16a34a"
RED   = "#dc2626"
GRAY  = "#374151"
FG    = "#ffffff"

# ======= Estado global =======
appcontroller_executado = False
sequencia_iniciada = False
tentou_remapear_lpt1 = False
probe_in_progress = False
details_visible = True

res_def_ok = res_modo_ok = res_calib_ok = None
cur_driver_ok = cur_comp_ok = cur_emul_ok = None

last_error_text = ""
last_tipo_text = "..."
last_check_time = "..."

# ======== Spooler RAW ========
winspool = ctypes.WinDLL("winspool.drv")
PH = wt.HANDLE
OpenPrinter = winspool.OpenPrinterW
ClosePrinter = winspool.ClosePrinter
StartDocPrinter = winspool.StartDocPrinterW
EndDocPrinter = winspool.EndDocPrinter
StartPagePrinter = winspool.StartPagePrinter
EndPagePrinter = winspool.EndPagePrinter
WritePrinter = winspool.WritePrinter

class DOC_INFO_1(ctypes.Structure):
    _fields_ = [("pDocName", wt.LPWSTR),
                ("pOutputFile", wt.LPWSTR),
                ("pDatatype",  wt.LPWSTR)]

def send_raw_to_printer(printer_name: str, raw: bytes) -> bool:
    hPrinter = PH()
    if not OpenPrinter(printer_name, ctypes.byref(hPrinter), None):
        return False
    try:
        di = DOC_INFO_1("RAW Job", None, "RAW")
        if StartDocPrinter(hPrinter, 1, ctypes.byref(di)) == 0:
            return False
        try:
            if not StartPagePrinter(hPrinter):
                return False
            written = wt.DWORD(0)
            ok = WritePrinter(hPrinter, raw, len(raw), ctypes.byref(written))
            EndPagePrinter(hPrinter)
            return bool(ok and written.value == len(raw))
        finally:
            EndDocPrinter(hPrinter)
    finally:
        ClosePrinter(hPrinter)

# ======== Comandos ========
FACTORY_DEFAULTS = b"^Z\r\n"
MODE_TT          = b"^AT\r\n"
MODE_DT          = b"^AD\r\n"
CALIB_SENSOR     = b"~S,SENSOR\r\n"  # <-- SOMENTE SENSOR (sem fallback)

# ======== Config %APPDATA%\Godex\modo_impressao.cfg ========
def cfg_path():
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(appdata, "Godex")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "modo_impressao.cfg")

def garantir_cfg_e_ler_tipo():
    path = cfg_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Godex BPX - Configuração de Modo de Impressão\n")
            f.write("# TipoDeImpressao = 1  # 1 = Transferência térmica (^AT)\n")
            f.write("# TipoDeImpressao = 2  # 2 = Térmica direta (^AD)\n")
            f.write("TipoDeImpressao = 1\n")
        return 1, path

    valor = 1
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or s.startswith(";"):
                    continue
                if "=" in s:
                    k, v = s.split("=", 1)
                    if k.strip().lower() == "tipodeimpressao":
                        try:
                            valor = int(v.strip())
                        except:
                            valor = 1
                        break
    except:
        valor = 1
    if valor not in (1, 2):
        valor = 1
    return valor, path

def comando_modo_impressao(tipo):
    return MODE_TT if tipo == 1 else MODE_DT

# ======== Utilitários ========
def run_cmd(cmd, timeout=CMD_TIMEOUT_SEC):
    try:
        cp = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout
        )
        return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return 1, "", f"Timeout ({timeout}s) em: {cmd}"
    except Exception as e:
        return 1, "", str(e)

def listar_impressoras_wmi():
    cmd = (
        r'powershell -NoProfile -Command "'
        r'Get-WmiObject Win32_Printer | '
        r'Select Name,WorkOffline,Shared,ShareName | '
        r'ConvertTo-Json -Compress"'
    )
    rc, out, err = run_cmd(cmd)
    if rc != 0 or not out:
        return []
    try:
        data = json.loads(out)
        return data if isinstance(data, list) else [data]
    except Exception:
        return []

def verificar_driver():
    for p in listar_impressoras_wmi():
        name = (p.get("Name") or "")
        if KEYWORD_BPX in name.lower():
            return not bool(p.get("WorkOffline", False))
    return False

def verificar_compartilhamento():
    for p in listar_impressoras_wmi():
        name = (p.get("Name") or "")
        if KEYWORD_BPX in name.lower():
            shared = bool(p.get("Shared", False))
            share_name = (p.get("ShareName") or "").strip()
            return shared and share_name.lower() == SHARE_TARGET.lower()
    return False

def verificar_emulacao():
    expected = f"\\\\{os.environ.get('COMPUTERNAME','').upper()}\\{SHARE_TARGET}"
    rc, out, _ = run_cmd("net use lpt1:")
    return (rc == 0 and expected.lower() in out.lower())

def remapear_emulacao_lpt1():
    run_cmd("net use LPT1: /delete /y")
    run_cmd(r'net use LPT1: "\\%COMPUTERNAME%\MB" /persistent:yes')
    return verificar_emulacao()

# ======== UI helpers ========
def _apply_palette(color):
    try:
        root.tk_setPalette(background=color, foreground=FG,
                           activeBackground=color, activeForeground=FG,
                           highlightColor=color, highlightBackground=color)
    except Exception:
        pass

def set_bg(color):
    _apply_palette(color)
    root.configure(bg=color, highlightthickness=0)
    for w in (lbl_title, lbl_status, btn_toggle, frame_details, lbl_details):
        try:
            w.configure(bg=color, fg=FG, highlightthickness=0, bd=0)
        except Exception:
            pass  # ttk usa tema próprio

def status_info(msg): lbl_status.config(text=msg)

def start_progress():
    if not pb_running[0]:
        progress.start(10); pb_running[0] = True

def stop_progress():
    if pb_running[0]:
        progress.stop(); pb_running[0] = False

def mostrar_falha(msg):
    global last_error_text
    last_error_text = str(msg)
    stop_progress(); set_bg(RED); status_info(f"FALHA: {msg}")
    update_details_text()

def mostrar_sucesso(msg):
    stop_progress(); set_bg(GREEN); status_info(msg)
    update_details_text()

def resetar_resultados_etapas():
    global res_def_ok, res_modo_ok, res_calib_ok
    res_def_ok = res_modo_ok = res_calib_ok = None

def bool_to_text(b, pending_text="..."):
    if b is None: return pending_text
    return "OK" if b else "FALHA"

def update_details_text():
    lines = [
        f"Driver: {bool_to_text(cur_driver_ok)}",
        f"Compartilhamento: {bool_to_text(cur_comp_ok)}",
        f"Emulação LPT1: {bool_to_text(cur_emul_ok)}",
        f"Tipo selecionado: {last_tipo_text}",
        f"Padrões de Fábrica: {bool_to_text(res_def_ok)}",
        f"Modo de Impressão: {bool_to_text(res_modo_ok)}",
        f"Calibração: {bool_to_text(res_calib_ok)}",
        f"Última verificação: {last_check_time if last_check_time else '...'}",
    ]
    if last_error_text:
        lines.append(f"Erro: {last_error_text}")
    lbl_details.config(text="\n".join(lines))

# ======== "Ver detalhes" ========
def toggle_details():
    global details_visible
    details_visible = not details_visible
    if details_visible:
        update_details_text()
        frame_details.pack(padx=12, pady=(4, 12), fill="x")
        btn_toggle.config(text="Ocultar detalhes")
    else:
        frame_details.forget()
        btn_toggle.config(text="Ver detalhes")

# ======== Sequência (threads; status só “Aguarde…”) ========
def etapa_1_factory_defaults():
    def work():
        ok = send_raw_to_printer(PRINTER_NAME, FACTORY_DEFAULTS)
        root.after(0, lambda: etapa_1_done(ok))
    threading.Thread(target=work, daemon=True).start()

def etapa_1_done(ok):
    global res_def_ok
    res_def_ok = bool(ok); update_details_text()
    if not ok: return mostrar_falha("Padrões de Fábrica")
    root.after(5000, etapa_2_modo_impressao)

def etapa_2_modo_impressao():
    tipo, _ = garantir_cfg_e_ler_tipo()
    global last_tipo_text
    last_tipo_text = 'Transferência térmica (^AT)' if tipo == 1 else 'Térmica direta (^AD)'
    update_details_text()
    cmd = comando_modo_impressao(tipo)
    def work():
        ok = send_raw_to_printer(PRINTER_NAME, cmd)
        root.after(0, lambda: etapa_2_done(ok))
    threading.Thread(target=work, daemon=True).start()

def etapa_2_done(ok):
    global res_modo_ok
    res_modo_ok = bool(ok); update_details_text()
    if not ok: return mostrar_falha("Aplicar Modo de Impressão")
    root.after(5000, etapa_3_calibracao)

def etapa_3_calibracao():
    # SOMENTE SENSOR (sem fallback)
    def work():
        ok = send_raw_to_printer(PRINTER_NAME, CALIB_SENSOR)
        root.after(0, lambda: etapa_3_done(ok))
    threading.Thread(target=work, daemon=True).start()

def etapa_3_done(ok):
    global res_calib_ok
    res_calib_ok = bool(ok); update_details_text()
    if not ok: return mostrar_falha("Calibração")
    root.after(5000, abrir_consinco)

def abrir_consinco():
    if res_def_ok and res_modo_ok and res_calib_ok:
        def work():
            try:
                subprocess.Popen(
                    r'start appcontroller.exe -h bonanza150976.consinco.cloudtotvs.com.br -c',
                    cwd=r'C:\Program Files (x86)\graphon\appcontroller',
                    shell=True
                )
                root.after(0, lambda: mostrar_sucesso("Tudo OK — Abrindo Consinco..."))
            except Exception as e:
                root.after(0, lambda: mostrar_falha(f"Inicializar Consinco ({e})"))
        threading.Thread(target=work, daemon=True).start()
    else:
        mostrar_falha("Pré-condições da sequência não atendidas")

def iniciar_sequencia():
    start_progress(); resetar_resultados_etapas(); status_info("Aguarde…")
    etapa_1_factory_defaults()

# ======== Probe base (threads) ========
def aplicar_resultados_base(driver_ok, comp_ok, emul_ok, erro_txt=""):
    global probe_in_progress, sequencia_iniciada, tentou_remapear_lpt1
    global cur_driver_ok, cur_comp_ok, cur_emul_ok, last_error_text, last_check_time

    cur_driver_ok, cur_comp_ok, cur_emul_ok = driver_ok, comp_ok, emul_ok
    last_check_time = datetime.datetime.now().strftime("%H:%M:%S")
    if erro_txt: last_error_text = erro_txt
    update_details_text()

    any_fail = (not driver_ok) or (not comp_ok) or (not emul_ok)
    if any_fail and not sequencia_iniciada:
        set_bg(RED)
        status_info("FALHA: " + " ; ".join(filter(None, [
            None if driver_ok else "Driver/Online da BPX",
            None if comp_ok else f"Compartilhamento '{SHARE_TARGET}'",
            None if emul_ok else "Emulação LPT1"
        ])))
        tentou_remapear_lpt1 = False
        stop_progress()
    elif (not any_fail) and (not sequencia_iniciada) and (not appcontroller_executado):
        sequencia_iniciada = True
        set_bg(GRAY); status_info("Aguarde…")
        iniciar_sequencia()

    probe_in_progress = False

def probe_base_async():
    global tentou_remapear_lpt1
    erro_txt = ""
    driver_ok = verificar_driver()
    comp_ok   = verificar_compartilhamento()
    emul_ok   = verificar_emulacao()

    if driver_ok and comp_ok and not emul_ok and not tentou_remapear_lpt1:
        tentou_remapear_lpt1 = True
        try:
            emul_ok = remapear_emulacao_lpt1()
        except Exception as e:
            erro_txt = f"Remap LPT1: {e}"

    root.after(0, lambda: aplicar_resultados_base(driver_ok, comp_ok, emul_ok, erro_txt))

def atualizar():
    global probe_in_progress
    if not probe_in_progress:
        probe_in_progress = True
        threading.Thread(target=probe_base_async, daemon=True).start()
    root.after(CHECK_INTERVAL_MS, atualizar)

# ======== UI ========
root = tk.Tk()
root.title("Validador de Impressora Godex")
root.geometry("580x320")
root.resizable(False, False)

lbl_title  = tk.Label(root, text="Validador de Impressora Godex", font=("Segoe UI", 18, "bold"), bd=0, highlightthickness=0)
lbl_title.pack(pady=(14, 6))

lbl_status = tk.Label(root, text="Aguarde… verificando", font=("Segoe UI", 14, "bold"), bd=0, highlightthickness=0)
lbl_status.pack(pady=(0, 10))

progress = ttk.Progressbar(root, mode="indeterminate", length=520)
progress.pack(pady=(0, 10))
pb_running = [False]

btn_toggle = tk.Button(root, text="Ver detalhes", font=("Segoe UI", 10, "bold"),
                       command=toggle_details, bd=0, highlightthickness=0)
btn_toggle.pack(pady=(0, 6))

# --- Frame de detalhes (toggle) ---
frame_details = tk.Frame(root, bd=0, highlightthickness=0)
lbl_details = tk.Label(
    frame_details,
    text="",
    font=("Consolas", 11),   # monoespaçado = colunas mais alinhadas
    justify="left",
    anchor="w",
    bd=0, highlightthickness=0
)
lbl_details.pack(fill="x", padx=10, pady=(2, 4), anchor="w")

# Visual inicial
set_bg(GRAY)
start_progress()

# Pré-carrega/mostra tipo do cfg (cria arquivo se não existir)
_tipo, _ = garantir_cfg_e_ler_tipo()
last_tipo_text = 'Transferência térmica (^AT)' if _tipo == 1 else 'Térmica direta (^AD)'

# >>> Mostrar detalhes já na inicialização
if details_visible:
    update_details_text()  # preenche as linhas iniciais
    frame_details.pack(padx=12, pady=(4, 12), fill="x")
    btn_toggle.config(text="Ocultar detalhes")
# <<<
# Loop e UI
root.after(300, atualizar)
root.mainloop()
