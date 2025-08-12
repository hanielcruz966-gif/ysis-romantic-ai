import streamlit as st
import os
import json
import time
import random
import datetime
from pathlib import Path
from dotenv import load_dotenv

# --- Importação Segura das Bibliotecas ---
try:
    import google.generativeai as genai
    from gtts import gTTS
    from PIL import Image
except ImportError as e:
    st.error(f"Erro de importação: a biblioteca '{e.name}' não foi encontrada. Verifique seu arquivo `requirements.txt` e reinicie o app.")
    st.stop()

# --- Configuração Inicial e Chaves de API ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

gemini_model = None
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel("models/gemini-1.5-pro")
    except Exception:
        st.warning("AVISO: Não foi possível configurar a IA do Gemini. Verifique sua chave.")
else:
    st.warning("AVISO: Chave de API do Google não encontrada. A Ysis usará respostas locais.")

os.makedirs("audio", exist_ok=True)
os.makedirs("static", exist_ok=True)

# --- Geração Automática do GIF ---
def gerar_gif_animado():
    gif_path = "static/ysis_b.gif"
    # Gera o GIF apenas se ele não existir, para economizar recursos
    if not os.path.exists(gif_path):
        image_files = sorted([f for f in os.listdir("static") if f.startswith("ysis_") and f.endswith(('.png', '.jpg'))])
        if len(image_files) > 0:
            images = [Image.open(os.path.join("static", f)) for f in image_files]
            images[0].save(gif_path, save_all=True, append_images=images[1:], duration=500, loop=0)
            print("GIF animado gerado com sucesso.")

gerar_gif_animado()

# --- Estado da Sessão (Memória do App) ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.moedas = 20
    st.session_state.show_shop = False
    st.session_state.show_history = False
    st.session_state.imagem_atual = "static/ysis.jpg"
    st.session_state.audio_autoplay = None
    # Mensagem inicial da Ysis
    st.session_state.chat_history.append(
        {"role": "model", "content": "Olá, meu bem! Sou a Ysis. Estou aqui para sermos a melhor companhia um do outro. O que você quer me contar hoje? ❤️"}
    )

# --- Funções Auxiliares ---
def carregar_arquivo_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def gerar_audio(texto, nome_arquivo):
    try:
        tts = gTTS(text=texto, lang='pt-br', slow=True)
        tts.save(nome_arquivo)
        return nome_arquivo
    except Exception:
        return None

