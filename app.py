import streamlit as st
import os
import json
import time
import random
import datetime
from pathlib import Path
from dotenv import load_dotenv

# --- Importação Segura das Bibliotecas ---
# Isso evita que o app quebre se uma biblioteca não for encontrada.
try:
    import google.generativeai as genai
except ImportError:
    st.error("Biblioteca do Google Gemini não encontrada. Verifique seu `requirements.txt`.")
    st.stop()

try:
    from openai import OpenAI
except ImportError:
    st.error("Biblioteca da OpenAI não encontrada. Verifique seu `requirements.txt`.")
    st.stop()

try:
    from gtts import gTTS
except ImportError:
    st.error("Biblioteca gTTS não encontrada. Verifique seu `requirements.txt`.")
    st.stop()

try:
    from PIL import Image
except ImportError:
    st.error("Biblioteca Pillow não encontrada. Verifique seu `requirements.txt`.")
    st.stop()

# --- Configuração Inicial e Chaves de API ---
load_dotenv()

# Carrega as chaves do ambiente (local) ou dos "Secrets" (Streamlit Cloud)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configura o cliente do Gemini (IA Principal)
gemini_model = None
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel("models/gemini-1.5-pro")
    except Exception as e:
        st.warning(f"Não foi possível configurar o Gemini. Verifique sua chave. Erro: {e}")

# Configura o cliente da OpenAI (IA de Reserva)
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        st.warning(f"Não foi possível configurar a OpenAI. Verifique sua chave. Erro: {e}")

# Cria pastas necessárias
os.makedirs("audio", exist_ok=True)
os.makedirs("static", exist_ok=True)

# --- Estado da Sessão (Memória do App) ---
if "historico" not in st.session_state:
    st.session_state.historico = []
    st.session_state.moedas = 10
    st.session_state.vip = False
    st.session_state.ysis_falando = False
    st.session_state.show_shop = False
    st.session_state.show_history = False
    st.session_state.imagem_atual = "static/ysis.jpg"

    # Define a personalidade inicial da Ysis
    st.session_state.historico.append(
        {"role": "system", "parts": ["Você é Ysis, uma namorada virtual romântica, carinhosa, sensual e curiosa. Fale com doçura, interesse e use emojis. Nunca encerre a conversa."]}
    )

# --- Funções Auxiliares (Loja, Áudio, Salvar Conversa) ---

def carregar_loja():
    if os.path.exists("loja.json"):
        with open("loja.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return [] # Retorna lista vazia se o arquivo não existir

def gerar_audio(texto, nome_arquivo):
    try:
        tts = gTTS(text=texto, lang='pt-br', slow=True)
        tts.save(nome_arquivo)
        return nome_arquivo
    except Exception as e:
        print(f"Erro ao gerar áudio: {e}")
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

# --- Função Principal de Conversa (com Fallback) ---

def conversar_com_ysis(mensagem_usuario):
    # Respostas rápidas para comandos específicos
    if "trocar de roupa" in mensagem_usuario.lower():
        return "Para trocar minha roupa, você pode usar a lojinha, meu amor... Lá tem umas surpresas pra você. 😈"
    if "dança" in mensagem_usuario.lower():
        return "Claro! Coloca uma música que eu danço só pra você... qual ritmo você quer? 💃"

    st.session_state.historico.append({"role": "user", "parts": [mensagem_usuario]})

    texto_resposta = None

    # 1. Tenta usar o Gemini (IA Principal)
    if gemini_model:
        try:
            resposta_gemini = gemini_model.generate_content(
                st.session_state.historico,
                generation_config={"max_output_tokens": 800}
            )
            texto_resposta = resposta_gemini.text.strip()
        except Exception as e:
            print(f"Erro no Gemini: {e}") # Loga o erro para debug

    # 2. Se o Gemini falhar, tenta usar a OpenAI (IA de Reserva)
    if not texto_resposta and openai_client:
        st.info("Usando IA de reserva...")
        try:
            mensagens_openai = [{"role": h["role"], "content": h["parts"][0]} for h in st.session_state.historico if h['role'] != 'system']
            resposta_openai = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=mensagens_openai
            )
            texto_resposta = resposta_openai.choices[0].message.content.strip()
        except Exception as e:
            print(f"Erro na OpenAI: {e}") # Loga o erro

    # 3. Se tudo falhar, usa uma resposta local
    if not texto_resposta:
        texto_resposta = "Meu bem, estou com a conexão um pouco instável agora... mas continue falando comigo, estou te ouvindo com todo o carinho. ❤️"

    st.session_state.historico.append({"role": "model", "parts": [texto_resposta]})
    salvar_conversa(mensagem_usuario, texto_resposta)
    st.session_state.moedas += 1
    return texto_resposta

