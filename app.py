import os
import json
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Configurazione del client OpenAI per puntare a Groq tramite la variabile d'ambiente
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

MODEL_NAME = "llama-3.3-70b-versatile"

def vector_search(query: str) -> str:
    """Legge dinamicamente i manuali di testo presenti nella cartella knowledge_base"""
    kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base")
    context_text = ""

    if os.path.exists(kb_path):
        for filename in os.listdir(kb_path):
            if filename.endswith(".txt"):
                file_path = os.path.join(kb_path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    context_text += f"\n--- {filename} ---\n{content}\n"

    if not context_text:
        return "Nessun manuale trovato nella base di conoscenza."

    return context_text

def create_crm_ticket(ragione_sociale: str, partita_iva: str, matricola_rt: str, descrizione_guasto: str, priorita: str) -> dict:
    return {
        "status": "success",
        "ticket_id": "TK-GROQ-001",
        "message": f"Ticket registrato per {ragione_sociale} (Matricola RT: {matricola_rt})."
    }

tools = [
    {
        "type": "function",
        "function": {
            "name": "create_crm_ticket",
            "description": "Apre un ticket di assistenza sul CRM in caso di guasto hardware, blocco fiscale o richiesta di intervento.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ragione_sociale": {"type": "string", "description": "Nome dell'attività"},
                    "partita_iva": {"type": "string", "description": "Partita IVA o Codice Fiscale"},
                    "matricola_rt": {"type": "string", "description": "Matricola del registratore telematico/POS"},
                    "descrizione_guasto": {"type": "string", "description": "Sintesi del problema riscontrato"},
                    "priorita": {"type": "string", "enum": ["BASSA", "MEDIA", "ALTA", "URGENTE_CASSA_BLOCCATA"], "description": "Urgenza"}
                },
                "required": ["ragione_sociale", "matricola_rt", "descrizione_guasto", "priorita"]
            }
        }
    }
]

@app.route("/api/v1/chat", methods=["POST"])
def chat_endpoint():
    data = request.json or {}
    user_message = data.get("message", "")
    session_history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Il parametro 'message' è obbligatorio"}), 400

    retrieved_context = vector_search(user_message)

    system_prompt = (
        "Sei l'assistente virtuale per il supporto tecnico sui registratori di cassa e POS.\n"
        "Fornisci assistenza di I livello aiutando il cliente a risolvere i problemi più semplici.\n\n"
        f"--- CONTESTO TECNICO DAI MANUALI ---\n{retrieved_context}\n-------------------------------------\n\n"
        "REGOLE:\n1. Se è una procedura semplice, spiegalo passo-passo basandoti sul contesto.\n"
        "2. Se è un guasto bloccante o esaurimento DGFE, chiedi i dati necessari e usa la funzione `create_crm_ticket`."
    )

    messages = [{"role": "system", "content": system_prompt}] + session_history + [{"role": "user", "content": user_message}]

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    response_message = response.choices[0].message

    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            if tool_call.function.name == "create_crm_ticket":
                args = json.loads(tool_call.function.arguments)
                ticket_res = create_crm_ticket(
                    ragione_sociale=args.get("ragione_sociale"),
                    partita_iva=args.get("partita_iva", "N/D"),
                    matricola_rt=args.get("matricola_rt"),
                    descrizione_guasto=args.get("descrizione_guasto"),
                    priorita=args.get("priorita", "MEDIA")
                )
                return jsonify({
                    "type": "ticket_escalation",
                    "reply": f"Richiesta inoltrata al reparto tecnico. Codice Ticket: {ticket_res.get('ticket_id')}.",
                    "ticket_data": ticket_res
                })

    return jsonify({
        "type": "standard_response",
        "reply": response_message.content
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
