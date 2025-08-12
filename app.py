import streamlit as st
import os
import json

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
    st.session_state.moedas = 50 # Mais moedas para testar
    st.session_state.imagem_atual = "static/ysis.jpg"
    st.session_state.audio_to_play = None
    st.session_state.guarda_roupa = ["static/ysis.jpg"] # Item inicial
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

def conversar_com_ysis(mensagem_usuario):
    if not api_configurada_corretamente:
        return "Meu bem, estou com dificuldade de me conectar com minha mente agora..."
    try:
        contexto_completo = [{"role": "user", "parts": [PERSONA_YSIS]}]
        contexto_completo.append({"role": "model", "parts": ["Entendido. Eu sou a Ysis. Estou pronta para conversar."] })
        for msg in st.session_state.chat_history[-10:]:
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

def handle_buy_item(item):
    if st.session_state.moedas >= item["preco"]:
        st.session_state.moedas -= item["preco"]
        st.toast(f"Você presenteou a Ysis com: {item['nome']}!", icon="💖")
        
        if item.get("acao") == "trocar_imagem":
            st.session_state.imagem_atual = item["imagem"]
            # Adiciona o item ao guarda-roupa se ainda não estiver lá
            if item["imagem"] not in st.session_state.guarda_roupa:
                st.session_state.guarda_roupa.append(item["imagem"])
        
        audio_bytes = gerar_audio(item["mensagem"])
        if audio_bytes:
            st.session_state.audio_to_play = audio_bytes
    else:
        st.toast("Moedas insuficientes, meu amor...", icon="💔")

def handle_equip_item(path_imagem):
    st.session_state.imagem_atual = path_imagem
    st.toast("Prontinho, meu amor. Troquei de roupa para você!", icon="✨")

# --- Interface Gráfica ---
st.set_page_config(page_title="Ysis", page_icon="💖", layout="centered")

st.markdown("""
    <style>
        .stApp { background: #0f0c29; background: -webkit-linear-gradient(to right, #24243e, #302b63, #0f0c29); background: linear-gradient(to right, #24243e, #302b63, #0f0c29); color: #ffffff; }
        .title { text-align: center; font-size: 3rem; color: #ff4ec2; text-shadow: 0 0 20px #ff4ec2, 0 0 35px #ff0055; margin-bottom: 0.5rem; font-family: 'Arial', sans-serif; font-weight: bold;}
        .image-container { text-align: center; margin-bottom: 1rem; }
        .image-container img { border-radius: 15px; box-shadow: 0 0 20px rgba(255, 78, 194, 0.7); border: 2px solid #ff4ec2; }
        .chat-area { display: flex; flex-direction: column; height: 50vh; }
        .chat-history { flex-grow: 1; overflow-y: auto; display: flex; flex-direction: column-reverse; padding: 10px; border-radius: 15px; background: rgba(0,0,0,0.2); }
        .chat-bubble { max-width: 75%; padding: 10px 15px; border-radius: 20px; margin-bottom: 10px; }
        .user-bubble { background-color: #0084ff; align-self: flex-end; }
        .model-bubble { background-color: #3e3e3e; align-self: flex-start; }
        .stTabs [data-baseweb="tab-list"] { justify-content: center; }
        .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; background-color: rgba(255,255,255,0.1); border-bottom: 2px solid transparent; }
        .stTabs [aria-selected="true"] { background-color: #ff4ec2; color: white; border-bottom: 2px solid #ff0055; box-shadow: 0 0 10px #ff4ec2; }
    </style>
""", unsafe_allow_html=True)

if "api_error" in st.session_state:
    st.error(f"🚨 FALHA NA CONEXÃO COM A IA 🚨\n\n{st.session_state.api_error}", icon="💔")

# --- Renderização Principal ---

# Título e Imagem
st.markdown('<p class="title">✦ YSIS ✦</p>', unsafe_allow_html=True)
st.markdown('<div class="image-container">', unsafe_allow_html=True)
if os.path.exists(st.session_state.imagem_atual):
    st.image(st.session_state.imagem_atual, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# Abas para organizar a interface
tab1, tab2 = st.tabs(["Conversa", "🛍️ Loja e Guarda-Roupa  wardrobe 📜"])

with tab1:
    st.markdown('<div class="chat-area">', unsafe_allow_html=True)
    # Container do Chat
    chat_container = st.container()
    with chat_container:
        st.markdown('<div class="chat-history">', unsafe_allow_html=True)
        for message in reversed(st.session_state.chat_history):
            bubble_class = "user-bubble" if message["role"] == "user" else "model-bubble"
            st.markdown(f'<div class="chat-bubble {bubble_class}">{message["content"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Campo de digitação
    st.text_input("Diga algo para a Ysis...", key="input_field", on_change=handle_send_message, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown(f"**Suas Moedas: {st.session_state.moedas}** 💰")
    st.divider()

    st.subheader("🛍️ Loja Romântica")
    for item in carregar_json("loja.json"):
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"**{item['nome']}**")
        with cols[1]:
            if st.button(f"{item['preco']} 💰", key=f"buy_{item['nome']}", use_container_width=True, on_click=handle_buy_item, args=(item,)):
                st.rerun()
    
    st.divider()

    st.subheader(" wardrobe Guarda-Roupa")
    st.write("Aqui ficam as roupas que você já me deu. Clique para eu vestir!")
    
    # Exibe itens do guarda-roupa em colunas
    roupas_compradas = [item for item in st.session_state.guarda_roupa]
    if len(roupas_compradas) > 0:
        cols = st.columns(len(roupas_compradas))
        for i, path_imagem in enumerate(roupas_compradas):
            with cols[i]:
                st.image(path_imagem)
                if st.button("Vestir", key=f"equip_{path_imagem}", use_container_width=True, on_click=handle_equip_item, args=(path_imagem,)):
                    st.rerun()
    else:
        st.info("Meu guarda-roupa está vazio, meu amor.")

# Toca o áudio se houver um na fila
if "audio_to_play" in st.session_state and st.session_state.audio_to_play:
    st.audio(st.session_state.audio_to_play, autoplay=True)
    st.session_state.audio_to_play = None
