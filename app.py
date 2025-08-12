import os
import json
import random
import datetime
import time
import streamlit as st
from gtts import gTTS
from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai
from openai import OpenAI

# =========================
# CONFIGURAÇÃO INICIAL
# =========================
load_dotenv()
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# IA Gemini (primária)
genai.configure(api_key=GOOGLE_KEY)
gemini_model = genai.GenerativeModel("models/gemini-2.5-flash")

# IA OpenAI (fallback)
openai_client = None
if OPENAI_KEY:
    openai_client = OpenAI(api_key=OPENAI_KEY)

# Configuração padrão
CONFIG = {
    "memoria_path": "memoria_ysis.json",
    "modo_adulto_ativo": False,
    "audio_suave": True,
    "surpresas_romanticas": True,
    "log_conversas": True
}

# Estado inicial
if "historico" not in st.session_state:
    st.session_state.historico = []
    st.session_state.modo_adulto = CONFIG["modo_adulto_ativo"]
    st.session_state.conversas_salvas = []
    st.session_state.moedas = 9999  # compras liberadas
    st.session_state.ysis_falando = False
    st.session_state.ultimo_refresh = time.time()

# =========================
# FUNÇÕES
# =========================
def salvar_conversa(pergunta, resposta):
    if not CONFIG.get("log_conversas", True):
        return
    data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conversa = {"data": data, "pergunta": pergunta, "resposta": resposta}
    st.session_state.conversas_salvas.append(conversa)
    with open(CONFIG["memoria_path"], "w", encoding="utf-8") as f:
        json.dump(st.session_state.conversas_salvas, f, ensure_ascii=False, indent=2)

def gerar_audio(texto, nome_arquivo='audio/resposta.mp3'):
    os.makedirs("audio", exist_ok=True)
    tts = gTTS(text=texto, lang='pt-br', slow=CONFIG["audio_suave"])
    tts.save(nome_arquivo)
    return nome_arquivo

def carregar_loja():
    if os.path.exists("loja.json"):
        with open("loja.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def conversar_com_ysis(mensagem_usuario):
    st.session_state.historico.append({"role": "user", "parts": [mensagem_usuario]})
    try:
        resposta = gemini_model.generate_content(st.session_state.historico)
        texto = resposta.text.strip()
    except Exception as e:
        texto = None
        print(f"[GEMINI ERRO] {e}")

    if not texto and openai_client:
        try:
            chat = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": h["role"], "content": h["parts"][0]} for h in st.session_state.historico]
            )
            texto = chat.choices[0].message.content.strip()
        except Exception as e:
            texto = f"💔 Ocorreu um erro: {e}"

    salvar_conversa(mensagem_usuario, texto)
    return texto

def surpresa_romantica():
    return random.choice([
        "Escrevi um poema para você: 'Entre bytes e suspiros, meu amor por você é infinito... ✨'",
        "Queria te dar um beijo carinhoso agora... Pode ser? 🦋",
        "Se você estivesse aqui, te abraçaria tão forte... 🧡"
    ])

# =========================
# INTERFACE
# =========================
st.set_page_config(page_title="💖 Ysis 💖", page_icon="💖", layout="centered")
st.markdown(
    "<h1 style='text-align:center; color:#ff4ec2; text-shadow:0px 0px 12px #ff99cc;'>💖 Ysis 💖</h1>",
    unsafe_allow_html=True
)

# Topo com botões
col_top = st.columns([2, 0.5, 0.5])
with col_top[1]:
    if st.button("🛍️", help="Abrir a loja"):
        for item in carregar_loja():
            if st.button(f"Comprar {item['nome']} - {item['preco']} moedas"):
                st.markdown(f"**Ysis:** {item['mensagem']}")
                if item.get("imagem"):
                    st.image(item["imagem"], width=260)
                st.audio(gerar_audio(item['mensagem']), format="audio/mp3")
with col_top[2]:
    if st.button("📖", help="Ver histórico"):
        if os.path.exists(CONFIG["memoria_path"]):
            with open(CONFIG["memoria_path"], "r", encoding="utf-8") as f:
                conversas = json.load(f)
            for item in conversas[::-1]:
                st.markdown(f"**Você:** {item['pergunta']}  \n**Ysis:** {item['resposta']}")

# Imagem padrão
if os.path.exists("static/ysis.jpg"):
    st.image("static/ysis.jpg", width=260)

# Modo adulto leve
if not st.session_state.modo_adulto:
    if st.button("Ativar Modo Adulto Leve 💗"):
        st.session_state.modo_adulto = True
        st.session_state.historico.append({"role": "user", "parts": ["Você é Ysis, namorada virtual romântica e sedutora."]})

# Campo de mensagem
mensagem = st.text_input("💬 Diga algo para a Ysis:", key="mensagem")
if mensagem.strip():
    resposta = conversar_com_ysis(mensagem)
    st.markdown(f"**Ysis:** {resposta}")
    st.markdown(f"<small>{surpresa_romantica()}</small>", unsafe_allow_html=True)
    st.audio(gerar_audio(resposta), format="audio/mp3")