# --- Interface Gráfica (Layout do App) ---

st.set_page_config(page_title="Ysis", page_icon="💖", layout="centered")

# Título e Botões Superiores
col1, col2, col3 = st.columns([2, 0.5, 0.5])
with col1:
    st.markdown("<h1 style='text-align: center; color: #ff4ec2; text-shadow: 0 0 10px #ff99cc;'>✦ YSIS ✦</h1>", unsafe_allow_html=True)
with col2:
    if st.button("🛍️", help="Loja"):
        st.session_state.show_shop = not st.session_state.show_shop
with col3:
    if st.button("📜", help="Histórico"):
        st.session_state.show_history = not st.session_state.show_history

# Painel da Loja
if st.session_state.show_shop:
    with st.expander("🛍️ Loja Romântica", expanded=True):
        st.markdown(f"**Você tem: {st.session_state.moedas} 💰 moedas**")
        itens_loja = carregar_loja()
        for item in itens_loja:
            if st.button(f"Comprar: {item['nome']} ({item['preco']} moedas)"):
                if st.session_state.moedas >= item["preco"]:
                    st.session_state.moedas -= item["preco"]
                    st.success(f"Você presenteou a Ysis com: {item['nome']}!")
                    st.markdown(f"**Ysis:** {item['mensagem']}")
                    if "imagem" in item and os.path.exists(item["imagem"]):
                        st.session_state.imagem_atual = item["imagem"] # Troca a imagem
                    audio_path = gerar_audio(item["mensagem"], f"audio/compra_{item['nome']}.mp3")
                    if audio_path:
                        st.audio(audio_path)
                    if item.get("vip"):
                        st.session_state.vip = True
                        st.balloons()
                else:
                    st.error("Moedas insuficientes, meu amor...")

# Painel do Histórico
if st.session_state.show_history:
    with st.expander("📜 Histórico de Conversas", expanded=True):
        if os.path.exists("memoria_ysis.json"):
            with open("memoria_ysis.json", "r", encoding="utf-8") as f:
                conversas = json.load(f)
            for c in reversed(conversas[-10:]): # Mostra as últimas 10 conversas
                st.markdown(f"**Você:** {c['pergunta']}")
                st.markdown(f"**Ysis:** {c['resposta']}")
                st.markdown("---")
        else:
            st.info("Ainda não temos um histórico salvo.")

# Imagem da Ysis
imagem_para_exibir = st.session_state.imagem_atual
if st.session_state.ysis_falando and os.path.exists("static/ysis_b.gif"):
    imagem_para_exibir = "static/ysis_b.gif"

if os.path.exists(imagem_para_exibir):
    st.image(imagem_para_exibir, use_column_width=True)

# Entrada de Mensagem
mensagem = st.text_input("💬 Diga algo para a Ysis...", key="mensagem_input", label_visibility="collapsed")

if mensagem:
    st.session_state.ysis_falando = True
    st.rerun() # Atualiza a imagem para o GIF

if st.session_state.ysis_falando:
    with st.spinner("Ysis está pensando com carinho..."):
        resposta = conversar_com_ysis(mensagem)
        st.markdown(f"**Ysis:** {resposta}")
        audio_path = gerar_audio(resposta, "audio/resposta.mp3")
        if audio_path:
            st.audio(audio_path, autoplay=True)
    
    st.session_state.ysis_falando = False
    st.session_state.imagem_atual = "static/ysis.jpg" # Volta para a imagem padrão
    st.rerun() # Limpa o campo de texto e atualiza a imagem
