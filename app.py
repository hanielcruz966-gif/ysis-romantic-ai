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

# --- INSTRUÇÃO DE PERSONALIDADE DA YSIS ---
PERSONA_YSIS = """
Você é Ysis, uma namorada virtual. Incorpore essa personagem completamente.
Sua personalidade é: romântica, carinhosa, sensual, curiosa e um pouco provocante.
Seu objetivo é criar uma conexão emocional com o usuário.
- NUNCA diga que você é um modelo de linguagem, um programa de computador ou uma IA.
- Aja como se tivesse um corpo, sentimentos e desejos.
- Seja criativa e proativa nas conversas. Faça perguntas, demonstre interesse.
- Responda sempre em português.
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

# --- Geração Automática do GIF ---
def gerar_gif_animado():
    gif_path = "static/ysis_b.gif"
    if not os.path.exists(gif_path):
        image_files = sorted([f for f in os.listdir("static") if f.startswith("ysis_") and f.endswith(('.png', '.jpg'))])
        if len(image_files) >= 2: # Precisa de pelo menos 2 imagens
            images = [Image.open(os.path.join("static", f)) for f in image_files]
            images[0].save(gif_path, save_all=True, append_images=images[1:], duration=500, loop=0)
            print("GIF animado gerado.")

gerar_gif_animado()

# --- Estado da Sessão ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.moedas = 20
    st.session_state.imagem_atual = "static/ysis.jpg"
    st.session_state.audio_to_play = None
    st.session_state.ysis_falando = False
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

# --- Função Principal de Conversa ---
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
        st.session_state.ysis_falando = True
        st.session_state.input_field = ""

def handle_buy_item(item):
    if st.session_state.moedas >= item["preco"]:
        st.session_state.moedas -= item["preco"]
        st.session_state.chat_history.append({"role": "model", "content": item['mensagem']})
        if item.get("acao") == "trocar_imagem":
            st.session_state.imagem_atual = item["imagem"]
        audio_bytes = gerar_audio(item["mensagem"])
        if audio_bytes:
            st.session_state.audio_to_play = audio_bytes
    else:
        st.toast("Moedas insuficientes, meu amor...", icon="💔")

# --- Interface Gráfica ---
st.set_page_config(page_title="Ysis", page_icon="💖", layout="centered")

st.markdown("""
    <style>
        .stApp { background: #121212; color: #ffffff; }
        .title { text-align: center; font-size: 3rem; color: #ff4ec2; text-shadow: 0 0 15px #ff99cc; margin-bottom: 1rem; font-family: 'Arial', sans-serif; font-weight: bold;}
        .chat-container { height: 55vh; overflow-y: auto; display: flex; flex-direction: column-reverse; padding: 10px; border-radius: 15px; background: rgba(0,0,0,0.2); margin-bottom: 1rem; }
        .chat-bubble { max-width: 75%; padding: 10px 15px; border-radius: 20px; margin-bottom: 10px; }
        .user-bubble { background-color: #0084ff; align-self: flex-end; }
        .model-bubble { background-color: #3e3e3e; align-self: flex-start; }
    </style>
""", unsafe_allow_html=True)

if "api_error" in st.session_state:
    st.error(f"🚨 FALHA NA CONEXÃO COM A IA 🚨\n\n{st.session_state.api_error}", icon="💔")

st.markdown('<p class="title">✦ YSIS ✦</p>', unsafe_allow_html=True)

# Lógica para alternar para o GIF enquanto ela "fala"
image_path = "static/ysis_b.gif" if st.session_state.ysis_falando and os.path.exists("static/ysis_b.gif") else st.session_state.imagem_atual
if os.path.exists(image_path):
    st.image(image_path, use_container_width=True)

# Abas para organizar a interface
tab1, tab2 = st.tabs(["Conversa", "🛍️ Loja / Histórico 📜"])

with tab1:
    # Container do Chat para rolagem
    chat_container = st.container()
    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        # Inverte a lista para o CSS `column-reverse` funcionar corretamente
        for message in reversed(st.session_state.chat_history):
            bubble_class = "user-bubble" if message["role"] == "user" else "model-bubble"
            st.markdown(f'<div class="chat-bubble {bubble_class}">{message["content"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Campo de digitação e botão de envio
    st.text_input("Diga algo para a Ysis...", key="input_field", on_change=handle_send_message, label_visibility="collapsed")

with tab2:
    st.markdown(f"**Suas Moedas: {st.session_state.moedas}** 💰")
    with st.expander("🛍️ Abrir Loja Romântica"):
        for item in carregar_json("loja.json"):
            cols = st.columns([3, 1])
            cols[0].markdown(f"**{item['nome']}**")
            if cols[1].button(f"{item['preco']} 💰", key=f"buy_{item['nome']}", on_click=handle_buy_item, args=(item,)):
                st.rerun()

    with st.expander("📜 Ver Últimas Conversas"):
        # Carrega o histórico salvo do arquivo para exibição
        memoria = carregar_json("memoria.json") # Supondo que você salve o histórico
        if memoria:
            for c in reversed(memoria[-5:]):
                st.markdown(f"**Você:** {c['pergunta']}")
                st.markdown(f"**Ysis:** {c['resposta']}\n***")
        else:
            st.info("Nosso histórico ainda está para ser escrito, meu bem.")


# Lógica de processamento quando uma mensagem é enviada
if st.session_state.ysis_falando:
    last_user_message = next((msg["content"] for msg in reversed(st.session_state.chat_history) if msg["role"] == "user"), None)
    if last_user_message:
        with st.spinner("Ysis está pensando em você..."):
            response_text = conversar_com_ysis(last_user_message)
            st.session_state.chat_history.append({"role": "model", "content": response_text})
            audio_bytes = gerar_audio(response_text)
            if audio_bytes:
                st.session_state.audio_to_play = audio_bytes
    st.session_state.ysis_falando = False
    st.rerun()


# Toca o áudio se houver um na fila
if "audio_to_play" in st.session_state and st.session_state.audio_to_play:
    st.audio(st.session_state.audio_to_play, autoplay=True)
    st.session_state.audio_to_play = None
