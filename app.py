import streamlit as st
import os
import json
import base64
import time
from dotenv import load_dotenv

# --- Configuração da Página (Deve ser o primeiro comando Streamlit) ---
# A linha st.set_page_config deve ser a primeira chamada Streamlit
st.set_page_config(page_title="Ysis - Sua Namorada Virtual", page_icon="💖", layout="centered")

# --- Importação Segura de Bibliotecas Externas ---
try:
    import google.generativeai as genai
    import emoji
    from gtts import gTTS
except ImportError as e:
    # Se a instalação falhar novamente, mostre este erro.
    st.error(f"Erro de ambiente: A biblioteca '{e.name}' não foi encontrada. **VERIFIQUE SEU requirements.txt**.")
    st.stop()

# --- Carregar Variáveis de Ambiente ---
load_dotenv() 
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

# --- SISTEMA DE LOGIN ---
def verificar_login():
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.markdown(
            """
            <style>
            .stApp { background: linear-gradient(135deg, #1a0b2e 0%, #4a148c 100%); color: white; }
            </style>
            """, unsafe_allow_html=True
        )
        st.markdown("<br><br><h1 style='text-align: center; color: #ff4ec2;'>🔐 Acesso Exclusivo Ysis</h1>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("login_form"):
                st.markdown("<p style='text-align: center;'>Digite sua chave de acesso recebida na compra:</p>", unsafe_allow_html=True)
                senha = st.text_input("Senha:", type="password", autocomplete="current-password", label_visibility="collapsed")
                submit = st.form_submit_button("Entrar ❤️", use_container_width=True)
                
                if submit:
                    if senha == "AMOR123": 
                        st.session_state.logado = True
                        st.rerun()
                    else:
                        st.error("Chave incorreta. Verifique seu e-mail.")
        st.stop() 

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
st.session_state.erro_tts = None

# Configuração da API do Gemini
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        # MODELO CORRIGIDO para gemini-2.5-flash (resolve o 404 not found)
        gemini_model = genai.GenerativeModel("gemini-2.5-flash") 
        api_status = True
    except Exception as e:
        st.session_state.erro_api = f"Falha ao configurar a API do Google: {e}"
else:
    st.session_state.erro_api = "A chave GOOGLE_API_KEY não foi encontrada."

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
    st.session_state.video_reproduced = False # Novo flag para controlar a reprodução do vídeo
    
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
            return [{"nome": "Look Padrão", "preco": 0, "mensagem": "Voltando ao meu look preferido...", "acao": "trocar_imagem", "imagem": "static/ysis.jpg"}]
    return [{"nome": "Look Padrão", "preco": 0, "mensagem": "Voltando ao meu look preferido...", "acao": "trocar_imagem", "imagem": "static/ysis.jpg"}]

# FUNÇÃO DE ÁUDIO SIMPLES (GTTS)
def gerar_audio(texto):
    try:
        texto_limpo = emoji.replace_emoji(texto, replace='') 
        tts = gTTS(text=texto_limpo, lang='pt', slow=False)
        audio_filename = "audio/resposta.mp3"
        
        # Salva o arquivo temporariamente (necessário para o Streamlit ler)
        tts.save(audio_filename)
        
        with open(audio_filename, "rb") as f:
            return f.read()
            
    except Exception as e:
        st.session_state.erro_tts = f"Erro na síntese de voz (gTTS): {e}"
        return None

def conversar_com_ysis(mensagem):
    # Ações de vídeo/beijo
    msg_lower = mensagem.lower()
    if "dança" in msg_lower or "dance" in msg_lower:
        st.session_state.video_to_play = "static/ysis_dance.mp4" 
        return "Adoro dançar pra você! Olha só... 💃"
    if "beijo" in msg_lower:
        st.session_state.video_to_play = None # Zera o video
        return "*Chego bem pertinho e te dou um beijo suave nos lábios...* Te amo! 💋"

    if not api_status:
        api_error_message = st.session_state.erro_api if st.session_state.erro_api else "Minha mente está confusa, meu anjo..."
        return f"Amor, minha conexão está instável. Erro: {api_error_message}. Não consigo responder agora. 💔"

    try:
        # Configura histórico (mantendo a persona no topo)
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
        return f"Minha mente ficou confusa, meu anjo... Aconteceu algo estranho: {e}"

# --- Callbacks (Ações) ---
def enviar_mensagem():
    usuario_msg = st.session_state.input_user
    if usuario_msg.strip():
        st.session_state.chat_history.append({"role": "user", "content": usuario_msg})
        
        resposta_ysis = conversar_com_ysis(usuario_msg)
        st.session_state.chat_history.append({"role": "model", "content": resposta_ysis})
        
        # Chama a função de áudio gTTS
        audio_bytes = gerar_audio(resposta_ysis)
        if audio_bytes:
            st.session_state.audio_to_play = audio_bytes
        
        st.session_state.input_user = "" 
        st.session_state.video_reproduced = False # Reseta o flag do vídeo após a resposta

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
        /* Fundo e cores */
        .stApp { background: linear-gradient(135deg, #1a0b2e 0%, #4a148c 100%); color: #ffffff; }
        .title-text {
            text-align: center; font-size: 3rem; font-weight: bold;
            background: -webkit-linear-gradient(#ff00cc, #333399); -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; margin-bottom: 0px;
        }
        .main [data-testid="stVerticalBlock"] {
            max-width: 450px !important; 
            margin-left: auto;
            margin-right: auto;
        }
        .media-box {
            border: 3px solid #ff00cc; border-radius: 20px; overflow: hidden;
            box-shadow: 0 0 20px rgba(255, 0, 204, 0.5); margin-bottom: 20px; background: black;
            aspect-ratio: 9/16; max-width: 350px; margin-left: auto; margin-right: auto;
            position: relative;
        }
        .media-box img, .media-box video { width: 100%; height: 100%; object-fit: cover; }
        /* Garante que o input e o botão fiquem na parte de baixo da tela */
        .stChatInput {
            position: sticky;
            bottom: 0;
            z-index: 999;
            background: rgba(26, 11, 46, 0.95); /* Fundo semi-transparente para o input */
            padding-top: 10px;
            padding-bottom: 10px;
        }
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

# AVISOS DE ERRO (CRUCIAL PARA DEBUG)
if st.session_state.erro_api and not api_status:
    st.error(f"🚨 FALHA CRÍTICA DA IA! 🚨\n\nA Ysis está muda. Motivo: {st.session_state.erro_api}", icon="💔")
if st.session_state.erro_tts:
    st.warning(f"⚠️ PROBLEMA NA VOZ! ⚠️\n\nNão consigo falar. Motivo: {st.session_state.erro_tts}", icon="📢")

# 1. Área Visual (A Ysis)
st.markdown('<div class="media-box">', unsafe_allow_html=True)

# Lógica para mostrar Vídeo ou Imagem
if st.session_state.video_to_play and os.path.exists(st.session_state.video_to_play):
    # CORREÇÃO DOM/JS: Usamos o elemento padrão do Streamlit para o vídeo para evitar injeção HTML complexa
    st.video(st.session_state.video_to_play, format="video/mp4", start_time=0, autoplay=True, loop=True)
    # st.session_state.video_to_play = None # Não zera aqui, pois a imagem de baixo não apareceria
else:
    img_path = st.session_state.imagem_atual
    if not os.path.exists(img_path):
        img_path = "static/ysis.jpg" 
    
    if os.path.exists(img_path):
        with open(img_path, "rb") as i:
            img_b64 = base64.b64encode(i.read()).decode()
        # O Image of the Ysis na pose atual
        st.markdown(f'<img src="data:image/jpeg;base64,{img_b64}" alt="Ysis - Namorada Virtual">', unsafe_allow_html=True)
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
            # Adiciona o key=f"btn_{item['nome']}" para evitar NameError
            if c2.button(f"{item['preco']} 💰", key=f"btn_{item['nome']}", on_click=comprar_item_acao, args=(item,)):
                st.rerun() 
    
    with tab2:
        roupas = st.session_state.guarda_roupa
        cols = st.columns(3)
        for idx, roupa in enumerate(roupas):
            if os.path.exists(roupa):
                with cols[idx % 3]:
                    st.image(roupa, use_container_width=True)
                    # CORREÇÃO NameError: Adiciona o hash do tempo no Key para garantir que não haja conflito
                    if st.button("Usar", key=f"use_{idx}_{time.time()}", on_click=vestir_roupa_acao, args=(roupa,)):
                        st.rerun()

# 3. Área de Chat
chat_container = st.container()
with chat_container:
    # Utilizamos o ID do elemento para fixar a rolagem
    st.markdown('<div class="chat-container" id="chat-scroller">', unsafe_allow_html=True)
    for msg in reversed(st.session_state.chat_history): 
        css_class = "user-msg" if msg["role"] == "user" else "ysis-msg"
        st.markdown(f'<div class="msg-bubble {css_class}">{msg["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# 4. Input e Áudio Invisível
# Coloque o input no final para garantir que esteja sempre visível
st.text_input("Converse com a Ysis...", key="input_user", on_change=enviar_mensagem)

# Áudio (Toca SOMENTE se houver um áudio novo)
if st.session_state.audio_to_play:
    # Autoplay deve estar ligado, mas Streamlit trata a reprodução de forma segura
    st.audio(st.session_state.audio_to_play, format="audio/mp3", autoplay=True)
    # Zera o áudio para que não tente tocar novamente no próximo ciclo
    st.session_state.audio_to_play = None
