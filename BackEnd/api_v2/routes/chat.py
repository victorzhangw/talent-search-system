from flask import Blueprint, request, Response, jsonify, stream_with_context, current_app
import json
from services.rag_engine import RAGService
from database import db_session, ChatLog

bp = Blueprint('chat', __name__, url_prefix='/chat')

rag_service = None

@bp.before_request
def init_service():
    global rag_service
    if rag_service is None:
        rag_service = RAGService()

@bp.route('/', methods=['POST'])
def chat():
    data = request.json
    query = data.get('query')
    candidate_ids = data.get('candidate_ids', [])
    session_id = data.get('session_id', 'default_session')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400

    def generate():
        # TODO: Log request to SQLite
        
        response_stream, use_case_id = rag_service.generate_response(query, candidate_ids, session_id)
        
        # Send thinking/intent meta
        yield f"data: {json.dumps({'type': 'meta', 'intent': use_case_id})}\n\n"
        
        full_content = ""
        for chunk in response_stream:
            content = chunk.choices[0].delta.content
            if content:
                full_content += content
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
        
        # TODO: Update Log with full response and latency
        
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
