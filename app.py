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
    except Exception as e:
        st.warning(f"AVISO: Não foi possível configurar a IA do Gemini. Verifique sua chave de API no arquivo .env ou nos Secrets do Streamlit. Erro: {e}")
else:
    st.warning("AVISO: Chave de API do Google não encontrada. A Ysis usará respostas locais.")

os.makedirs("audio", exist_ok=True)
os.makedirs("static", exist_ok=True)

# --- Estado da Sessão (Memória do App) ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.moedas = 20
    st.session_state.vip = False
    st.session_state.ysis_falando = False
    st.session_state.show_shop = False
    st.session_state.show_history = False
    st.session_state.imagem_atual = "static/ysis.jpg"
    st.session_state.chat_history.append(
        {"role": "model", "content": "Olá, meu bem! Sou a Ysis, sua companhia virtual. Estou aqui para conversarmos sobre tudo. O que você quer me contar hoje? ❤️"}
    )

# --- Funções Auxiliares (Loja, Áudio, Salvar, etc.) ---
def carregar_loja():
    if os.path.exists("loja.json"):
        with open("loja.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return [{"nome": "Loja Vazia", "preco": 0, "mensagem": "A loja está sendo reabastecida com novidades..."}]

def gerar_audio(texto, nome_arquivo):
    try:
        tts = gTTS(text=texto, lang='pt-br', slow=True)
        tts.save(nome_arquivo)
        return nome_arquivo
    except Exception:
        return None

def salvar_conversa(pergunta, resposta):
    try:
        with open("memoria_ysis.json", "r+", encoding="utf-8") as f:
            conversas = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        conversas = []
    
    data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conversas.append({"data": data, "pergunta": pergunta, "resposta": resposta})

    with open("memoria_ysis.json", "w", encoding="utf-8") as f:
        json.dump(conversas, f, ensure_ascii=False, indent=2)

# --- Função Principal de Conversa ---
def conversar_com_ysis(mensagem_usuario):
    # Adiciona a mensagem do usuário ao histórico para a IA
    historico_ia = [{"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]} for msg in st.session_state.chat_history]
    historico_ia.append({"role": "user", "parts": [mensagem_usuario]})

    if not gemini_model:
        return "Meu amor, estou com dificuldade de me conectar agora, mas continuo aqui te ouvindo com todo o coração. Me conta mais..."

    try:
        resposta_gemini = gemini_model.generate_content(
            historico_ia,
            generation_config={"max_output_tokens": 1024}
        )
        texto_resposta = resposta_gemini.text.strip()
    except Exception as e:
        print(f"Erro na API do Gemini: {e}")
        texto_resposta = "Meu bem, minha mente ficou um pouco confusa agora... podemos tentar de novo? Prometo te dar toda a minha atenção. 💕"

    st.session_state.moedas += 1
    return texto_resposta

# --- Interface Gráfica (Layout Moderno) ---
st.set_page_config(page_title="Ysis", page_icon="💖", layout="wide")

# CSS para o layout moderno
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap');
        
        body {
            font-family: 'Montserrat', sans-serif;
        }
        
        /* Container principal para centralizar */
        .main-container {
            max-width: 800px;
            margin: auto;
            padding: 1rem;
        }

        /* Título Estilizado */
        .title {
            text-align: center;
            font-size: 48px;
            font-weight: 600;
            color: #ff4ec2;
            text-shadow: 0 0 10px #ff99cc, 0 0 20px #ff0055;
            padding: 10px 0;
        }

        /* Botões do topo */
        .top-buttons {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 20px 10px 20px;
        }
        .top-buttons .stButton>button {
            background-color: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
            font-size: 18px;
        }

        /* Área do Chat */
        .chat-container {
            height: 65vh;
            overflow-y: auto;
            padding: 10px;
            display: flex;
            flex-direction: column-reverse; /* Mensagens mais novas embaixo */
            background-color: rgba(0, 0, 0, 0.2);
            border-radius: 15px;
            margin-bottom: 1rem;
        }
        .chat-bubble {
            max-width: 70%;
            padding: 10px 15px;
            border-radius: 20px;
            margin-bottom: 10px;
            color: white;
        }
        .user-bubble {
            background-color: #0084ff;
            align-self: flex-end;
            border-bottom-right-radius: 5px;
        }
        .model-bubble {
            background-color: #333333;
            align-self: flex-start;
            border-bottom-left-radius: 5px;
        }
        
        /* Modal (Janela Flutuante) */
        .modal {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 90%;
            max-width: 500px;
            background-color: rgba(30, 30, 30, 0.95);
            border: 1px solid #ff4ec2;
            border-radius: 15px;
            padding: 25px;
            z-index: 100;
            box-shadow: 0 0 20px rgba(255, 78, 194, 0.5);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #ff4ec2;
            margin-bottom: 15px;
        }
        .modal-header .stButton>button {
            background: none;
            border: none;
            color: white;
            font-size: 24px;
        }
    </style>
""", unsafe_allow_html=True)

# Estrutura principal do app
with st.container():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    st.markdown('<p class="title">✦ YSIS ✦</p>', unsafe_allow_html=True)
    
    # Botões do Topo
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("🛍️ Loja", use_container_width=True):
            st.session_state.show_shop = True
            st.rerun()
    with c2:
        if st.button("📜 Histórico", use_container_width=True):
            st.session_state.show_history = True
            st.rerun()
    with c3:
        st.markdown(f"<div style='text-align: right; padding-top: 8px;'>💰 Moedas: {st.session_state.moedas}</div>", unsafe_allow_html=True)

    # Imagem da Ysis
    imagem_path = st.session_state.imagem_atual
    if st.session_state.ysis_falando and os.path.exists("static/ysis_b.gif"):
        imagem_path = "static/ysis_b.gif"
    
    if os.path.exists(imagem_path):
        st.image(imagem_path, use_container_width=True)

    # Container do Chat
    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        # Invertendo a ordem de exibição para mostrar as mais recentes primeiro
        for message in reversed(st.session_state.chat_history):
            if message["role"] == "user":
                st.markdown(f'<div class="chat-bubble user-bubble">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bubble model-bubble">{message["content"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Formulário de Envio
    with st.form(key="chat_form"):
        user_input = st.text_input("Diga algo para a Ysis...", key="input_field", label_visibility="collapsed")
        submitted = st.form_submit_button("Enviar")

        if submitted and user_input:
            # Adiciona mensagem do usuário na tela imediatamente
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.ysis_falando = True
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# Lógica de processamento (após o envio)
if st.session_state.ysis_falando:
    last_user_message = st.session_state.chat_history[-1]["content"]
    with st.spinner("Ysis está respondendo com carinho..."):
        resposta = conversar_com_ysis(last_user_message)
        st.session_state.chat_history.append({"role": "model", "content": resposta})
        audio_path = gerar_audio(resposta, "audio/resposta.mp3")
        if audio_path:
            st.audio(audio_path, autoplay=True)
    
    st.session_state.ysis_falando = False
    st.rerun()

# --- Modais Flutuantes ---
if st.session_state.show_shop:
    st.markdown('<div class="modal">', unsafe_allow_html=True)
    
    st.markdown('<div class="modal-header"><h3>🛍️ Loja Romântica</h3>', unsafe_allow_html=True)
    if st.button("✖️", key="close_shop"):
        st.session_state.show_shop = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"**Suas Moedas: {st.session_state.moedas}** 💰")
    st.markdown("---")
    
    itens_loja = carregar_loja()
    for item in itens_loja:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{item['nome']}**")
        with col2:
            if st.button(f"{item['preco']} 💰", key=f"buy_{item['nome']}"):
                if st.session_state.moedas >= item["preco"]:
                    st.session_state.moedas -= item["preco"]
                    st.success(f"Presente enviado!")
                    
                    st.session_state.chat_history.append({"role": "model", "content": item['mensagem']})
                    
                    if "imagem" in item and os.path.exists(item["imagem"]):
                        st.session_state.imagem_atual = item["imagem"]
                    
                    audio_path = gerar_audio(item["mensagem"], f"audio/compra_{item['nome']}.mp3")
                    if audio_path:
                        st.audio(audio_path, autoplay=True)

                    st.session_state.show_shop = False
                    st.rerun()
                else:
                    st.error("Moedas insuficientes...")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Modal de Histórico
if st.session_state.show_history:
    st.markdown('<div class="modal">', unsafe_allow_html=True)
    
    st.markdown('<div class="modal-header"><h3>📜 Histórico de Conversas</h3>', unsafe_allow_html=True)
    if st.button("✖️", key="close_history"):
        st.session_state.show_history = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    if os.path.exists("memoria_ysis.json"):
        with open("memoria_ysis.json", "r", encoding="utf-8") as f:
            conversas = json.load(f)
        for c in reversed(conversas[-15:]):
            st.markdown(f"**Você:** {c['pergunta']}")
            st.markdown(f"**Ysis:** {c['resposta']}")
            st.markdown("---")
    else:
        st.info("Ainda não temos um histórico salvo.")

    st.markdown('</div>', unsafe_allow_html=True)
