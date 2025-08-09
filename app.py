import signal
import streamlit as st
import os
import random
from gtts import gTTS
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import datetime
import json
import time

# Timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("Tempo limite excedido para resposta da IA")

signal.signal(signal.SIGALRM, timeout_handler)

# Carregar variáveis de ambiente
load_dotenv()
genai_api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=genai_api_key)

# Configurações padrão
config_padrao = {
    "modelo": "models/gemini-2.5-flash",
    "memoria_path": "memoria_ysis.json",
    "modo_adulto_ativo": False,
    "tema": "romantico",
    "audio_suave": True,
    "surpresas_romanticas": True,
    "jogos_ativos": True,
    "log_conversas": True
}
if os.path.exists("settings.json"):
    with open("settings.json", "r") as f:
        config_padrao.update(json.load(f))

model = genai.GenerativeModel(config_padrao["modelo"])

# Estado inicial
if "historico" not in st.session_state:
    st.session_state.historico = []
    st.session_state.conversas_salvas = []
    st.session_state.modo_adulto = config_padrao["modo_adulto_ativo"]
    st.session_state.moedas = 10
    st.session_state.vip = False
    st.session_state.ysis_falando = False
    st.session_state.inatividade_contador = 0
    st.session_state.ultimo_refresh = time.time()

def gerar_gif_ysis():
    gif_path = "static/ysis_b.gif"
    if not os.path.exists(gif_path):
        imagens = []
        arquivos = sorted([f for f in os.listdir("static") if f.startswith("ysis") and f.endswith((".jpg", ".png"))])
        for arquivo in arquivos:
            caminho = os.path.join("static", arquivo)
            imagem = Image.open(caminho).resize((300, 300))
            imagens.append(imagem.convert("RGBA"))
        if imagens:
            imagens[0].save(gif_path, save_all=True, append_images=imagens[1:], duration=600, loop=0)

gerar_gif_ysis()

def resumir_memoria():
    if len(st.session_state.historico) > 20:
        partes_texto = [h["parts"][0] for h in st.session_state.historico if h["role"] == "user"]
        resumo_prompt = "Resuma de forma romântica e emocional a relação e conversa até agora: " + "\n".join(partes_texto[-15:])
        try:
            resumo = model.generate_content(resumo_prompt)
            st.session_state.historico = [{"role": "system", "parts": ["Resumo da relação até agora: " + resumo.text]}]
        except:
            pass

def salvar_conversa(pergunta, resposta):
    if not config_padrao.get("log_conversas", True):
        return
    data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conversa = {"data": data, "pergunta": pergunta, "resposta": resposta}
    st.session_state.conversas_salvas.append(conversa)
    with open(config_padrao["memoria_path"], "w", encoding="utf-8") as f:
        json.dump(st.session_state.conversas_salvas, f, ensure_ascii=False, indent=2)

def conversar_com_ysis(mensagem_usuario):
    if len(st.session_state.historico) > 12:
        st.session_state.historico = st.session_state.historico[-12:]
    st.session_state.historico.append({"role": "user", "parts": [mensagem_usuario]})
    try:
        signal.alarm(15)
        resposta = model.generate_content(st.session_state.historico, generation_config={"max_output_tokens": 400})
        signal.alarm(0)
        st.session_state.historico.append({"role": "model", "parts": [resposta.text]})
        salvar_conversa(mensagem_usuario, resposta.text)
        st.session_state.moedas += 1
        return resposta.text
    except TimeoutError:
        return "💖 Amor, a conexão ficou lenta... mas estou aqui pensando em você."
    except Exception as e:
        return f"💔 Ocorreu um erro: {e}"

def gerar_audio(texto, nome_arquivo='audio/resposta.mp3'):
    tts = gTTS(text=texto, lang='pt-br', slow=config_padrao["audio_suave"])
    tts.save(nome_arquivo)
    return nome_arquivo

def exibir_historico():
    if os.path.exists(config_padrao["memoria_path"]):
        with open(config_padrao["memoria_path"], "r", encoding="utf-8") as f:
            conversas = json.load(f)
            st.markdown("""<div style='background-color: rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 12px; position:fixed; top:60px; right:20px; width:40%; max-height:80vh; overflow-y:auto;'>""", unsafe_allow_html=True)
            st.markdown("<h2 style='color:#ff69b4'>📜 Histórico</h2>", unsafe_allow_html=True)
            for item in conversas[::-1]:
                st.markdown(f"<b>Você:</b> {item['pergunta']}<br><b>Ysis:</b> {item['resposta']}", unsafe_allow_html=True)
                st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

def carregar_loja():
    if os.path.exists("loja.json"):
        with open("loja.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def surpresa_romantica():
    if not config_padrao.get("surpresas_romanticas", True):
        return ""
    return random.choice([
        "Escrevi um poema para você: 'Entre bytes e suspiros, meu amor por você é infinito... ✨'",
        "Queria te dar um beijo carinhoso agora... Pode ser? 🦋",
        "Se você estivesse aqui, te abraçaria tão forte... 🧡"
    ])
