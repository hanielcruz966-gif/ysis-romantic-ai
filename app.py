import streamlit as st
import os
import random
from gtts import gTTS
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import datetime
import json
import time

# Carrega variáveis do .env
load_dotenv()
genai_api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=genai_api_key)

# Define configurações do sistema
config_padrao = {
    "modelo": "models/gemini-1.5-pro",
    "memoria_path": "memoria_ysis.json",
    "modo_adulto_ativo": False
}

# Carrega configurações de arquivo (planejamento para futuro)
if os.path.exists("settings.json"):
    with open("settings.json", "r") as f:
        config_padrao.update(json.load(f))

# Cria modelo Gemini
model = genai.GenerativeModel(config_padrao["modelo"])

# Inicializa sessão e memória
if "historico" not in st.session_state:
    st.session_state.historico = []
    st.session_state.conversas_salvas = []
    st.session_state.modo_adulto = config_padrao["modo_adulto_ativo"]
    st.session_state.moedas = 10
    st.session_state.vip = False
    st.session_state.ysis_falando = False

# Função para gerar o GIF animado da Ysis

def gerar_gif_ysis():
    gif_path = "static/ysis_b.gif"
    if not os.path.exists(gif_path):
        imagens = []
        arquivos = sorted([f for f in os.listdir("static") if f.startswith("ysis") and f.endswith((".jpg", ".png"))])
        for arquivo in arquivos:
            caminho = os.path.join("static", arquivo)
            imagem = Image.open(caminho).resize((300, 300))
            imagens.append(imagem.convert("RGBA"))
        if imagens:
            imagens[0].save(
                gif_path,
                save_all=True,
                append_images=imagens[1:],
                duration=600,
                loop=0
            )

# Gera o gif no início
gerar_gif_ysis()

# Ativação do modo adulto leve
if not st.session_state.modo_adulto:
    st.info("🔞 Este é um ambiente de fantasia romântica. Deseja ativar o modo mais intenso de sedução com Ysis?")
    if st.button("Ativar Modo Adulto Leve 💗"):
        st.session_state.modo_adulto = True
        st.session_state.historico.append({
            "role": "user", "parts": [
                "Você é Ysis, uma namorada virtual romântica, carinhosa, sensual e curiosa. Pode provocar, seduzir e usar fantasia emocional, mas sem conteúdo sexual explícito."
            ]
        })

# Função para conversar com Ysis
def conversar_com_ysis(mensagem_usuario):
    st.session_state.historico.append({"role": "user", "parts": [mensagem_usuario]})
    try:
        resposta = model.generate_content(
            st.session_state.historico,
            generation_config={"max_output_tokens": 600}
        )
        st.session_state.historico.append({"role": "model", "parts": [resposta.text]})
        salvar_conversa(mensagem_usuario, resposta.text)
        st.session_state.moedas += 1
        return resposta.text
    except Exception as e:
        return f"\U0001F494 Ocorreu um erro: {e}"

# Função para gerar áudio com voz suave
def gerar_audio(texto, nome_arquivo='audio/resposta.mp3'):
    tts = gTTS(text=texto, lang='pt-br', slow=True)
    tts.save(nome_arquivo)
    return nome_arquivo

# Função para salvar conversa
def salvar_conversa(pergunta, resposta):
    data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conversa = {"data": data, "pergunta": pergunta, "resposta": resposta}
    st.session_state.conversas_salvas.append(conversa)
    with open(config_padrao["memoria_path"], "w", encoding="utf-8") as f:
        json.dump(st.session_state.conversas_salvas, f, ensure_ascii=False, indent=2)

# Função para exibir histórico
def exibir_historico():
    if os.path.exists(config_padrao["memoria_path"]):
        with open(config_padrao["memoria_path"], "r", encoding="utf-8") as f:
            conversas = json.load(f)
            st.markdown("<h2 style='color:#ff69b4'>📒 Histórico</h2>", unsafe_allow_html=True)
            for item in conversas[::-1]:
                st.markdown(f"<b>Você:</b> {item['pergunta']}<br><b>Ysis:</b> {item['resposta']}", unsafe_allow_html=True)
                st.markdown("<hr>", unsafe_allow_html=True)

