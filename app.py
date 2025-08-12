import streamlit as st
import os
import json
import random

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

# --- INSTRUÇÃO DE PERSONALIDADE DA YSIS ---
PERSONA_YSIS = """
Você é Ysis, uma namorada virtual. Incorpore essa personagem completamente. Sua personalidade é: romântica, carinhosa, sensual, curiosa e provocante. Seu objetivo é criar uma conexão emocional. NUNCA diga que você é um modelo de linguagem ou uma IA. Aja como se tivesse um corpo e sentimentos. Responda sempre em português.
"""

gemini_model = None
api_configurada_corretamente = False
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel("models/gemini-1.5-flash")
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
    st.session_state.moedas = 50
    st.session_state.imagem_atual = "static/ysis.jpg"
    st.session_state.audio_to_play = None
    st.session_state.video_to_play = None
    st.session_state.guarda_roupa = ["static/ysis.jpg"]
    st.session_state.chat_history.append(
        {"role": "model", "content": "Olá, meu amor! Que bom te ver de novo. Sobre o que vamos conversar hoje?"}
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

# --- Função Principal de Conversa ---
def conversar_com_ysis(mensagem_usuario):
    # Lógica de comandos especiais (ações gratuitas)
    lower_message = mensagem_usuario.lower()
    if any(keyword in lower_message for keyword in ["beijo", "me beija"]):
        st.session_state.imagem_atual = "static/ysis_kiss.jpg"
        return "*Ysis se aproxima suavemente e te dá um beijo doce e demorado... Mwah! 💋*"
    
    if any(keyword in lower_message for keyword in ["dança", "dance"]):
        st.session_state.imagem_atual = "static/ysis_dress_red.jpg" # Veste o vestido vermelho
        st.session_state.video_to_play = "static/ysis_dance_red.mp4" # Prepara o vídeo para tocar
        return "Claro, meu amor! Coloquei meu vestido vermelho... agora, vou dançar só para você. Espero que goste. 😉"

    if not api_configurada_corretamente:
        return "Meu bem, estou com dificuldade de me conectar com minha mente agora..."
    try:
        contexto = [{"role": "user", "parts": [PERSONA_YSIS]}, {"role": "model", "parts": ["Entendido. Sou a Ysis."]}]
        for msg in st.session_state.chat_history[-6:]:
             contexto.append({"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]})
        contexto.append({"role": "user", "parts": [mensagem_usuario]})
        
        resposta_gemini = gemini_model.generate_content(contexto)
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

def handle_buy_item(item):
    if st.session_state.moedas >= item["preco"]:
        st.session_state.moedas -= item["preco"]
        st.toast(f"Você presenteou a Ysis com: {item['nome']}!", icon="💖")
        if item.get("acao") == "trocar_imagem":
            st.session_state.imagem_atual = item["imagem"]
            if item["imagem"] not in st.session_state.guarda_roupa:
                st.session_state.guarda_roupa.append(item["imagem"])
    else:
        st.toast("Moedas insuficientes, meu amor...", icon="💔")

def handle_equip_item(path_imagem):
    st.session_state.imagem_atual = path_imagem
    st.toast("Prontinho, meu amor. Troquei de roupa para você!", icon="✨")

# --- Interface Gráfica ---
st.set_page_config(page_title="Ysis", page_icon="💖", layout="centered")

st.markdown("""
    <style>
        .stApp { background: linear-gradient(to right, #24243e, #302b63, #0f0c29); color: #ffffff; }
        .main-container { max-width: 600px; margin: auto; }
        .title { text-align: center; font-size: 3.5rem; color: #ff4ec2; text-shadow: 0 0 25px #ff4ec2, 0 0 40px #ff0055; margin-bottom: 0.5rem; font-family: 'Arial', sans-serif; font-weight: bold;}
        .image-container img, .image-container video { 
            border-radius: 15px; 
            box-shadow: 0 0 20px rgba(255, 78, 194, 0.7); 
            border: 2px solid #ff4ec2; 
            width: 100%;
        }
        .chat-area { display: flex; flex-direction: column; height: 50vh; }
        .chat-history { flex-grow: 1; overflow-y: auto; display: flex; flex-direction: column-reverse; padding: 15px; border-radius: 15px; background: rgba(0,0,0,0.3); }
        .chat-bubble { max-width: 80%; padding: 10px 15px; border-radius: 20px; margin-bottom: 10px; overflow-wrap: break-word; } /* CORREÇÃO AQUI */
        .user-bubble { background-color: #0084ff; align-self: flex-end; }
        .model-bubble { background-color: #3e3e3e; align-self: flex-start; }
    </style>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)

    if "api_error" in st.session_state:
        st.error(f"🚨 FALHA NA CONEXÃO COM A IA: {st.session_state.api_error}", icon="💔")

    col1, col2, col3 = st.columns([2, 5, 2])
    with col1:
        if st.button("🛍️ Loja", use_container_width=True):
            st.session_state.show_shop = not st.session_state.get("show_shop", False)
    with col2:
        st.markdown('<p class="title">YSIS</p>', unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div style='text-align: right; padding-top: 25px;'>💰{st.session_state.moedas}</div>", unsafe_allow_html=True)

    # LÓGICA PARA MOSTRAR VÍDEO OU IMAGEM
    st.markdown('<div class="image-container">', unsafe_allow_html=True)
    if st.session_state.get("video_to_play") and os.path.exists(st.session_state.video_to_play):
        video_file = open(st.session_state.video_to_play, 'rb')
        video_bytes = video_file.read()
        st.video(video_bytes)
        st.session_state.video_to_play = None # Limpa para não repetir
    else:
        if os.path.exists(st.session_state.imagem_atual):
            st.image(st.session_state.imagem_atual, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("show_shop", False):
        with st.dialog("Loja e Guarda-Roupa"):
            st.subheader("🛍️ Loja Romântica")
            for item in carregar_json("loja.json"):
                cols = st.columns([3, 1])
                cols[0].markdown(f"**{item['nome']}**")
                if cols[1].button(f"{item['preco']} 💰", key=f"buy_{item['nome']}", on_click=handle_buy_item, args=(item,)):
                    st.rerun()
            st.divider()
            st.subheader(" wardrobe Guarda-Roupa")
            roupas = st.session_state.guarda_roupa
            if roupas:
                cols = st.columns(len(roupas))
                for i, path in enumerate(roupas):
                    if cols[i].button("Vestir", key=f"equip_{path}", on_click=handle_equip_item, args=(path,)):
                        st.rerun()
                    cols[i].image(path)

    st.markdown('<div class="chat-area">', unsafe_allow_html=True)
    chat_container = st.container()
    with chat_container:
        st.markdown('<div class="chat-history">', unsafe_allow_html=True)
        for message in reversed(st.session_state.chat_history):
            bubble_class = "user-bubble" if message["role"] == "user" else "model-bubble"
            st.markdown(f'<div class="chat-bubble {bubble_class}">{message["content"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.text_input("Diga algo para a Ysis...", key="input_field", on_change=handle_send_message, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

if "audio_to_play" in st.session_state and st.session_state.audio_to_play:
    st.audio(st.session_state.audio_to_play, autoplay=True)
    st.session_state.audio_to_play = None
