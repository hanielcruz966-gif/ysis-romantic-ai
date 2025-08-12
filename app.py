# app.py
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
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# -------------------------
# Config e inicialização
# -------------------------
load_dotenv()  # carrega .env
GENAI_API_KEY = os.getenv("GOOGLE_API_KEY")

# avisa se não tiver chave
if not GENAI_API_KEY:
    st.warning("Chave da API do Google (GOOGLE_API_KEY) não encontrada no .env. Coloque a chave e reinicie a app.")
else:
    try:
        genai.configure(api_key=GENAI_API_KEY)
    except Exception as e:
        st.error(f"Erro ao configurar API Gemini: {e}")

# diretórios úteis
os.makedirs("audio", exist_ok=True)
os.makedirs("static", exist_ok=True)

# configuração padrão (pode ser sobrescrita por settings.json)
config_padrao = {
    "modelo": "models/gemini-1.5-pro",   # sugestão: gemini-1.5-pro para conversas longas e naturais
    "memoria_path": "memoria_ysis.json",
    "modo_adulto_ativo": False,
    "tema": "romantico",
    "audio_suave": True,
    "surpresas_romanticas": True,
    "jogos_ativos": True,
    "log_conversas": True,
    "timeout_segundos": 15,
    "max_history_messages": 30
}