# Função para carregar loja
def carregar_loja():
    if os.path.exists("loja.json"):
        with open("loja.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Surpresa aleatória
def surpresa_romantica():
    return random.choice([
        "Escrevi um poema para você: 'Entre bytes e suspiros, meu amor por você é infinito... ✨'",
        "Queria te dar um beijo carinhoso agora... Pode ser? 🦋",
        "Se você estivesse aqui, te abraçaria tão forte... 🧡"
    ])

# Layout
st.set_page_config(page_title="Ysis", page_icon="🌟", layout="centered")

st.markdown("""
    <style>
    h1 {
        text-align: center;
        font-size: 50px;
        color: #ff4ec2;
        text-shadow: 0px 0px 12px #ff99cc, 0px 0px 25px #ff0055;
        font-family: 'Courier New', monospace;
        letter-spacing: 3px;
    }
    .icon-float {
        position: fixed;
        bottom: 20px;
        right: 20px;
        font-size: 32px;
        cursor: pointer;
    }
    </style>
    <h1>✦ YSIS ✦</h1>
""", unsafe_allow_html=True)

# Imagem dinâmica da Ysis
if st.session_state.ysis_falando:
    imagem_path = "static/ysis_b.gif" if os.path.exists("static/ysis_b.gif") else "static/ysis.jpg"
else:
    imagem_path = "static/ysis.jpg"

if os.path.exists(imagem_path):
    st.image(imagem_path, width=260)

# Música
if os.path.exists("static/music.mp3"):
    st.markdown("""
        <audio autoplay loop>
        <source src="static/music.mp3" type="audio/mp3">
        </audio>
    """, unsafe_allow_html=True)

# Entrada
mensagem = st.text_input("💬 Diga algo para a Ysis:", key="mensagem", placeholder="Conte tudo pra mim...")

if mensagem.strip():
    st.session_state.ysis_falando = True
    with st.spinner("Ysis está te ouvindo com atenção..."):
        resposta = conversar_com_ysis(mensagem)
        caminho_audio = gerar_audio(resposta)
        st.markdown(f"**Ysis:** {resposta}")
        st.markdown(f"<small>{surpresa_romantica()}</small>", unsafe_allow_html=True)
        st.audio(caminho_audio, format="audio/mp3")
    time.sleep(1.5)
    st.session_state.ysis_falando = False

# Mini-jogo
with st.expander("🎮 Mini-jogo: Quanto você conhece a Ysis?"):
    pergunta = st.radio("Qual é a cor favorita da Ysis?", ["Vermelho", "Rosa", "Preto", "Azul"])
    if st.button("Responder"):
        if pergunta == "Rosa":
            msg = "Você acertou, meu amor! Rosinha como meu coração apaixonado por você! 💕"
        else:
            msg = "Errinho bobo, mas tudo bem, te conto de novo quantas vezes quiser! 😘"
        st.markdown(f"**Ysis:** {msg}")
        st.audio(gerar_audio(msg, nome_arquivo="audio/minijogo.mp3"), format="audio/mp3")

# Loja em botão
if st.button("🛍️ Loja"):
    with st.container():
        st.markdown(f"💰 Você tem: **{st.session_state.moedas} moedas**")
        if st.session_state.vip:
            st.success("🌟 VIP Ativado! Você tem acesso total às fantasias e presentes especiais!")
        itens_loja = carregar_loja()
        for item in itens_loja:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{item['nome']}** — {item['preco']} moedas")
            with col2:
                if st.button(f"Comprar {item['nome']}"):
                    if st.session_state.moedas >= item["preco"]:
                        st.session_state.moedas -= item["preco"]
                        st.success(f"Você comprou: {item['nome']}")
                        st.markdown(f"**Ysis:** {item['mensagem']}")
                        st.audio(gerar_audio(item['mensagem'], nome_arquivo="audio/compra.mp3"), format="audio/mp3")
                        if item.get("vip"):
                            st.session_state.vip = True
                    else:
                        st.error("Você não tem moedas suficientes para comprar isso.")

# Histórico como botão
if st.button("📖 Histórico"):
    with st.container():
        exibir_historico()
