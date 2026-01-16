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
    candidates_info = data.get('candidates_info', [])  # Full candidate info from frontend
    trait_reports = data.get('trait_reports', {})  # NEW: Trait reports from frontend Session Storage
    session_id = data.get('session_id', 'default_session')
    
    print(f"[Chat] Received trait_reports for {len(trait_reports)} candidates", flush=True)
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400

    def generate():
        # TODO: Log request to SQLite
        
        try:
            response_stream, use_case_id = rag_service.generate_response(
                query, candidate_ids, session_id, 
                candidates_info=candidates_info,
                trait_reports=trait_reports  # NEW: Pass trait reports to RAG
            )
        except Exception as e:
            print(f"[RAG Generation Error] {e}")
            yield f"data: {json.dumps({'type': 'meta', 'intent': 'ERROR'})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': '抱歉，系統發生錯誤，無法進行分析。'})}\n\n"
            yield "data: [DONE]\n\n"
            return
        
        # Send thinking/intent meta
        yield f"data: {json.dumps({'type': 'meta', 'intent': use_case_id})}\n\n"
        
        try:
             full_content = ""
             for chunk in response_stream:
                 content = chunk.choices[0].delta.content
                 if content:
                     full_content += content
                     yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
        except Exception as e:
             print(f"[Streaming Error] {e}")
             err_msg = "\n\n(連線中斷: 請稍後再試)"
             yield f"data: {json.dumps({'type': 'token', 'content': err_msg})}\n\n"
        
        # TODO: Update Log with full response and latency
        
        yield "data: [DONE]\n\n"

    # Create response with proper headers to prevent buffering
    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    
    # Critical headers to disable buffering in production (IIS, Nginx, Waitress)
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['X-Accel-Buffering'] = 'no'  # Nginx
    response.headers['Content-Encoding'] = 'none'  # Prevent compression
    
    return response
