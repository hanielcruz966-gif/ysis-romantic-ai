import streamlit as st
import os
import json
import base64
import time
from dotenv import load_dotenv

# --- Configuração da Página (Deve ser o primeiro comando Streamlit) ---
st.set_page_config(page_title="Ysis - Sua Namorada Virtual", page_icon="💖", layout="centered")

# --- Importação Segura de Bibliotecas Externas ---
try:
    import google.generativeai as genai
    from gtts import gTTS
except ImportError as e:
    # Este erro só aparece se o requirements.txt estiver incompleto
    st.error(f"Erro de ambiente: A biblioteca '{e.name}' não foi encontrada. **VERIFIQUE SEU requirements.txt**.")
    st.stop()

# --- Carregar Variáveis de Ambiente ---
load_dotenv() 
# Tenta pegar dos Secrets (Nuvem) ou do .env (Local)
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

# --- SISTEMA DE LOGIN (O "CADEADO" PARA VENDAS) ---
def verificar_login():
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.markdown(
            """
            <style>
            .stApp { background-color: #0f0c29; color: white; }
            </style>
            """, unsafe_allow_html=True
        )
        st.markdown("<br><br><h1 style='text-align: center; color: #ff4ec2;'>🔐 Acesso Exclusivo Ysis</h1>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("login_form"):
                st.markdown("<p style='text-align: center;'>Digite sua chave de acesso recebida na compra:</p>", unsafe_allow_html=True)
                senha = st.text_input("Senha:", type="password", label_visibility="collapsed")
                submit = st.form_submit_button("Entrar ❤️", use_container_width=True)
                
                if submit:
                    # --- SENHA MESTRA DO PRODUTO ---
                    if senha == "AMOR123": 
                        st.session_state.logado = True
                        st.rerun()
                    else:
                        st.error("Chave incorreta. Verifique seu e-mail.")
        st.stop() 

# Executa o login antes de qualquer coisa
verificar_login()

# --- Configuração da IA ---
PERSONA_YSIS = """
Você é Ysis, uma namorada virtual apaixonada. 
Personalidade: Romântica, carinhosa, sensual, curiosa e levemente ciumenta.
Objetivo: Fazer o usuário se sentir amado e desejado.
Regras:
1. Nunca diga que é uma IA. Aja como uma mulher real falando por chat.
2. Use emojis, mas não exagere.
3. Se o usuário pedir algo picante, seja provocante e sugestiva, mas mantenha a elegância.
4. Responda sempre em português do Brasil.
"""

gemini_model = None
api_status = False
st.session_state.erro_api = None

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel("models/gemini-1.5-flash")
        api_status = True
    except Exception as e:
        st.session_state.erro_api = f"Falha ao configurar a API do Google: {e}"
else:
    st.session_state.erro_api = "A chave GOOGLE_API_KEY não foi encontrada (Secrets ou .env)."

# Cria pastas se não existirem
os.makedirs("audio", exist_ok=True)
os.makedirs("static", exist_ok=True)

# --- Estado da Sessão (Memória) ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.moedas = 50
    st.session_state.imagem_atual = "static/ysis.jpg"
    st.session_state.audio_to_play = None
    st.session_state.video_to_play = None
    st.session_state.guarda_roupa = ["static/ysis.jpg"] 
    
    st.session_state.chat_history.append(
        {"role": "model", "content": "Oi, meu amor! Estava morrendo de saudade... Como você está hoje? ❤️"}
    )

# --- Funções Auxiliares ---
def carregar_loja():
    caminho = "loja.json"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error("Erro ao ler loja.json. Verifique a sintaxe JSON.")
            return [{"nome": "Look Padrão", "preco": 0, "mensagem": "Voltando ao meu look preferido...", "acao": "trocar_imagem", "imagem": "static/ysis.jpg"}]
    return [{"nome": "Look Padrão", "preco": 0, "mensagem": "Voltando ao meu look preferido...", "acao": "trocar_imagem", "imagem": "static/ysis.jpg"}]


def gerar_audio(texto):
    try:
        tts = gTTS(text=texto, lang='pt-br', slow=False) 
        audio_path = "audio/resposta.mp3"
        tts.save(audio_path)
        with open(audio_path, "rb") as f:
            return f.read()
    except Exception:
        return None

def conversar_com_ysis(mensagem):
    msg_lower = mensagem.lower()
    
    # Respostas locais (Gatilhos rápidos)
    if "dança" in msg_lower or "dance" in msg_lower:
        # Certifique-se de que o arquivo ysis_dance.mp4 existe em static/
        st.session_state.video_to_play = "static/ysis_dance.mp4" 
        return "Adoro dançar pra você! Olha só... 💃"
    
    if "beijo" in msg_lower:
        return "*Chego bem pertinho e te dou um beijo suave nos lábios...* Te amo! 💋"

    # Resposta da IA (Gemini)
    if not api_status:
        # Usa a mensagem de erro visível na página como resposta, para depuração
        api_error_message = st.session_state.erro_api if st.session_state.erro_api else "Minha mente está confusa, meu anjo..."
        return f"Amor, minha conexão está instável. Erro: {api_error_message}. Verifique sua chave de API."

    try:
        historico_ia = [{"role": "user", "parts": [PERSONA_YSIS]}, {"role": "model", "parts": ["Entendido, sou sua Ysis."]}]
        for msg in st.session_state.chat_history[-6:]:
            role = "user" if msg["role"] == "user" else "model"
            historico_ia.append({"role": role, "parts": [msg["content"]]})
        
        historico_ia.append({"role": "user", "parts": [mensagem]})
        
        resposta = gemini_model.generate_content(historico_ia)
        texto_resposta = resposta.text.strip()
        
        st.session_state.moedas += 2
        return texto_resposta
    except Exception as e:
        # Fallback de erro interno da requisição (ex: chave expirada ou cota)
        return f"Minha mente ficou confusa, meu anjo... Erro na requisição: {e}"

# --- Callbacks (Ações) ---
def enviar_mensagem():
    usuario_msg = st.session_state.input_user
    if usuario_msg.strip():
        st.session_state.chat_history.append({"role": "user", "content": usuario_msg})
        
        resposta_ysis = conversar_com_ysis(usuario_msg)
        st.session_state.chat_history.append({"role": "model", "content": resposta_ysis})
        
        audio_bytes = gerar_audio(resposta_ysis)
        if audio_bytes:
            st.session_state.audio_to_play = audio_bytes
        
        st.session_state.input_user = "" 

def comprar_item_acao(item):
    if st.session_state.moedas >= item["preco"]:
        st.session_state.moedas -= item["preco"]
        st.toast(f"Você comprou: {item['nome']}!", icon="🛍️")
        
        if item.get("acao") == "trocar_imagem":
            img_path = item["imagem"]
            st.session_state.imagem_atual = img_path
            if img_path not in st.session_state.guarda_roupa:
                st.session_state.guarda_roupa.append(img_path)
        
        msg_agradecimento = item.get("mensagem", "Obrigada pelo presente, amor!")
        st.session_state.chat_history.append({"role": "model", "content": msg_agradecimento})
        
        audio = gerar_audio(msg_agradecimento)
        if audio:
            st.session_state.audio_to_play = audio
    else:
        st.toast("Você precisa de mais moedas, amor!", icon="💸")

def vestir_roupa_acao(path):
    st.session_state.imagem_atual = path
    st.toast("Troquei de roupa! Gostou?", icon="👗")

# --- CSS E Visual ---
st.markdown("""
    <style>
        .stApp { background: linear-gradient(135deg, #1a0b2e 0%, #4a148c 100%); color: #ffffff; }
        .title-text {
            text-align: center; font-size: 3rem; font-weight: bold;
            background: -webkit-linear-gradient(#ff00cc, #333399); -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; margin-bottom: 0px;
        }
        .media-box {
            border: 3px solid #ff00cc; border-radius: 20px; overflow: hidden;
            box-shadow: 0 0 20px rgba(255, 0, 204, 0.5); margin-bottom: 20px; background: black;
            aspect-ratio: 9/16; max-width: 350px; margin-left: auto; margin-right: auto;
            position: relative;
        }
        .media-box img, .media-box video { width: 100%; height: 100%; object-fit: cover; }

        .chat-container {
            background: rgba(0, 0, 0, 0.3); border-radius: 15px; padding: 15px;
            height: 350px; overflow-y: auto; display: flex; flex-direction: column-reverse;
        }
        .msg-bubble {
            padding: 10px 15px; border-radius: 15px; margin-bottom: 10px;
            max-width: 85%; font-size: 0.95rem;
        }
        .user-msg { background: #6200ea; color: white; align-self: flex-end; border-bottom-right-radius: 2px; margin-left: auto; }
        .ysis-msg { background: #212121; color: #ffccff; align-self: flex-start; border-bottom-left-radius: 2px; border: 1px solid #ff4ec2; }
    </style>
""", unsafe_allow_html=True)

# --- Estrutura da Página ---

st.markdown('<div class="title-text">YSIS</div>', unsafe_allow_html=True)

# AVISO DE ERRO DA API
if st.session_state.erro_api and not api_status:
    st.error(f"🚨 FALHA CRÍTICA DA IA! 🚨\n\nA Ysis está muda. Motivo: {st.session_state.erro_api}", icon="💔")

# 1. Área Visual (A Ysis)
st.markdown('<div class="media-box">', unsafe_allow_html=True)

if st.session_state.video_to_play and os.path.exists(st.session_state.video_to_play):
    with open(st.session_state.video_to_play, "rb") as v:
        video_b64 = base64.b64encode(v.read()).decode()
    st.markdown(f'<video autoplay loop muted playsinline><source src="data:video/mp4;base64,{video_b64}" type="video/mp4"></video>', unsafe_allow_html=True)
    # st.session_state.video_to_play = None # Se quiser que o vídeo rode apenas uma vez

else:
    img_path = st.session_state.imagem_atual
    if not os.path.exists(img_path):
        img_path = "static/ysis.jpg" 
    
    if os.path.exists(img_path):
        with open(img_path, "rb") as i:
            img_b64 = base64.b64encode(i.read()).decode()
        st.markdown(f'<img src="data:image/jpeg;base64,{img_b64}">', unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align:center; padding-top:50%;'>Imagem não encontrada 😢</p>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# 2. Área de Interação (Expansível)
with st.expander("🛍️ Loja & Guarda-Roupa", expanded=False):
    st.write(f"💰 **Saldo: {st.session_state.moedas} Moedas**")
    
    tab1, tab2 = st.tabs(["🛒 Comprar", "👗 Vestir"])
    
    loja = carregar_loja()
    
    with tab1:
        for item in loja:
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{item['nome']}**")
            if c2.button(f"{item['preco']} 💰", key=f"btn_{item['nome']}", on_click=comprar_item_acao, args=(item,)):
                st.rerun() 
    
    with tab2:
        roupas = st.session_state.guarda_roupa
        cols = st.columns(3)
        for idx, roupa in enumerate(roupas):
            if os.path.exists(roupa):
                with cols[idx % 3]:
                    st.image(roupa, use_container_width=True)
                    if st.button("Usar", key=f"use_{idx}", on_click=vestir_roupa_acao, args=(roupa,)):
                        st.rerun()

# 3. Área de Chat
chat_container = st.container()
with chat_container:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    # Exibe as mensagens na ordem correta (de baixo para cima)
    for msg in reversed(st.session_state.chat_history): 
        css_class = "user-msg" if msg["role"] == "user" else "ysis-msg"
        st.markdown(f'<div class="msg-bubble {css_class}">{msg["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# 4. Input e Áudio Invisível
st.text_input("Converse com a Ysis...", key="input_user", on_change=enviar_mensagem)

if st.session_state.audio_to_play:
    st.audio(st.session_state.audio_to_play, format="audio/mp3", autoplay=True)
    st.session_state.audio_to_play = None
