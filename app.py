import os
import json
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Configurazione client Groq per il modello di chat
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

# Selezione sicura del modello compatibile
try:
    models_response = client.models.list()
    available_models = [m.id for m in models_response.data]
    versatile_models = [m for m in available_models if "versatile" in m.lower()]
    if versatile_models:
        MODEL_NAME = versatile_models[0]
    else:
        llama_models = [m for m in available_models if "llama" in m.lower()]
        MODEL_NAME = llama_models[0] if llama_models else available_models[0]
except Exception:
    MODEL_NAME = "llama-3.3-70b-versatile"

KB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base")
if not os.path.exists(KB_PATH):
    os.makedirs(KB_PATH)

def load_knowledge_base():
    content = ""
    if not os.path.exists(KB_PATH):
        return content
    for root, dirs, files in os.walk(KB_PATH):
        for file in files:
            if file.endswith(('.txt', '.md', '.json')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content += f"\n\n--- File: {file} ---\n" + f.read()
                except Exception as e:
                    print(f"Errore lettura file {file}: {e}")
    return content

def lightweight_search(query: str) -> str:
    full_text = load_knowledge_base()
    if not full_text:
        return "Nessun documento trovato nella base di conoscenza."
    
    paragraphs = full_text.split("\n\n")
    query_words = set(query.lower().split())
    
    scored_paragraphs = []
    for p in paragraphs:
        p_lower = p.lower()
        score = sum(1 for word in query_words if word in p_lower)
        if score > 0 or len(paragraphs) <= 6:
            scored_paragraphs.append((score, p))
            
    scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
    top_content = "\n\n".join([p[1] for p in scored_paragraphs[:5]])
    return top_content if top_content else full_text[:4000]

@app.route("/api/v1/chat", methods=["POST"])
def chat_endpoint():
    try:
        data = request.json or {}
        user_message = data.get("message", "")
        session_history = data.get("history", [])

        if not user_message:
            return jsonify({"error": "Il parametro 'message' è obbligatorio"}), 400

        retrieved_context = lightweight_search(user_message)

        system_prompt = (
            "Sei l'assistente virtuale per il supporto tecnico sui registratori di cassa e POS.\n"
            "Fornisci assistenza di I livello aiutando il cliente a risolvere i problemi più semplici.\n\n"
            f"--- CONTESTO TECNICO DAI MANUALI ---\n{retrieved_context}\n-------------------------------------\n\n"
            "REGOLE:\n1. Se è una procedura semplice, spiegalo passo-passo basandoti sul contesto.\n"
            "2. Se è un guasto bloccante o esaurimento DGFE, chiedi i dati necessari."
        )

        messages = [{"role": "system", "content": system_prompt}] + session_history + [{"role": "user", "content": user_message}]

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7
        )

        return jsonify({
            "type": "standard_response",
            "reply": response.choices[0].message.content
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)