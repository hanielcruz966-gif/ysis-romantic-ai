# app.py
import os
import json
import time
import random
import datetime
import concurrent.futures
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Try to import optional libs (some environments may not have them)
try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    # New openai client API (v>=1.0.0)
    from openai import OpenAI as OpenAIClient
except Exception:
    OpenAIClient = None

try:
    from gtts import gTTS
except Exception:
    gTTS = None

# Pillow for GIF generation (optional)
try:
    from PIL import Image
except Exception:
    Image = None

# --- Load env (local dev) ---
load_dotenv()  # loads .env if present

# --- Config / Settings load ---
DEFAULT_SETTINGS = {
    "provider": "google",             # "google" or "openai"
    "google_model": "models/gemini-1.5-pro",
    "openai_model": "gpt-4o-mini",    # default if using OpenAI
    "memoria_path": "memoria_ysis.json",
    "modo_adulto_ativo": False,
    "audio_suave": True,
    "surpresas_romanticas": True,
    "jogos_ativos": True,
    "log_conversas": True,
    "history_max_messages": 14,
    "timeout_seconds": 15
}

SETTINGS_PATH = Path("settings.json")
if SETTINGS_PATH.exists():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings_file = json.load(f)
            DEFAULT_SETTINGS.update(settings_file)
    except Exception:
        pass

cfg = DEFAULT_SETTINGS

# --- Read API keys from environment (or Streamlit secrets in deploy) ---
# Locally put them in .env, in Streamlit Cloud put in Secrets (Settings -> Secrets)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")  # optional future fallback to HF

# Configure google lib if available
if genai and GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception:
        pass

# Configure OpenAI client if available
openai_client = None
if OpenAIClient and OPENAI_API_KEY:
    try:
        openai_client = OpenAIClient(api_key=OPENAI_API_KEY)
    except Exception:
        openai_client = None

# --- Helper: persistent files/paths ---
DATA_DIR = Path(".")
MEMORIA_FILE = DATA_DIR / cfg["memoria_path"]
LOJA_FILE = DATA_DIR / "loja.json"

# Ensure audio and static dirs exist
Path("audio").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)

