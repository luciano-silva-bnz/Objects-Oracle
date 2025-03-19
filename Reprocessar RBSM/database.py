import cx_Oracle
from datetime import datetime, timedelta
import concurrent.futures
import threading
from queue import Queue, Empty
import time

# Thread-local storage para conexões
thread_local = threading.local()
# Semáforo para controlar número máximo de conexões simultâneas
MAX_WORKERS = 30
connection_semaphore = threading.Semaphore(MAX_WORKERS)

def get_connection():
    if not hasattr(thread_local, "connection"):
        dsn = cx_Oracle.makedsn('189.126.156.13', '1521', service_name='CM6QEI_150976_C')
        thread_local.connection = cx_Oracle.connect(
            user='CLT150976TI',
            password='blvag60893YPFER!?',
            dsn=dsn
        )
    return thread_local.connection

def executar_checkout_sql():
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        cursor.execute("ALTER SESSION SET current_schema = CONSINCO")
        cursor.execute("""
            SELECT nroempresa 
            FROM MAX_EMPRESA 
            WHERE STATUS = 'A' 
            AND nroempresa not in (101,26,19,18,14,36,38,43)
            --AND nroempresa in (41)
        """)
        
        resultados = cursor.fetchall()
        cursor.close()
        
        return resultados
        
    except Exception as e:
        raise Exception(f"Erro ao consultar checkouts: {str(e)}")

def processar_empresa(data, nroempresa):
    with connection_semaphore:
        try:
            connection = get_connection()
            cursor = connection.cursor()
            
            cursor.execute("ALTER SESSION SET current_schema = CONSINCO")
            
            cursor.callproc(
                "ESP_PKG_EDI_REDEBRASIL.ESPP_GERA_EDI_REDEBRASIL",
                [
                    data,
                    data,
                    nroempresa
                ]
            )
            connection.commit()
            cursor.close()
            
            return nroempresa, True, None
            
        except Exception as e:
            return nroempresa, False, str(e)

class ProcessadorTarefas:
    def __init__(self, data_inicial, data_final, callback=None, should_stop=None, 
                 ignorar_processados=False, historico=None):
        self.data_inicial = data_inicial
        self.data_final = data_final
        self.callback = callback
        self.should_stop = should_stop
        self.ignorar_processados = ignorar_processados
        self.historico = historico
        self.fila_tarefas = Queue()
        self.empresas_em_execucao = {}  # Controle de empresas em execução
        self.lock = threading.Lock()
        
    def gerar_tarefas(self):
        empresas = [emp[0] for emp in executar_checkout_sql()]
        
        # Log inicial com resumo das tarefas
        if self.callback:
            self.callback(f"Encontradas {len(empresas)} empresas para processar", "info")
            self.callback(f"Período: {self.data_inicial.strftime('%d/%m/%Y')} até {self.data_final.strftime('%d/%m/%Y')}", "info")
            self.callback("Iniciando processamento...", "info")
        
        # Organizar tarefas por empresa primeiro
        for empresa in empresas:
            data_atual = self.data_inicial
            while data_atual <= self.data_final:
                data_str = data_atual.strftime("%Y-%m-%d")
                if self.ignorar_processados and self.historico and \
                   self.historico.get(data_str, {}).get(str(empresa), {}).get('sucesso', False):
                    if self.callback:
                        self.callback(
                            f"Pulando empresa {empresa} para data {data_atual.strftime('%d/%m/%Y')} - já processada",
                            "info"
                        )
                else:
                    self.fila_tarefas.put((data_atual, empresa))
                data_atual += timedelta(days=1)
            
        return empresas
    
    def pode_processar_empresa(self, empresa):
        """Verifica se uma empresa pode ser processada"""
        with self.lock:
            if empresa in self.empresas_em_execucao:
                return False
            self.empresas_em_execucao[empresa] = True
            return True
    
    def liberar_empresa(self, empresa):
        """Libera uma empresa para próximo processamento"""
        with self.lock:
            if empresa in self.empresas_em_execucao:
                del self.empresas_em_execucao[empresa]
    
    def processar_tarefa(self):
        while True:
            try:
                if self.should_stop and self.should_stop():
                    break
                
                # Tenta pegar uma nova tarefa
                try:
                    data, empresa = self.fila_tarefas.get_nowait()
                except Empty:
                    break
                
                # Verifica se pode processar esta empresa
                if not self.pode_processar_empresa(empresa):
                    # Coloca de volta na fila se não puder processar agora
                    self.fila_tarefas.put((data, empresa))
                    time.sleep(1)  # Aguarda um pouco antes de tentar novamente
                    continue
                
                try:
                    # Log de início do processamento
                    if self.callback:
                        self.callback(
                            f"Iniciando processamento da Empresa {empresa} para {data.strftime('%d/%m/%Y')}",
                            "info"
                        )
                    
                    # Processa a tarefa
                    nroempresa, sucesso, erro = processar_empresa(data, empresa)
                    
                    if self.callback:
                        if sucesso:
                            self.callback(
                                f"Empresa {nroempresa} processada com sucesso para {data.strftime('%d/%m/%Y')}",
                                "sucesso"
                            )
                        else:
                            self.callback(
                                f"Erro ao processar empresa {nroempresa} para {data.strftime('%d/%m/%Y')}: {erro}",
                                "erro",
                                {'data': data, 'empresa': nroempresa, 'erro': erro}
                            )
                finally:
                    # Libera a empresa para próximo processamento
                    self.liberar_empresa(empresa)
                
            except Exception as e:
                if self.callback:
                    self.callback(f"Erro no processamento: {str(e)}", "erro")
    
    def executar(self):
        try:
            empresas = self.gerar_tarefas()
            
            if self.fila_tarefas.empty():
                raise Exception("Nenhuma tarefa para processar")
            
            # Criar pool de threads
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Inicia os workers
                futures = [executor.submit(self.processar_tarefa) for _ in range(MAX_WORKERS)]
                
                # Aguarda conclusão
                concurrent.futures.wait(futures)
            
            return empresas
            
        except Exception as e:
            raise Exception(f"Erro na execução: {str(e)}")

def executar_procedure(data_inicial, data_final, callback=None, should_stop=None, 
                      ignorar_processados=False, historico=None):
    processador = ProcessadorTarefas(
        data_inicial, data_final, callback, should_stop,
        ignorar_processados, historico
    )
    return processador.executar()