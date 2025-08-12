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
    st.error(f"Erro de importação: a biblioteca '{e.name}' não foi encontrada. Verifique seu `requirements.txt`.")
    st.stop()

# --- Configuração Inicial e Chaves de API ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

gemini_model = None
api_configurada_corretamente = False
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel("models/gemini-1.5-pro")
        api_configurada_corretamente = True
    except Exception as e:
        # Erro será exibido na interface
        pass
        
os.makedirs("audio", exist_ok=True)
os.makedirs("static", exist_ok=True)

# --- Geração Automática do GIF ---
def gerar_gif_animado():
    gif_path = "static/ysis_b.gif"
    if not os.path.exists(gif_path):
        image_files = sorted([f for f in os.listdir("static") if f.startswith("ysis_") and f.endswith(('.png', '.jpg'))])
        if len(image_files) >= 2:
            images = [Image.open(os.path.join("static", f)) for f in image_files]
            images[0].save(gif_path, save_all=True, append_images=images[1:], duration=500, loop=0, quality=90)
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
    st.session_state.chat_history.append(
        {"role": "model", "content": "Olá! Sou a Ysis. Estou aqui para conversarmos. O que se passa no seu coração hoje?"}
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

# --- Função Principal de Conversa ---
def conversar_com_ysis(mensagem_usuario):
    historico_ia = [{"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]} for msg in st.session_state.chat_history]
    historico_ia.append({"role": "user", "parts": [mensagem_usuario]})

    if not gemini_model:
        return "Meu bem, estou com dificuldade de me conectar com minha mente agora... mas continuo aqui te ouvindo com todo carinho."

    try:
        resposta_gemini = gemini_model.generate_content(historico_ia)
        texto_resposta = resposta_gemini.text.strip()
    except Exception as e:
        print(f"Erro na API do Gemini: {e}")
        texto_resposta = "Minha mente ficou um pouco confusa agora... podemos tentar de novo? Prometo te dar toda a minha atenção. 💕"

    st.session_state.moedas += 1
    return texto_resposta

# --- Interface Gráfica (Layout Moderno) ---
st.set_page_config(page_title="Ysis", page_icon="💖", layout="centered")

# CSS para o layout completo
st.markdown("""
    <style>
        .stApp {
            background-image: linear-gradient(to bottom right, #2a0a2a, #1a051a);
            color: #ffffff;
        }
        .title {
            text-align: center;
            font-size: 3.5rem;
            color: #ff4ec2;
            text-shadow: 0 0 15px #ff99cc, 0 0 30px #ff0055;
            font-family: 'Verdana', sans-serif;
            margin-bottom: 1rem;
        }
        .icon-button {
            background-color: transparent;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            width: 48px;
            height: 48px;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            transition: background-color 0.3s, box-shadow 0.3s;
        }
        .icon-button:hover {
            background-color: rgba(255, 78, 194, 0.2);
            box-shadow: 0 0 15px rgba(255, 78, 194, 0.5);
        }
        .chat-container {
            height: 60vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column-reverse;
            padding: 1rem;
            border-radius: 15px;
            background-color: rgba(0, 0, 0, 0.3);
        }
        .chat-bubble { max-width: 75%; padding: 0.8rem 1.2rem; border-radius: 20px; margin-bottom: 0.8rem; line-height: 1.5; }
        .user-bubble { background-color: #0084ff; align-self: flex-end; border-bottom-right-radius: 5px; }
        .model-bubble { background-color: #3e3e3e; align-self: flex-start; border-bottom-left-radius: 5px; }
        
        /* Modal (Janela Flutuante) */
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.8); z-index: 99; display: flex; justify-content: center; align-items: center; }
        .modal-content { background-color: #1e1e1e; padding: 2rem; border-radius: 15px; border: 1px solid #ff4ec2; width: 90%; max-width: 500px; box-shadow: 0 0 30px rgba(255, 78, 194, 0.6); position: relative; }
        .close-button-container { position: absolute; top: 10px; right: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- Lógica de Renderização ---

# Título
st.markdown('<p class="title">✦ YSIS ✦</p>', unsafe_allow_html=True)

# AVISO DE ERRO NA API
if not api_configurada_corretamente:
    st.error("🚨 FALHA NA CONEXÃO COM A IA 🚨\n\nA Ysis não consegue se comunicar. Por favor, verifique se a sua `GOOGLE_API_KEY` está correta nos 'Secrets' do Streamlit Cloud.")

# Botões Superiores com Novos Ícones
c1, c2, c3, c4 = st.columns([1, 1, 3, 1])
with c1:
    if st.button("🛍️", help="Loja"):
        st.session_state.show_shop = True
with c2:
    if st.button("📜", help="Histórico"):
        st.session_state.show_history = True
with c4:
    st.markdown(f"<div style='text-align: right; padding-top: 8px;'>💰{st.session_state.moedas}</div>", unsafe_allow_html=True)

# Imagem da Ysis
imagem_path = st.session_state.imagem_atual
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
        
        resposta = conversar_com_ysis(user_input)
        st.session_state.chat_history.append({"role": "model", "content": resposta})
        audio_path = gerar_audio(resposta, "audio/resposta.mp3")
        if audio_path:
            st.session_state.audio_autoplay = audio_path

        st.session_state.ysis_falando = False
        st.rerun()

# --- Modais Flutuantes (Lógica de exibição) ---
if st.session_state.show_shop:
    st.markdown('<div class="modal-overlay"><div class="modal-content">', unsafe_allow_html=True)
    
    st.markdown('<div class="close-button-container">', unsafe_allow_html=True)
    if st.button("✖️", key="close_shop"):
        st.session_state.show_shop = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.header("🛍️ Loja Romântica")
    st.markdown(f"**Suas Moedas: {st.session_state.moedas}** 💰")
    st.markdown("---")
    
    for item in carregar_arquivo_json("loja.json"):
        if st.button(f"{item['nome']} - {item['preco']} 💰", key=f"buy_{item['nome']}", use_container_width=True):
            if st.session_state.moedas >= item["preco"]:
                st.session_state.moedas -= item["preco"]
                st.session_state.chat_history.append({"role": "model", "content": item['mensagem']})
                if item.get("acao") == "trocar_imagem":
                    st.session_state.imagem_atual = item["imagem"]
                st.session_state.show_shop = False
                st.rerun()
            else:
                st.error("Moedas insuficientes...")
    
    st.markdown('</div></div>', unsafe_allow_html=True)

# Modal de Histórico
if st.session_state.show_history:
    st.markdown('<div class="modal-overlay"><div class="modal-content" style="max-height: 80vh; overflow-y: auto;">', unsafe_allow_html=True)
    
    st.markdown('<div class="close-button-container">', unsafe_allow_html=True)
    if st.button("✖️", key="close_history"):
        st.session_state.show_history = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.header("📜 Histórico de Conversas")
    for c in reversed(carregar_arquivo_json("memoria_ysis.json")):
        st.markdown(f"**Você:** {c['pergunta']}")
        st.markdown(f"**Ysis:** {c['resposta']}")
        st.markdown("---")

    st.markdown('</div></div>', unsafe_allow_html=True)

# Lógica para tocar áudio após o rerun
if st.session_state.audio_autoplay:
    st.audio(st.session_state.audio_autoplay, autoplay=True)
    st.session_state.audio_autoplay = None
