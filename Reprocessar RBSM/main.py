import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
import cx_Oracle
from datetime import datetime, timedelta
import threading
import json
import os
from database import executar_checkout_sql, executar_procedure
from tkinter import messagebox
import re

class AppPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.processamento_ativo = False
        self.log_file = "processamento.log"
        self.historico_file = "historico_processamento.json"
        self.erro_file = "erros_processamento.log"
        self.historico = self.carregar_historico()
        
        # Configuração da janela
        self.title("Gerador EDI Rede Brasil")
        self.geometry("800x600")
        
        # Frame superior para calendários e botões
        self.frame_superior = ttk.Frame(self)
        self.frame_superior.pack(fill="x", padx=10, pady=10)
        
        # Calendários
        self.lbl_data_inicial = ttk.Label(self.frame_superior, text="Data Inicial:")
        self.lbl_data_inicial.pack(side="left", padx=5)
        
        self.data_inicial = DateEntry(self.frame_superior, width=12, background='darkblue',
                                    foreground='white', borderwidth=2)
        self.data_inicial.pack(side="left", padx=5)
        
        self.lbl_data_final = ttk.Label(self.frame_superior, text="Data Final:")
        self.lbl_data_final.pack(side="left", padx=5)
        
        self.data_final = DateEntry(self.frame_superior, width=12, background='darkblue',
                                  foreground='white', borderwidth=2)
        self.data_final.pack(side="left", padx=5)
        
        # Frame para botões
        self.frame_botoes = ttk.Frame(self.frame_superior)
        self.frame_botoes.pack(side="right", padx=10)
        
        # Botões de execução e parada
        self.btn_executar = ttk.Button(self.frame_botoes, text="Executar Processo",
                                     command=self.confirmar_execucao)
        self.btn_executar.pack(side="left", padx=5)
        
        self.btn_parar = ttk.Button(self.frame_botoes, text="Parar Processo",
                                   command=self.parar_processo, state="disabled")
        self.btn_parar.pack(side="left", padx=5)
        
        # Criar notebook para os logs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(padx=10, pady=5, fill="both", expand=True)
        
        # Aba para log de execução
        self.frame_execucao = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_execucao, text="Log de Execução")
        
        # Treeview para log de execução
        self.tree_execucao = ttk.Treeview(self.frame_execucao, columns=("empresa", "data", "status", "tempo"))
        self.tree_execucao.heading("empresa", text="Empresa")
        self.tree_execucao.heading("data", text="Data")
        self.tree_execucao.heading("status", text="Status")
        self.tree_execucao.heading("tempo", text="Tempo")
        
        # Configurar colunas
        self.tree_execucao.column("#0", width=0, stretch=False)  # Coluna fantasma
        self.tree_execucao.column("empresa", width=100)
        self.tree_execucao.column("data", width=100)
        self.tree_execucao.column("status", width=200)
        self.tree_execucao.column("tempo", width=100)
        
        # Scrollbar para a árvore
        scrollbar_tree = ttk.Scrollbar(self.frame_execucao, orient="vertical", command=self.tree_execucao.yview)
        self.tree_execucao.configure(yscrollcommand=scrollbar_tree.set)
        
        # Layout
        self.tree_execucao.pack(side="left", fill="both", expand=True)
        scrollbar_tree.pack(side="right", fill="y")
        
        # Dicionário para controlar execuções em andamento
        self.execucoes_em_andamento = {}
        
        # Aba para log de conclusão
        self.frame_conclusao = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_conclusao, text="Log de Conclusão")
        
        # Text widget para log de conclusão
        self.text_conclusao = tk.Text(self.frame_conclusao, width=80, height=30)
        self.text_conclusao.pack(padx=5, pady=5, fill="both", expand=True)
        
        # Scrollbar para log de conclusão
        scrollbar_conc = ttk.Scrollbar(self.text_conclusao)
        scrollbar_conc.pack(side="right", fill="y")
        self.text_conclusao.config(yscrollcommand=scrollbar_conc.set)
        scrollbar_conc.config(command=self.text_conclusao.yview)
        
        # Configurar estilos
        self.configure_styles()
        
        # Verificar integridade do histórico periodicamente
        self.after(60000, self.verificar_historico)  # Verifica a cada minuto
    
    def configure_styles(self):
        # Configurar estilo do text_conclusao
        self.text_conclusao.configure(
            bg='#f0f0f0',
            fg='black',
            font=('Consolas', 10)
        )
        
        # Configurar estilo do Treeview
        style = ttk.Style()
        style.configure("Treeview",
            background="#f0f0f0",
            foreground="black",
            fieldbackground="#f0f0f0",
            font=('Consolas', 10)
        )
        style.configure("Treeview.Heading",
            font=('Consolas', 10, 'bold')
        )
        
        # Configurar cores para os diferentes status
        self.tree_execucao.tag_configure("Em execução", background="light blue")
        self.tree_execucao.tag_configure("Concluído", background="light green")
        self.tree_execucao.tag_configure("Erro", background="light coral")
        self.tree_execucao.tag_configure("Aguardando", background="white")

    
    def carregar_historico(self):
        if os.path.exists(self.historico_file):
            try:
                with open(self.historico_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def salvar_historico(self):
        """Salva o histórico em arquivo com tratamento de erros"""
        try:
            with open(self.historico_file, 'w', encoding='utf-8') as f:
                json.dump(self.historico, f, indent=4, default=str, ensure_ascii=False)
        except Exception as e:
            self.adicionar_log(f"Erro ao salvar arquivo de histórico: {str(e)}", "erro")
    
    def ja_processado(self, data, nroempresa):
        data_str = data.strftime("%Y-%m-%d")
        return self.historico.get(data_str, {}).get(str(nroempresa), False)
    
    def marcar_processado(self, data, nroempresa, sucesso=True, erro=None):
        """Marca um processamento no histórico e salva imediatamente"""
        try:
            data_str = data.strftime("%Y-%m-%d")
            if data_str not in self.historico:
                self.historico[data_str] = {}
            
            # Salvar status com mais detalhes
            self.historico[data_str][str(nroempresa)] = {
                'sucesso': sucesso,
                'erro': erro,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Salvar imediatamente no arquivo
            self.salvar_historico()
        except Exception as e:
            self.adicionar_log(f"Erro ao salvar histórico: {str(e)}", "erro")
    
    def adicionar_log(self, mensagem, tipo="normal", categoria="conclusao"):
        cores = {
            "normal": "black",
            "erro": "red",
            "sucesso": "dark green",
            "info": "blue"
        }
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {mensagem}\n"
        
        try:
            # Selecionar o widget de texto apropriado
            text_widget = self.text_execucao if categoria == "execucao" else self.text_conclusao
            
            # Log na interface
            text_widget.tag_config(tipo, foreground=cores[tipo])
            text_widget.insert("end", f"[{timestamp}] ", "normal")
            text_widget.insert("end", f"{mensagem}\n", tipo)
            text_widget.see("end")
            text_widget.update()
            
            # Log no arquivo
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_msg)
        except Exception as e:
            print(f"Erro ao adicionar log: {str(e)}")
    
    def parar_processo(self):
        self.processamento_ativo = False
        self.adicionar_log("Solicitação de parada recebida. Aguardando finalização...", "info")
        
    def iniciar_processo(self):
        self.processamento_ativo = True
        self.btn_executar["state"] = "disabled"
        self.btn_parar["state"] = "normal"
        thread = threading.Thread(target=self.executar_processo)
        thread.start()
        
    def executar_processo(self):
        try:
            data_inicial = self.data_inicial.get_date()
            data_final = self.data_final.get_date()
            
            self.adicionar_log("Iniciando processamento...", "info")
            
            try:
                empresas = executar_procedure(
                    data_inicial, 
                    data_final,
                    callback=self.processar_callback,
                    should_stop=lambda: not self.processamento_ativo,
                    ignorar_processados=self.ignorar_processados,
                    historico=self.historico
                )
                
                self.adicionar_log(
                    f"Processamento concluído com sucesso!",
                    "sucesso"
                )
                
            except Exception as e:
                if "interrompido pelo usuário" in str(e):
                    self.adicionar_log("Processo interrompido pelo usuário", "info")
                else:
                    self.adicionar_log(f"Erro ao executar procedure: {str(e)}", "erro")
            
        except Exception as e:
            self.adicionar_log(f"Erro no processo: {str(e)}", "erro")
        finally:
            self.processamento_ativo = False
            self.btn_executar["state"] = "normal"
            self.btn_parar["state"] = "disabled"
    
    def processar_callback(self, mensagem, tipo, dados=None):
        """Processa callbacks do processamento e atualiza histórico"""
        # Atualizar log de conclusão
        self.after(100, lambda: self.adicionar_log(mensagem, tipo, "conclusao"))
        
        # Atualizar status na árvore de execução
        if "Iniciando processamento da Empresa" in mensagem:
            match = re.search(r"Empresa (\d+).+para (\d{2}/\d{2}/\d{4})", mensagem)
            if match:
                empresa = match.group(1)
                data = datetime.strptime(match.group(2), "%d/%m/%Y")
                self.atualizar_execucao(empresa, data, "Em execução")
        
        elif "processada com sucesso" in mensagem:
            match = re.search(r"Empresa (\d+).+para (\d{2}/\d{2}/\d{4})", mensagem)
            if match:
                empresa = match.group(1)
                data = datetime.strptime(match.group(2), "%d/%m/%Y")
                self.atualizar_execucao(empresa, data, "Concluído")
                self.marcar_processado(data, empresa)
        
        elif tipo == "erro" and dados:
            self.atualizar_execucao(dados['empresa'], dados['data'], "Erro")
            self.marcar_processado(
                dados['data'],
                dados['empresa'],
                sucesso=False,
                erro=dados.get('erro')
            )
            self.registrar_erro(dados['data'], dados['empresa'], dados['erro'])
    
    def zerar_historico(self):
        if tk.messagebox.askyesno("Confirmar", "Deseja realmente zerar o histórico de processamento?"):
            self.historico = {}
            self.salvar_historico()
            self.adicionar_log("Histórico de processamento zerado!", "info")
    
    def mostrar_erros(self):
        # Criar nova janela para mostrar erros
        janela_erros = tk.Toplevel(self)
        janela_erros.title("Histórico de Erros")
        janela_erros.geometry("600x400")
        
        # Área de texto para mostrar erros
        text_erros = tk.Text(janela_erros, wrap=tk.WORD)
        text_erros.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Mostrar erros do histórico
        for data in self.historico:
            for empresa, status in self.historico[data].items():
                if isinstance(status, dict) and status.get('erro'):
                    text_erros.insert("end", f"Data: {data}\n")
                    text_erros.insert("end", f"Empresa: {empresa}\n")
                    text_erros.insert("end", f"Erro: {status['erro']}\n")
                    text_erros.insert("end", "-" * 50 + "\n")
    
    def confirmar_execucao(self):
        """Diálogo de confirmação antes de iniciar o processamento"""
        zerar = messagebox.askyesno(
            "Zerar Histórico",
            "Deseja zerar o histórico de processamento antes de iniciar?"
        )
        if zerar:
            self.historico = {}
            self.salvar_historico()
            self.adicionar_log("Histórico de processamento zerado!", "info")
        
        ignorar = messagebox.askyesno(
            "Ignorar Processados",
            "Deseja ignorar registros já processados?"
        )
        
        if messagebox.askyesno("Confirmar", "Iniciar processamento?"):
            self.ignorar_processados = ignorar
            self.iniciar_processo()
    
    def registrar_erro(self, data, empresa, erro):
        """Registra erros em arquivo separado"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.erro_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] Data: {data.strftime('%d/%m/%Y')} - Empresa: {empresa} - Erro: {erro}\n")
            f.write("-" * 80 + "\n")
    
    def verificar_historico(self):
        """Verifica se o histórico está sendo salvo corretamente"""
        try:
            with open(self.historico_file, 'r', encoding='utf-8') as f:
                historico_arquivo = json.load(f)
                
            if self.historico != historico_arquivo:
                self.adicionar_log("Detectada diferença no histórico, resincronizando...", "info")
                self.salvar_historico()
                
        except Exception as e:
            self.adicionar_log(f"Erro ao verificar histórico: {str(e)}", "erro")
        
        finally:
            # Agendar próxima verificação
            self.after(60000, self.verificar_historico)
    
    def atualizar_execucao(self, empresa, data, status, tempo=None):
        """Atualiza o status de uma execução na árvore"""
        data_str = data.strftime("%d/%m/%Y")
        item_id = f"{empresa}_{data_str}"
        
        # Define cores baseadas no status
        cores = {
            "Em execução": "light blue",
            "Concluído": "light green",
            "Erro": "light coral",
            "Aguardando": "white"
        }

        
        if status == "Em execução":
            # Registra início da execução
            self.execucoes_em_andamento[item_id] = datetime.now()
            tempo_str = "Em andamento..."
        elif status in ["Concluído", "Erro"]:
            # Calcula tempo de execução
            inicio = self.execucoes_em_andamento.get(item_id)
            if inicio:
                tempo_decorrido = datetime.now() - inicio
                tempo_str = str(tempo_decorrido).split('.')[0]  # Remove microssegundos
                del self.execucoes_em_andamento[item_id]
            else:
                tempo_str = "N/A"
        else:
            tempo_str = ""

        # Verifica se o item já existe
        if self.tree_execucao.exists(item_id):
            self.tree_execucao.item(item_id, values=(empresa, data_str, status, tempo_str))
            self.tree_execucao.tag_configure(status, background=cores.get(status, "white"))
            self.tree_execucao.item(item_id, tags=(status,))
        else:
            self.tree_execucao.insert("", "end", item_id, values=(empresa, data_str, status, tempo_str))
            self.tree_execucao.tag_configure(status, background=cores.get(status, "white"))
            self.tree_execucao.item(item_id, tags=(status,))
        
        # Garante que o item mais recente esteja visível
        self.tree_execucao.see(item_id)

if __name__ == "__main__":
    app = AppPrincipal()
    app.mainloop() 