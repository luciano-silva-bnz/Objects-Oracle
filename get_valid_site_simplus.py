from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
import time

chromedriver_autoinstaller.install()
# Configuração do ChromeOptions para iniciar maximizado
chrome_options = Options()
chrome_options.add_argument("--start-maximized")

# Configuração do driver do Chrome com as opções
driver = webdriver.Chrome(options=chrome_options)
# Acesse o site
driver.get("https://sso.simplustec.com.br/realms/simplus-platform/protocol/openid-connect/auth?client_id=prod-service&redirect_uri=https%3A%2F%2Fauth.simplustec.com.br%2Fapplications%2Fapps&state=1bf4b1f1-e862-469e-8f60-bac1cc66c93a&response_mode=fragment&response_type=code&scope=openid&nonce=b34dfd32-a15d-49d1-83bd-836fcf5107ab&code_challenge=xBeVREr_N3xbBL4wGaNbn6F4XSiUtt7GD80jjGbU5ic&code_challenge_method=S256")
time.sleep(5)  
# Localize e preencha o campo de usuário
campo_usuario = driver.find_element(By.NAME, "username")
campo_usuario.send_keys("luciano@bonanza.com.br")

# Localize e preencha o campo de senha
campo_senha = driver.find_element(By.NAME, "password")
campo_senha.send_keys("luci@NO86")
campo_senha.send_keys(Keys.RETURN)  # Submete o formulário de login

# Aguarde um tempo para garantir que o login foi processado
time.sleep(3)  # Ajuste o tempo conforme necessário

# Localize o elemento pela classe e clique nele "SIMPLUS"
elemento = driver.find_element(By.CLASS_NAME, "application")
elemento.click()
time.sleep(5)  # Ajuste o tempo conforme necessário
# Após o login, encontre o campo onde você vai colar o texto da tabela


# Feche o navegador
driver.quit()


