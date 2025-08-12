import streamlit as st
import os
import json
import base64 # Importante para o novo método de vídeo

# --- Importação Segura e Configuração de API ---
try:
    import google.generativeai as genai
    from gtts import gTTS
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
    st.session_state.moedas = 100
    st.session_state.imagem_atual = "static/ysis.jpg"
    st.session_state.audio_to_play = None
    st.session_state.video_to_play = None
    st.session_state.guarda_roupa = ["static/ysis.jpg"]
    st.session_state.chat_history.append(
        {"role": "model", "content": "Olá, meu amor! Que bom te ver de novo. Sobre o que vamos conversar hoje?"}
    )

# --- Funções Auxiliares e de Conversa ---
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

def conversar_com_ysis(mensagem_usuario):
    lower_message = mensagem_usuario.lower()
    if any(keyword in lower_message for keyword in ["dança", "dance"]):
        st.session_state.imagem_atual = "static/ysis_dress_red.jpg"
        st.session_state.video_to_play = "static/ysis_dance_red.mp4"
        return "Com prazer, meu amor! Coloquei meu vestido vermelho... agora, assista à minha dança só para você. 😉"
    
    if any(keyword in lower_message for keyword in ["beijo", "me beija"]):
        st.session_state.imagem_atual = "static/ysis_kiss.jpg"
        return "*Ysis se aproxima suavemente e te dá um beijo doce e demorado... Mwah! 💋*"

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
        return f"Minha mente ficou confusa, meu anjo... Erro na conexão: {e}"

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
        .stApp { background: linear-gradient(to right, #24243e, #302b63, #0f0c29); color: #ffffff; }
        .block-container { padding: 1rem; }
        .main-layout { display: flex; flex-direction: column; height: 90vh; }
        .header { text-align: center; }
        .title { font-size: 3rem; color: #ff4ec2; text-shadow: 0 0 20px #ff4ec2; margin: 0; }
        .image-container { text-align: center; padding: 0.5rem 0; }
        .image-container img, .image-container video {
            max-height: 35vh;
            width: auto;
            border-radius: 15px;
            border: 2px solid #ff4ec2;
            box-shadow: 0 0 20px rgba(255, 78, 194, 0.7);
        }
        .chat-history { flex-grow: 1; overflow-y: auto; display: flex; flex-direction: column-reverse; padding: 10px; border-radius: 15px; background: rgba(0,0,0,0.2); margin-bottom: 1rem; }
        .chat-bubble { max-width: 80%; padding: 10px 15px; border-radius: 20px; margin-bottom: 10px; overflow-wrap: break-word; }
        .user-bubble { background-color: #0084ff; align-self: flex-end; }
        .model-bubble { background-color: #3e3e3e; align-self: flex-start; }
    </style>
""", unsafe_allow_html=True)

# --- LAYOUT PRINCIPAL DO APP ---
st.markdown('<div class="main-layout">', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="header">', unsafe_allow_html=True)
    st.markdown('<p class="title">YSIS</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="image-container">', unsafe_allow_html=True)
    # --- LÓGICA PARA MOSTRAR VÍDEO SEM CONTROLES ---
    if st.session_state.get("video_to_play") and os.path.exists(st.session_state.video_to_play):
        video_path = st.session_state.video_to_play
        with open(video_path, "rb") as video_file:
            video_bytes = video_file.read()
            base64_video = base64.b64encode(video_bytes).decode('utf-8')
            
            video_html = f"""
                <video autoplay muted playsinline>
                    <source src="data:video/mp4;base64,{base64_video}" type="video/mp4">
                </video>
            """
            st.markdown(video_html, unsafe_allow_html=True)
        
        st.session_state.video_to_play = None # Limpa para não repetir na próxima interação
    else:
        if os.path.exists(st.session_state.imagem_atual):
            st.image(st.session_state.imagem_atual)
    st.markdown('</div>', unsafe_allow_html=True)

# ÁREA DO CHAT
chat_container = st.container()
with chat_container:
    st.markdown('<div class="chat-history">', unsafe_allow_html=True)
    for message in reversed(st.session_state.chat_history):
        bubble_class = "user-bubble" if message["role"] == "user" else "model-bubble"
        st.markdown(f'<div class="chat-bubble {bubble_class}">{message["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# CAMPO DE DIGITAÇÃO
st.text_input("Diga algo para a Ysis...", key="input_field", on_change=handle_send_message, label_visibility="collapsed")

st.markdown('</div>', unsafe_allow_html=True)

# Toca o áudio se houver um na fila
if "audio_to_play" in st.session_state and st.session_state.audio_to_play:
    st.audio(st.session_state.audio_to_play, autoplay=True)
    st.session_state.audio_to_play = None

# LOJA E GUARDA-ROUPA (em uma barra lateral para não interferir)
with st.sidebar:
    # A lógica da loja e guarda-roupa continua aqui...
    pass # (O código da loja e guarda-roupa que já tínhamos)
