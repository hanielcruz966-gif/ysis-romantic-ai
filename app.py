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

# Carrega a chave de API de forma segura
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")

gemini_model = None
api_configurada_corretamente = False
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel("models/gemini-1.5-pro")
        api_configurada_corretamente = True
    except Exception as e:
        st.session_state.api_error = f"A chave de API do Google é inválida ou o projeto não está configurado corretamente. Erro: {e}"
else:
    st.session_state.api_error = "A chave GOOGLE_API_KEY não foi encontrada nos 'Secrets' do seu app."

# Cria pastas necessárias
os.makedirs("audio", exist_ok=True)
os.makedirs("static", exist_ok=True)

# --- Estado da Sessão ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.moedas = 20
    st.session_state.imagem_atual = "static/ysis.jpg"
    st.session_state.chat_history.append(
        {"role": "model", "content": "Olá! Sou a Ysis. Estou aqui para você. O que se passa no seu coração hoje?"}
    )

# --- Funções Auxiliares ---
def carregar_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def gerar_audio(texto, nome_arquivo):
    try:
        tts = gTTS(text=texto, lang='pt-br', slow=True)
        tts.save(nome_arquivo)
        with open(nome_arquivo, "rb") as audio_file:
            return audio_file.read()
    except Exception:
        return None

def conversar_com_ysis(mensagem_usuario):
    if not api_configurada_corretamente:
        return "Meu bem, estou com dificuldade de me conectar com minha mente agora..."
    try:
        historico_ia = [{"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]} for msg in st.session_state.chat_history]
        historico_ia.append({"role": "user", "parts": [mensagem_usuario]})
        
        resposta_gemini = gemini_model.generate_content(historico_ia)
        texto_resposta = resposta_gemini.text.strip()
        st.session_state.moedas += 1
        return texto_resposta
    except Exception as e:
        return f"Minha mente ficou confusa... (Erro na API: {e})"

# --- Callbacks ---
def handle_send_message():
    if st.session_state.input_field:
        user_message = st.session_state.input_field
        st.session_state.chat_history.append({"role": "user", "content": user_message})
        response_text = conversar_com_ysis(user_message)
        st.session_state.chat_history.append({"role": "model", "content": response_text})
        
        audio_bytes = gerar_audio(response_text, "audio/resposta.mp3")
        if audio_bytes:
            st.session_state.audio_to_play = audio_bytes
        st.session_state.input_field = ""

def handle_buy_item(item):
    if st.session_state.moedas >= item["preco"]:
        st.session_state.moedas -= item["preco"]
        st.session_state.chat_history.append({"role": "model", "content": item['mensagem']})
        if item.get("acao") == "trocar_imagem":
            st.session_state.imagem_atual = item["imagem"]
        
        audio_bytes = gerar_audio(item["mensagem"], "audio/compra.mp3")
        if audio_bytes:
            st.session_state.audio_to_play = audio_bytes
    else:
        st.toast("Moedas insuficientes, meu amor...", icon="💔")

# --- Interface Gráfica ---
st.set_page_config(page_title="Ysis", page_icon="💖", layout="centered")

# CSS para o layout
st.markdown("""
    <style>
        .stApp { background: #121212; color: #ffffff; }
        .title { text-align: center; font-size: 3rem; color: #ff4ec2; text-shadow: 0 0 15px #ff99cc; margin-bottom: 1rem; font-family: 'Arial', sans-serif; font-weight: bold;}
        .chat-container { display: flex; flex-direction: column; gap: 10px; padding: 10px; }
        .chat-bubble { max-width: 75%; padding: 10px 15px; border-radius: 20px; }
        .user-bubble { background-color: #0084ff; align-self: flex-end; }
        .model-bubble { background-color: #3e3e3e; align-self: flex-start; }
    </style>
""", unsafe_allow_html=True)

# AVISO DE ERRO NA API
if "api_error" in st.session_state:
    st.error(f"🚨 FALHA NA CONEXÃO COM A IA 🚨\n\n{st.session_state.api_error}", icon="💔")

# Título e Imagem
st.markdown('<p class="title">✦ YSIS ✦</p>', unsafe_allow_html=True)
if os.path.exists(st.session_state.imagem_atual):
    st.image(st.session_state.imagem_atual, use_container_width=True)

# Botões de Loja e Histórico (em abas para organizar)
tab1, tab2 = st.tabs(["Conversa", "🛍️ Loja / Histórico 📜"])

with tab1:
    # Container do Chat
    chat_placeholder = st.empty()
    with chat_placeholder.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for message in st.session_state.chat_history:
            bubble_class = "user-bubble" if message["role"] == "user" else "model-bubble"
            st.markdown(f'<div class="chat-bubble {bubble_class}">{message["content"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Campo de digitação
    st.text_input("Diga algo para a Ysis...", key="input_field", on_change=handle_send_message, label_visibility="collapsed")

with tab2:
    st.markdown(f"**Suas Moedas: {st.session_state.moedas}** 💰")
    with st.expander("🛍️ Abrir Loja Romântica"):
        for item in carregar_json("loja.json"):
            cols = st.columns([3, 1])
            cols[0].markdown(f"**{item['nome']}**")
            if cols[1].button(f"{item['preco']} 💰", key=f"buy_{item['nome']}", on_click=handle_buy_item, args=(item,)):
                st.rerun() # Apenas para atualizar a UI da loja

    with st.expander("📜 Ver Últimas Conversas"):
        for c in reversed(carregar_json("memoria_ysis.json")[-5:]): # Mostra as 5 últimas
            st.markdown(f"**Você:** {c['pergunta']}")
            st.markdown(f"**Ysis:** {c['resposta']}\n***")

# Toca o áudio se houver um na fila
if "audio_to_play" in st.session_state and st.session_state.audio_to_play:
    st.audio(st.session_state.audio_to_play, autoplay=True)
    st.session_state.audio_to_play = None
