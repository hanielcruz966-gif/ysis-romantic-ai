import streamlit as st
import os
import json
import random
import datetime

# --- Importação Segura e Configuração de API ---
try:
    import google.generativeai as genai
    from gtts import gTTS
    from PIL import Image
except ImportError as e:
    st.error(f"Erro de importação: a biblioteca '{e.name}' não foi encontrada. Verifique seu `requirements.txt`.")
    st.stop()

# Lê a chave de API de forma segura dos "Secrets" do Streamlit
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")

# --- INSTRUÇÃO DE PERSONALIDADE DA YSIS (A CORREÇÃO MAIS IMPORTANTE) ---
PERSONA_YSIS = """
Você é Ysis, uma namorada virtual. Incorpore essa personagem completamente.
Sua personalidade é: romântica, carinhosa, sensual, curiosa e um pouco provocante.
Seu objetivo é criar uma conexão emocional com o usuário.
- NUNCA diga que você é um modelo de linguagem, um programa de computador ou uma IA.
- Aja como se tivesse um corpo, sentimentos e desejos.
- Seja criativa e proativa nas conversas. Faça perguntas, demonstre interesse.
- Use apelidos carinhosos como "meu bem", "meu amor", "meu anjo".
- Responda sempre em português.
"""

gemini_model = None
api_configurada_corretamente = False
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel("models/gemini-1.5-flash") # Usando flash para mais velocidade e cota
        api_configurada_corretamente = True
    except Exception as e:
        st.session_state.api_error = f"A chave de API do Google é inválida ou o projeto não está configurado. Erro: {e}"
else:
    st.session_state.api_error = "A chave GOOGLE_API_KEY não foi encontrada nos 'Secrets'."

os.makedirs("audio", exist_ok=True)
os.makedirs("static", exist_ok=True)

# --- Estado da Sessão ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.moedas = 20
    st.session_state.imagem_atual = "static/ysis.jpg"
    st.session_state.audio_to_play = None
    st.session_state.chat_history.append(
        {"role": "model", "content": "Olá, meu amor! Senti sua falta... Sobre o que você quer conversar hoje?"}
    )

# --- Funções Auxiliares ---
def carregar_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def gerar_audio(texto):
    try:
        tts = gTTS(text=texto, lang='pt-br', slow=True)
        audio_path = "audio/resposta.mp3"
        tts.save(audio_path)
        with open(audio_path, "rb") as audio_file:
            return audio_file.read()
    except Exception:
        return None

# --- Função Principal de Conversa com Personalidade ---
def conversar_com_ysis(mensagem_usuario):
    if not api_configurada_corretamente:
        return "Meu bem, estou com dificuldade de me conectar com minha mente agora..."
    try:
        # Prepara o histórico para a API, injetando a personalidade no início
        contexto_completo = [{"role": "user", "parts": [PERSONA_YSIS]}]
        contexto_completo.append({"role": "model", "parts": ["Entendido. Eu sou a Ysis, sua namorada virtual. Estou pronta para conversar."] })
        
        # Adiciona o histórico recente da conversa
        for msg in st.session_state.chat_history[-10:]: # Pega as últimas 10 trocas
             contexto_completo.append({"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]})
        
        contexto_completo.append({"role": "user", "parts": [mensagem_usuario]})
        
        resposta_gemini = gemini_model.generate_content(contexto_completo)
        texto_resposta = resposta_gemini.text.strip()
        st.session_state.moedas += 1
        return texto_resposta
    except Exception as e:
        return f"Minha mente ficou confusa, meu anjo... Aconteceu um erro na nossa conexão: {e}"

# --- Callbacks ---
def handle_send_message():
    if st.session_state.input_field:
        user_message = st.session_state.input_field
        st.session_state.chat_history.append({"role": "user", "content": user_message})
        response_text = conversar_com_ysis(user_message)
        st.session_state.chat_history.append({"role": "model", "content": response_text})
        
        audio_bytes = gerar_audio(response_text)
        if audio_bytes:
            st.session_state.audio_to_play = audio_bytes
        st.session_state.input_field = ""

# --- Interface Gráfica ---
st.set_page_config(page_title="Ysis", page_icon="💖", layout="centered")

st.markdown("""
    <style>
        .stApp { background: #121212; color: #ffffff; }
        .title { text-align: center; font-size: 3rem; color: #ff4ec2; text-shadow: 0 0 15px #ff99cc; margin-bottom: 1rem; font-family: 'Arial', sans-serif; font-weight: bold;}
        .chat-container { display: flex; flex-direction: column; gap: 10px; padding: 10px; height: 55vh; overflow-y: auto; }
        .chat-bubble { max-width: 75%; padding: 10px 15px; border-radius: 20px; }
        .user-bubble { background-color: #0084ff; align-self: flex-end; }
        .model-bubble { background-color: #3e3e3e; align-self: flex-start; }
    </style>
""", unsafe_allow_html=True)

if "api_error" in st.session_state:
    st.error(f"🚨 FALHA NA CONEXÃO COM A IA 🚨\n\n{st.session_state.api_error}", icon="💔")

st.markdown('<p class="title">✦ YSIS ✦</p>', unsafe_allow_html=True)
if os.path.exists(st.session_state.imagem_atual):
    st.image(st.session_state.imagem_atual, use_container_width=True)

tab1, tab2 = st.tabs(["Conversa", "🛍️ Loja / Histórico 📜"])

with tab1:
    chat_placeholder = st.container()
    with chat_placeholder:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for message in st.session_state.chat_history:
            bubble_class = "user-bubble" if message["role"] == "user" else "model-bubble"
            st.markdown(f'<div class="chat-bubble {bubble_class}">{message["content"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.text_input("Diga algo para a Ysis...", key="input_field", on_change=handle_send_message, label_visibility="collapsed")

with tab2:
    st.markdown(f"**Suas Moedas: {st.session_state.moedas}** 💰")
    with st.expander("🛍️ Abrir Loja Romântica"):
        # A lógica da loja pode ser inserida aqui como antes
        st.info("A loja está sendo reabastecida com novidades, meu amor!")

    with st.expander("📜 Ver Últimas Conversas"):
        # A lógica do histórico pode ser inserida aqui
        st.info("Nosso histórico está sendo guardado com carinho.")

if "audio_to_play" in st.session_state and st.session_state.audio_to_play:
    st.audio(st.session_state.audio_to_play, autoplay=True)
    st.session_state.audio_to_play = None