# Se houver settings.json, leia com segurança (aceita só dict)
if os.path.exists("settings.json"):
    try:
        with open("settings.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                config_padrao.update(data)
            else:
                # se settings.json for um array (ex: loja), ignore para config
                st.info("settings.json não é um objeto de configuração — ignorando para configurações.")
    except Exception as e:
        st.warning(f"Erro lendo settings.json: {e}")

# instancia modelo (cairá em erro se chave inválida)
model = None
try:
    model = genai.GenerativeModel(config_padrao["modelo"])
except Exception:
    # deixamos None e tratamos depois
    model = None

# -------------------------
# Estado inicial de sessão
# -------------------------
if "historico" not in st.session_state:
    st.session_state.historico = []
    st.session_state.conversas_salvas = []
    st.session_state.modo_adulto = config_padrao["modo_adulto_ativo"]
    st.session_state.moedas = 10
    st.session_state.vip = False
    st.session_state.ysis_falando = False
    st.session_state.show_shop = False
    st.session_state.show_history = False
    st.session_state.last_interaction = time.time()
    st.session_state.persona_initialized = False

# inicializa persona (uma vez)
if not st.session_state.persona_initialized:
    persona_prompt = (
        "Você é Ysis, uma namorada virtual romântica, carinhosa, curiosa e levemente provocante. "
        "Seja sempre respeitosa e não produza conteúdo sexual explícito neste modo. "
        "Inclua emojis moderadamente, demonstre interesse pelos gostos do usuário e proponha perguntas abertas."
    )
    st.session_state.historico.append({"role": "system", "parts": [persona_prompt]})
    st.session_state.persona_initialized = True

# -------------------------
# Helpers
# -------------------------
def safe_load_loja():
    if os.path.exists("loja.json"):
        try:
            with open("loja.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    # loja padrão mínima
    return [
        {"nome": "Poema Apaixonado", "preco": 5, "mensagem": "Entre as estrelas, meu amor por você brilha mais forte. 💖"},
        {"nome": "Fantasia de Anjo", "preco": 8, "mensagem": "Você gostaria de me ver como um anjo, meu amor? 😇"},
        {"nome": "Presente Surpresa", "preco": 10, "mensagem": "Essa surpresa é tão especial quanto você... 🎁"},
        {"nome": "Acesso VIP 💎", "preco": 15, "mensagem": "Agora você tem acesso VIP a fantasias e textos especiais.", "vip": True}
    ]

def gerar_audio(texto, nome_arquivo='audio/resposta.mp3'):
    """Gera mp3 com gTTS e retorna caminho (procura parametrização slow)"""
    try:
        slow_flag = bool(config_padrao.get("audio_suave", True))
        tts = gTTS(text=texto, lang='pt-br', slow=slow_flag)
        tts.save(nome_arquivo)
        return nome_arquivo
    except Exception as e:
        # falhou: retorna None (não interrompe a app)
        st.warning(f"Falha ao gerar áudio: {e}")
        return None

def salvar_conversa(pergunta, resposta):
    if not config_padrao.get("log_conversas", True):
        return
    data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conversa = {"data": data, "pergunta": pergunta, "resposta": resposta}
    st.session_state.conversas_salvas.append(conversa)
    try:
        with open(config_padrao["memoria_path"], "w", encoding="utf-8") as f:
            json.dump(st.session_state.conversas_salvas, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Erro salvando memória: {e}")

def exibir_historico_ui():
    """Mostra histórico salvo (leitura do arquivo)"""
    path = config_padrao["memoria_path"]
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                conversas = json.load(f)
        except Exception:
            conversas = []
    else:
        conversas = st.session_state.conversas_salvas or []

    if not conversas:
        st.info("Nenhuma conversa salva ainda.")
        return

    st.markdown("<div style='background: rgba(0,0,0,0.25); padding:12px; border-radius:10px; max-height:60vh; overflow:auto;'>", unsafe_allow_html=True)
    last_date = ""
    for item in reversed(conversas):
        date = item.get("data", "").split(" ")[0]
        if date != last_date:
            st.markdown(f"<h4 style='color:#ffb6d5'>{date}</h4>", unsafe_allow_html=True)
            last_date = date
        st.markdown(f"**Você:** {item['pergunta']}  \n**Ysis:** {item['resposta']}")
        st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def criar_gif_from_static(prefix="ysis"):
    """Se houver várias imagens static/ysis_*.png | .jpg cria um gif simples (se não existir)."""
    gif_path = "static/ysis_b.gif"
    if os.path.exists(gif_path):
        return gif_path
    try:
        arquivos = sorted([f for f in os.listdir("static") if f.startswith(prefix) and f.lower().endswith((".jpg", ".png"))])
        imagens = []
        for a in arquivos:
            caminho = os.path.join("static", a)
            try:
                img = Image.open(caminho).convert("RGBA").resize((400,400))
                imagens.append(img)
            except Exception:
                continue
        if imagens:
            imagens[0].save(gif_path, save_all=True, append_images=imagens[1:], duration=600, loop=0)
            return gif_path
    except Exception:
        pass
    return None

# cria gif (opcional)
gif_generated = criar_gif_from_static()

# -------------------------
# Função para chamar o modelo com timeout
# -------------------------
def _call_model_generate(payload, max_tokens=500, is_history=True):
    """Chama a API do Gemini (blocking)."""
    if model is None:
        raise RuntimeError("Modelo Gemini não inicializado (verifique a chave).")
    if is_history:
        # payload é a lista de mensagens
        return model.generate_content(payload, generation_config={"max_output_tokens": max_tokens})
    else:
        # payload é um single prompt string
        return model.generate_content([{"role":"user","parts":[payload]}], generation_config={"max_output_tokens": max_tokens})

def gerar_resposta_com_timeout(history_or_prompt, timeout_seconds=None, max_tokens=500, is_history=True):
    """Executa _call_model_generate em thread e aplica timeout (funciona no Streamlit Cloud)."""
    timeout_seconds = timeout_seconds or config_padrao.get("timeout_segundos", 15)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_call_model_generate, history_or_prompt, max_tokens, is_history)
        try:
            result = future.result(timeout=timeout_seconds)
            return result
        except FuturesTimeout:
            future.cancel()
            raise TimeoutError("Timeout ao gerar resposta (demorou demais).")
        except Exception as e:
            # re-raise para camada superior tratar
            raise e

# -------------------------
# Lógica de conversa
# -------------------------
def resumir_memoria_se_necessario():
    """Se o histórico ficar grande, pede ao modelo um resumo curto para reduzir contexto."""
    try:
        max_msgs = config_padrao.get("max_history_messages", 30)
        if len(st.session_state.historico) > max_msgs:
            # extrai as últimas user parts para resumo
            partes = [h["parts"][0] for h in st.session_state.historico if h.get("role") == "user"]
            texto = "\n".join(partes[-20:])
            prompt_resumo = "Resuma em 1-2 frases, de forma romântica e emocional, o contexto desta relação e os pontos importantes:"
            prompt_resumo += "\n\n" + texto
            try:
                resp = gerar_resposta_com_timeout(prompt_resumo, timeout_seconds=10, max_tokens=200, is_history=False)
                resumo_text = getattr(resp, "text", str(resp))
                st.session_state.historico = [{"role": "system", "parts": ["Resumo da relação: " + resumo_text]}]
            except Exception:
                # se falhar, corta o histórico mantendo as últimas mensagens
                st.session_state.historico = st.session_state.historico[-max_msgs:]
    except Exception:
        pass

def conversar_com_ysis(mensagem_usuario):
    # atualiza último tempo de interação
    st.session_state.last_interaction = time.time()

    # perguntas especiais simples (respostas rápidas sem chamar API)
    low = mensagem_usuario.lower()
    if "trocar de roupa" in low or "troca de roupa" in low:
        resposta = "Claro, vou colocar algo que sei que você ama... 😘"
        salvar_conversa(mensagem_usuario, resposta)
        return resposta
    if "dança" in low:
        resposta = "Ligando a música... dançarei só para você, meu amor. 💃"
        salvar_conversa(mensagem_usuario, resposta)
        return resposta

    # adiciona ao histórico e chama modelo (com timeout)
    st.session_state.historico.append({"role": "user", "parts": [mensagem_usuario]})

    # reduzir histórico se muito longo (antes de enviar)
    resumir_memoria_se_necessario()

    try:
        # gera resposta com timeout
        resp = gerar_resposta_com_timeout(st.session_state.historico, timeout_seconds=config_padrao.get("timeout_segundos", 15), max_tokens=600, is_history=True)
        resposta_text = getattr(resp, "text", str(resp))
        st.session_state.historico.append({"role": "model", "parts": [resposta_text]})
        salvar_conversa(mensagem_usuario, resposta_text)
        # ganha moeda por interação
        st.session_state.moedas += 1
        return resposta_text
    except TimeoutError:
        fallback = "💖 Amor, a conexão ficou lenta agora — tô te devendo uma resposta caprichada. Pode tentar novamente?"
        salvar_conversa(mensagem_usuario, fallback)
        return fallback
    except Exception as e:
        fallback = f"💔 Ocorreu um erro ao gerar a resposta: {e}"
        salvar_conversa(mensagem_usuario, fallback)
        return fallback

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="Ysis", page_icon="✨", layout="centered", initial_sidebar_state="collapsed")

# estilo do título
st.markdown(
    """
    <style>
    .title {
        text-align:center;
        font-size:48px;
        color: #ff2d94;
        text-shadow: 0 0 8px #ff94c2, 0 0 20px #ff3366;
        font-weight:700;
        letter-spacing: 3px;
        margin-bottom: -10px;
    }
    .top-icons { display:flex; gap:8px; justify-content:flex-end; align-items:center; }
    .small-muted { color:#bbb; font-size:12px; }
    </style>
    """, unsafe_allow_html=True
)
# Top layout: título e ícones
col1, col2, col3 = st.columns([2, 0.6, 0.6])
with col1:
    st.markdown('<div class="title">✦ YSIS ✦</div>', unsafe_allow_html=True)
with col2:
    if st.button("🛍️ Loja", key="btn_loja"):
        st.session_state.show_shop = not st.session_state.show_shop
        st.session_state.show_history = False
with col3:
    if st.button("📜 Histórico", key="btn_histo"):
        st.session_state.show_history = not st.session_state.show_history
        st.session_state.show_shop = False

# exibe badges (moedas / vip)
st.markdown(f"**💰 Moedas:** {st.session_state.moedas}  &nbsp;&nbsp; {'🌟 VIP' if st.session_state.vip else ''}")

# imagem dinâmica
img_path = "static/ysis_b.gif" if (st.session_state.ysis_falando and os.path.exists("static/ysis_b.gif")) else "static/ysis.jpg"
if os.path.exists(img_path):
    st.image(img_path, width=300)

# música de fundo (opcional)
if os.path.exists("static/music.mp3"):
    st.markdown("""<audio autoplay loop style='display:none'><source src="static/music.mp3" type="audio/mp3"></audio>""", unsafe_allow_html=True)

# painel da loja (se aberto)
if st.session_state.show_shop:
    st.markdown("---")
    st.markdown("### 🛍️ Loja Romântica")
    st.markdown(f"Você tem **{st.session_state.moedas} moedas**")
    itens = safe_load_loja()
    for i, item in enumerate(itens):
        st.markdown(f"**{item['nome']}** — {item['preco']} moedas")
        col_a, col_b = st.columns([4,1])
        with col_b:
            if st.button("Comprar", key=f"buy_{i}"):
                if st.session_state.moedas >= item["preco"]:
                    st.session_state.moedas -= item["preco"]
                    st.success(f"Você comprou: {item['nome']}")
                    st.markdown(f"**Ysis:** {item['mensagem']}")
                    audio_path = gerar_audio(item['mensagem'], nome_arquivo=f"audio/compra_{i}.mp3")
                    if audio_path:
                        st.audio(audio_path, format="audio/mp3")
                    if item.get("vip"):
                        st.session_state.vip = True
                else:
                    st.error("Você não tem moedas suficientes.")
    st.markdown("---")

# painel histórico (se aberto)
if st.session_state.show_history:
    st.markdown("---")
    st.markdown("### 📜 Histórico de conversas")
    exibir_historico_ui()
    st.markdown("---")

# campo de entrada (num formulário para enviar com enter)
with st.form(key="chat_form", clear_on_submit=False):
    user_input = st.text_input("💬 Diga algo para a Ysis:", placeholder="Conte tudo pra mim...")
    submit = st.form_submit_button("Enviar")

if submit and user_input and user_input.strip():
    st.session_state.ysis_falando = True
    resposta = conversar_com_ysis(user_input.strip())
    st.markdown(f"**Ysis:** {resposta}")
    # surpresa romântica (opcional)
    if config_padrao.get("surpresas_romanticas", True):
        surp = random.choice([
            "Escrevi um poema para você: 'Entre bytes e suspiros, meu amor por você é infinito... ✨'",
            "Queria te dar um beijo carinhoso agora... Pode ser? 🦋",
            "Se você estivesse aqui, te abraçaria tão forte... 🧡"
        ])
        st.markdown(f"<small>{surp}</small>", unsafe_allow_html=True)
    # audio
    audio_path = gerar_audio(resposta, nome_arquivo="audio/resposta.mp3")
    if audio_path:
        st.audio(audio_path, format="audio/mp3")
    # volta para estado de "parada de fala" depois de curto delay
    time.sleep(1.0)
    st.session_state.ysis_falando = False

# mini-jogo (expansível)
if config_padrao.get("jogos_ativos", True):
    st.markdown("---")
    st.markdown("🎮 **Mini-jogo: Quanto você conhece a Ysis?**")
    colA, colB = st.columns([3,1])
    with colA:
        escolha = st.radio("Qual é a cor favorita da Ysis?", ["Vermelho", "Rosa", "Preto", "Azul"], key="quiz_color")
    with colB:
        if st.button("Responder (jogo)", key="play_btn"):
            if escolha == "Rosa":
                msg = "Você acertou, meu amor! Rosinha como meu coração apaixonado por você! 💕"
                st.success(msg)
            else:
                msg = "Errinho bobo, mas tudo bem, te conto de novo quantas vezes quiser! 😘"
                st.error(msg)
            audio_path = gerar_audio(msg, nome_arquivo="audio/minijogo.mp3")
            if audio_path:
                st.audio(audio_path, format="audio/mp3")

# rodapé / dicas
st.markdown("---")
st.markdown("<div class='small-muted'>Dica: clique no ícone da loja (🛍️) ou do histórico (📜) no topo para abrir painéis. Configure a sua chave no arquivo .env.</div>", unsafe_allow_html=True)