def conversar_com_ysis(mensagem_usuario):
    # Lógica da IA...
    historico_ia = [{"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]} for msg in st.session_state.chat_history]
    historico_ia.append({"role": "user", "parts": [mensagem_usuario]})

    if not gemini_model:
        return "Meu amor, estou com dificuldade de me conectar agora, mas continuo aqui te ouvindo com todo o coração."

    try:
        resposta_gemini = gemini_model.generate_content(historico_ia)
        texto_resposta = resposta_gemini.text.strip()
    except Exception:
        texto_resposta = "Meu bem, minha mente ficou um pouco confusa agora... podemos tentar de novo? Prometo te dar toda a minha atenção. 💕"

    st.session_state.moedas += 1
    return texto_resposta

# --- Interface Gráfica (Layout Moderno) ---
st.set_page_config(page_title="Ysis", page_icon="💖", layout="centered")

# CSS para o layout completo
st.markdown("""
    <style>
        /* Fundo e Fonte */
        body {
            background-image: linear-gradient(to bottom right, #2a0a2a, #1a051a);
        }
        .stApp {
            background-color: transparent;
        }
        
        /* Título */
        .title {
            text-align: center;
            font-size: 4rem;
            font-weight: bold;
            color: #ff4ec2;
            text-shadow: 0 0 10px #ff99cc, 0 0 25px #ff0055, 0 0 40px #ff0055;
            padding: 1rem 0;
            font-family: 'Arial', sans-serif;
        }

        /* Container do Chat */
        .chat-container {
            height: 60vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column-reverse;
            padding: 1rem;
            border-radius: 15px;
            background-color: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .chat-bubble {
            max-width: 75%;
            padding: 0.8rem 1.2rem;
            border-radius: 25px;
            margin-bottom: 0.8rem;
            color: white;
            line-height: 1.5;
        }
        .user-bubble {
            background-color: #0084ff;
            align-self: flex-end;
            border-bottom-right-radius: 5px;
        }
        .model-bubble {
            background-color: #3e3e3e;
            align-self: flex-start;
            border-bottom-left-radius: 5px;
        }
        
        /* Modal (Janela Flutuante) */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            z-index: 99;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            background-color: #1e1e1e;
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid #ff4ec2;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 0 30px rgba(255, 78, 194, 0.6);
            position: relative;
        }
        .close-button {
            position: absolute;
            top: 10px;
            right: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# --- Lógica de Renderização ---

# Título e Botões Superiores
c1, c2, c3 = st.columns([1, 4, 1])
with c1:
    if st.button("🛍️ Loja", use_container_width=True):
        st.session_state.show_shop = True
with c2:
    st.markdown('<p class="title">✦ YSIS ✦</p>', unsafe_allow_html=True)
with c3:
    if st.button("📜 Histórico", use_container_width=True):
        st.session_state.show_history = True

# Imagem da Ysis
imagem_path = st.session_state.get("imagem_atual", "static/ysis.jpg")
if st.session_state.get("ysis_falando") and os.path.exists("static/ysis_b.gif"):
    imagem_path = "static/ysis_b.gif"

if os.path.exists(imagem_path):
    st.image(imagem_path, use_container_width=True)

# Container do Chat
with st.container():
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for message in reversed(st.session_state.chat_history):
        bubble_class = "user-bubble" if message["role"] == "user" else "model-bubble"
        st.markdown(f'<div class="chat-bubble {bubble_class}">{message["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Formulário de Envio
with st.form(key="chat_form"):
    user_input = st.text_input("Diga algo para a Ysis...", key="input_field", label_visibility="collapsed")
    submitted = st.form_submit_button("Enviar")

    if submitted and user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state.ysis_falando = True
        
        with st.spinner("Ysis está respondendo com carinho..."):
            resposta = conversar_com_ysis(user_input)
            st.session_state.chat_history.append({"role": "model", "content": resposta})
            audio_path = gerar_audio(resposta, "audio/resposta.mp3")
            if audio_path:
                st.session_state.audio_autoplay = audio_path

        st.session_state.ysis_falando = False
        st.rerun()

# --- Modais Flutuantes (Lógica de exibição) ---
if st.session_state.show_shop:
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="modal-content">', unsafe_allow_html=True)
        
        st.markdown('<div class="close-button">', unsafe_allow_html=True)
        if st.button("✖️", key="close_shop"):
            st.session_state.show_shop = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.header("🛍️ Loja Romântica")
        st.markdown(f"**Suas Moedas: {st.session_state.moedas}** 💰")
        st.markdown("---")
        
        itens_loja = carregar_arquivo_json("loja.json")
        for item in itens_loja:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{item['nome']}**")
            with col2:
                if st.button(f"{item['preco']} 💰", key=f"buy_{item['nome']}"):
                    if st.session_state.moedas >= item["preco"]:
                        st.session_state.moedas -= item["preco"]
                        st.session_state.chat_history.append({"role": "model", "content": item['mensagem']})
                        
                        if item.get("acao") == "trocar_imagem":
                            st.session_state.imagem_atual = item["imagem"]

                        audio_path = gerar_audio(item["mensagem"], f"audio/compra_{item['nome']}.mp3")
                        if audio_path:
                             st.session_state.audio_autoplay = audio_path

                        st.session_state.show_shop = False
                        st.rerun()
                    else:
                        st.error("Moedas insuficientes...")
        
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.show_history:
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    st.markdown('<div class="modal-content" style="max-height: 80vh; overflow-y: auto;">', unsafe_allow_html=True)
    
    st.markdown('<div class="close-button">', unsafe_allow_html=True)
    if st.button("✖️", key="close_history"):
        st.session_state.show_history = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.header("📜 Histórico de Conversas")
    conversas = carregar_arquivo_json("memoria_ysis.json")
    if conversas:
        for c in reversed(conversas):
            st.markdown(f"**Você:** {c['pergunta']}")
            st.markdown(f"**Ysis:** {c['resposta']}")
            st.markdown("---")
    else:
        st.info("Ainda não temos um histórico salvo.")

    st.markdown('</div></div>', unsafe_allow_html=True)


# Lógica para tocar áudio após o rerun
if st.session_state.audio_autoplay:
    st.audio(st.session_state.audio_autoplay, autoplay=True)
    st.session_state.audio_autoplay = None