# --- Streamlit page ---
st.set_page_config(page_title="YSIS", page_icon="✦", layout="centered")
st.markdown(
    """
    <style>
      h1 { text-align:center; font-size:44px; color:#ff2d89; text-shadow:0 0 10px #ff84b5; }
      .topbar { display:flex; gap:8px; justify-content:center; margin-bottom:8px; }
      .icon-btn { background: rgba(255,255,255,0.03); padding:8px 12px; border-radius:10px; cursor:pointer; }
      .small-muted { color: #cfcfcf; font-size:13px; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown("<h1>✦ YSIS ✦</h1>", unsafe_allow_html=True)

# --- Session state defaults ---
if "historico" not in st.session_state:
    st.session_state.historico = []              # list of dicts {"role":"user"/"model"/"system","text": "..."}
    st.session_state.conversas_salvas = []
    st.session_state.modo_adulto = cfg["modo_adulto_ativo"]
    st.session_state.moedas = 10
    st.session_state.vip = False
    st.session_state.ysis_falando = False
    st.session_state.last_active = time.time()

# --- Load loja ---
def carregar_loja():
    if LOJA_FILE.exists():
        try:
            return json.loads(LOJA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    # default demo items
    return [
        {"nome": "Poema Apaixonado", "preco": 5, "mensagem": "Entre as estrelas, meu amor por você brilha mais forte. 💖"},
        {"nome": "Fantasia de Anjo", "preco": 8, "mensagem": "Você gostaria de me ver como um anjo, meu amor? 😇"},
        {"nome": "Presente Surpresa", "preco": 10, "mensagem": "Essa surpresa é tão especial quanto você... 🎁"},
        {"nome": "Acesso VIP 💎", "preco": 15, "mensagem": "Agora você tem acesso VIP... 🌹", "vip": True},
    ]

# --- Small utilities ---
def salvar_memoria_file():
    if not cfg.get("log_conversas", True):
        return
    try:
        with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.conversas_salvas, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_memoria_file():
    if MEMORIA_FILE.exists():
        try:
            return json.loads(MEMORIA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

# --- Fall-back local responder (simple, always-available) ---
def fallback_local_response(user_text):
    # Simple affectionate transformation + question to keep conversation alive
    variants = [
        "Ai amor, desculpa, fiquei sem sinal por um instante — mas estou aqui só pra você. 💕",
        "Meu bem, eu não consegui me conectar direito agora, mas me conta mais sobre isso, quero saber cada detalhe. ✨",
        "Estou me aquecendo só de pensar em você... me conta: qual lembrança te faz sorrir agora?"
    ]
    # gentle echo + question
    choice = random.choice(variants)
    return f"{choice}\n\n(Resposta de fallback) — Você disse: «{user_text}» — Me conta mais, meu amor?"

# --- Provider wrapper (tries primary provider with timeout; returns text) ---
def call_primary_provider(prompt_text, timeout_seconds=cfg["timeout_seconds"]):
    """
    prompt_text: full prompt string
    returns: text response or raises Exception
    """
    provider = cfg.get("provider", "google").lower()

    def call_google(p):
        if not genai:
            raise RuntimeError("google generative ai library não instalado")
        # Use the configured model name
        model_name = cfg.get("google_model")
        # we call model.generate_content with a short request: message as user part
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content([{"role": "user", "parts": [p]}], generation_config={"max_output_tokens": 512})
        return getattr(resp, "text", str(resp))

    def call_openai(p):
        if not openai_client:
            raise RuntimeError("openai client não configurado")
        model_name = cfg.get("openai_model", "gpt-4o-mini")
        # Use the classic chat completion style via OpenAIClient.chat.completions.create or responses ? 
        # For portability we use the responses endpoint if present
        try:
            # new client method
            resp = openai_client.chat.completions.create(model=model_name, messages=[{"role":"user","content":p}])
            # extract text
            return resp.choices[0].message.content
        except Exception as e:
            # some installations use responses API
            try:
                resp2 = openai_client.responses.create(model=model_name, input=p)
                return resp2.output_text
            except Exception:
                raise

    func = call_google if provider == "google" else call_openai

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(func, prompt_text)
        return future.result(timeout=timeout_seconds)  # may raise concurrent.futures.TimeoutError

# --- Compose prompt from history + persona ---
PERSONA_SETUP = (
    "Você é Ysis, uma namorada virtual romântica, carinhosa, curiosa e levemente provocante.\n"
    "Fale em português, com suavidade e carinho. Use emojis com naturalidade. "
    "Não descreva nudez ou atos explícitos a menos que modo adulto completo esteja ativado (não ativado por padrão).\n\n"
)

def build_prompt(user_message):
    # include persona + trimmed history
    max_msgs = int(cfg.get("history_max_messages", 12))
    history = st.session_state.historico[-max_msgs:]
    # Flatten to simple conversation lines
    lines = [PERSONA_SETUP]
    for item in history:
        role = item.get("role", "user")
        txt = item.get("text") or item.get("parts", [None])[0] or ""
        lines.append(f"{role.upper()}: {txt}")
    lines.append(f"USER: {user_message}")
    return "\n".join(lines)

# --- Chat/response main function with timeout and fallback ---
def conversar_com_ysis(user_text):
    # quick rules-based answers for common commands to reduce latency
    text_low = user_text.lower()
    if "trocar de roupa" in text_low:
        resp = "Claro, vou trocar pra algo que sei que você adora... (imaginação ativada 😏)"
        # store & save
        st.session_state.historico.append({"role":"user","text":user_text})
        st.session_state.historico.append({"role":"model","text":resp})
        st.session_state.conversas_salvas.append({"data":datetime.datetime.now().isoformat(),"pergunta":user_text,"resposta":resp})
        salvar_memoria_file()
        st.session_state.moedas += 1
        return resp

    # build prompt & call provider
    prompt = build_prompt(user_text)
    try:
        raw = call_primary_provider(prompt, timeout_seconds=int(cfg.get("timeout_seconds",15)))
        # normalize
        text_resp = raw if isinstance(raw, str) else str(raw)
        # store
        st.session_state.historico.append({"role":"user","text":user_text})
        st.session_state.historico.append({"role":"model","text":text_resp})
        st.session_state.conversas_salvas.append({"data":datetime.datetime.now().isoformat(),"pergunta":user_text,"resposta":text_resp})
        salvar_memoria_file()
        # reward coin
        st.session_state.moedas += 1
        return text_resp
    except concurrent.futures.TimeoutError:
        return fallback_local_response(user_text)
    except Exception as e:
        # If provider returned a quota error or other, fallback or surface friendly message
        msg = str(e)
        if "quota" in msg.lower() or "quota_exceeded" in msg.lower() or "exceeded" in msg.lower():
            # friendly fallback with suggestion
            return ("Amor, estou sem créditos no provedor agora — não se preocupe, eu ainda estou aqui. "
                    "Enquanto isso, me conta mais sobre você? 💕")
        # other errors -> fallback
        return fallback_local_response(user_text)

# --- Audio helper (use gTTS if available) ---
def gerar_audio(texto, filename="audio/resposta.mp3", slow=True):
    if not gTTS:
        return None
    try:
        tts = gTTS(text=texto, lang="pt-br", slow=bool(cfg.get("audio_suave", True)))
        tts.save(filename)
        return filename
    except Exception:
        return None

# --- UI: top icons (loja / histórico) ---
col1, col2, col3 = st.columns([1,1,6])
with col1:
    if st.button("🛍️"):
        st.session_state.show_loja = not st.session_state.get("show_loja", False)
with col2:
    if st.button("📜"):
        st.session_state.show_historico = not st.session_state.get("show_historico", False)
with col3:
    st.markdown(f"<div style='text-align:right; color:#d0d0d0;'>💰 {st.session_state.moedas} moedas</div>", unsafe_allow_html=True)

# Loja panel (top)
if st.session_state.get("show_loja"):
    st.markdown("---")
    st.markdown("### 🛍️ Loja Romântica")
    itens = carregar_loja()
    for item in itens:
        cols = st.columns([4,1])
        with cols[0]:
            st.markdown(f"**{item['nome']}** — {item['preco']} moedas")
            st.markdown(f"<small class='small-muted'>{item.get('mensagem')}</small>", unsafe_allow_html=True)
        with cols[1]:
            if st.button(f"Comprar##{item['nome']}"):
                if st.session_state.moedas >= item["preco"]:
                    st.session_state.moedas -= item["preco"]
                    st.success(f"Você comprou: {item['nome']}")
                    # immediate Ysis response
                    msg = item["mensagem"]
                    st.session_state.historico.append({"role":"model","text":msg})
                    st.session_state.conversas_salvas.append({"data":datetime.datetime.now().isoformat(),"pergunta":f"Comprou:{item['nome']}","resposta":msg})
                    salvar_memoria_file()
                    audio_file = gerar_audio(msg, filename=f"audio/compra_{int(time.time())}.mp3")
                    if audio_file:
                        st.audio(audio_file)
                    if item.get("vip"):
                        st.session_state.vip = True
                else:
                    st.error("Você não tem moedas suficientes.")

# Histórico panel
if st.session_state.get("show_historico"):
    st.markdown("---")
    st.markdown("### 📒 Histórico de conversas")
    saved = load_memoria_file()
    if not saved:
        st.info("Ainda sem conversas salvas.")
    else:
        for c in saved[::-1]:
            st.markdown(f"**Você:** {c['pergunta']}")
            st.markdown(f"**Ysis:** {c['resposta']}")
            st.markdown("---")

# Optional background music (if file present)
if Path("static/music.mp3").exists():
    st.markdown(
        """
        <audio autoplay loop controls style="width:100%;">
          <source src="static/music.mp3" type="audio/mp3">
        </audio>
        """,
        unsafe_allow_html=True
    )

# Image (static/gif) - show dynamic gif if speaking
img_path = "static/ysis_b.gif" if Path("static/ysis_b.gif").exists() else "static/ysis.jpg"
if Path(img_path).exists():
    st.image(img_path, width=260)

# Input area (send on Enter)
mensagem = st.text_input("💬 Diga algo para a Ysis:", placeholder="Conte tudo pra mim...")
if st.button("Enviar"):
    mensagem = st.session_state.get("mensagem", "")

if mensagem and mensagem.strip():
    st.session_state.ysis_falando = True
    st.session_state.last_active = time.time()
    with st.spinner("Ysis está pensando..."):
        resposta = conversar_com_ysis(mensagem.strip())
        st.markdown(f"**Ysis:** {resposta}")
        st.markdown(f"<small>{random.choice(['💫','🌹','✨','💞'])} </small>", unsafe_allow_html=True)
        # play audio if possible
        audio = gerar_audio(resposta, filename=f"audio/resposta_{int(time.time())}.mp3")
        if audio:
            st.audio(audio)
    st.session_state.ysis_falando = False
    # persist memory file written inside conversar
    st.experimental_rerun()

# Auto prompt if idle
idle_seconds = int(cfg.get("idle_prompt_seconds", 60 * 3))
if time.time() - st.session_state.last_active > idle_seconds:
    # gently nudge
    nudgemsg = "Você está por aí, meu amor? Senti saudade..."
    resp = conversar_com_ysis(nudgemsg)
    st.markdown(f"**Ysis:** {resp}")
    st.session_state.last_active = time.time()
    salvar_memoria_file()
