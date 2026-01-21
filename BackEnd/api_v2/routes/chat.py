from flask import Blueprint, request, Response, jsonify, stream_with_context, current_app
import json
from sqlalchemy.exc import OperationalError
from ..services.rag_engine import RAGService
from ..services.session_store import SqlSessionStore
from ..database.connection import get_db_session
from ..database.models import ChatSession
from ..database import db_session

bp = Blueprint('chat', __name__, url_prefix='/chat')

rag_service = None

@bp.before_request
def init_service():
    global rag_service
    if rag_service is None:
        rag_service = RAGService()

@bp.route('/', methods=['POST'])
def chat():
    print(">>> [DEBUG] /chat/ endpoint called", flush=True)
    try:
        data = request.get_json(force=True)
        print(f">>> [DEBUG] Payload received. Keys: {list(data.keys())}", flush=True)
    except Exception as e:
        print(f">>> [DEBUG] Failed to parse JSON: {e}", flush=True)
        return jsonify({'error': 'Invalid JSON'}), 400

    query = data.get('query')
    candidate_ids = data.get('candidate_ids', [])
    candidates_info = data.get('candidates_info', [])  # Full candidate info from frontend
    trait_reports = data.get('trait_reports', {})  # NEW: Trait reports from frontend Session Storage
    session_id = data.get('session_id', 'default_session')
    user_id = data.get('user_id') # Copied from frontend config email
    
    print(f"[Chat] Received trait_reports for {len(trait_reports)} candidates", flush=True)
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400

    print(f">>> [DEBUG] Candidate IDs: {candidate_ids}", flush=True)
    print(f">>> [DEBUG] Session ID: {session_id}, User ID: {user_id}", flush=True)
    
    def generate():
        print(">>> [DEBUG] Generator started", flush=True)
        try:
             # Initialize Session Store
             session_store = SqlSessionStore()
             print(">>> [DEBUG] Session store initialized", flush=True)
        
             # Ensure session exists (Upsert logic or Check?)
             try:
                 # Check if exists
                     existing_session = session_store.get_session(session_id)
                 if not existing_session:
                     # Create with user_id
                     print(f"[Chat] Creating new session {session_id} with user_id: '{user_id}'", flush=True)
                     session_store.create_session(session_id=session_id, user_id=user_id)
                 else:
                     # Check if we need to update user_id
                     current_db_user_id = existing_session.user_id
                     print(f"[Chat] Found existing session {session_id}. DB user_id: '{current_db_user_id}'. Request user_id: '{user_id}'", flush=True)
                     
                     if user_id and current_db_user_id != user_id:
                         # Update user_id if it was missing or changed
                         print(f"[Chat] Updating session {session_id} user_id from '{current_db_user_id}' to '{user_id}'", flush=True)
                         db = get_db_session()
                         try:
                             rows = db.query(ChatSession).filter(ChatSession.session_id == session_id).update({"user_id": user_id})
                             db.commit()
                             print(f"[Chat] Update committed. Rows affected: {rows}", flush=True)
                         except Exception as update_e:
                             db.rollback()
                             print(f"[Chat] Update failed: {update_e}", flush=True)
                         finally:
                             db.close()
             except Exception as e:
                 print(f"[Chat] Session Init Error: {e}")

             # Log User Message
             session_store.add_message(session_id, 'user', query)

             try:
                 response_stream, use_case_id = rag_service.generate_response(
                     query, candidate_ids, session_id, 
                     candidates_info=candidates_info,
                     trait_reports=trait_reports
                 )
             except OperationalError as db_err:
                 # Catch specific DB connection errors
                 print(f"[RAG DB Error] {db_err}", flush=True)
                 err_json = json.dumps({'type': 'token', 'content': "⚠️ 系統提示：目前資料庫暫時無法連線，無法讀取候選人資料。請通知管理員檢查後端服務。\n"})
                 yield f"data: {err_json}\n\n"
                 yield "data: [DONE]\n\n"
                 return
             except Exception as e:
                 print(f"[RAG Generation Error] {e}", flush=True)
                 import traceback
                 tb = traceback.format_exc()
                 
                 # Friendly error message for general failures
                 err_json = json.dumps({'type': 'token', 'content': "⚠️ 抱歉，系統運算時發生未預期的錯誤，請稍後再試。"})
                 yield f"data: {err_json}\n\n"
                 
                 # Log full traceback to console/file instead of sending to user
                 print(f"SYSTEM ERROR TRACEBACK:\n{tb}", flush=True)
                 
                 yield "data: [DONE]\n\n"
                 return
            
             # Send thinking/intent meta
             yield f"data: {json.dumps({'type': 'meta', 'intent': use_case_id})}\n\n"
            
             full_assistant_content = ""
             total_usage = None
            
             try:
                 for chunk in response_stream:
                     # Check for usage in the chunk (OpenAI standard)
                     if hasattr(chunk, 'usage') and chunk.usage:
                         total_usage = chunk.usage
                         # print(f"[Chat] Token Usage: {total_usage}")
                         continue

                     if chunk.choices and len(chunk.choices) > 0:
                         delta = chunk.choices[0].delta
                         content = delta.content
                         if content:
                             full_assistant_content += content
                             yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
             except Exception as e:
                 print(f"[Streaming Error] {e}", flush=True)  # ADDED FLUSH
                 import traceback
                 traceback.print_exc()
                 err_msg = "\n\n(連線中斷: 請稍後再試)"
                 yield f"data: {json.dumps({'type': 'token', 'content': err_msg})}\n\n"
            
             # Log Assistant Message & Usage
             prompt_tokens = 0
             completion_tokens = 0
             if total_usage:
                 prompt_tokens = getattr(total_usage, 'prompt_tokens', 0)
                 completion_tokens = getattr(total_usage, 'completion_tokens', 0)
            
             # We store total tokens for simple billing schema, or separate?
             # Model has 'token_usage' int. Let's store total.
             session_store.add_message(
                 session_id, 
                 'assistant', 
                 full_assistant_content, 
                 token_usage=(prompt_tokens + completion_tokens),
                 model_name='deepseek-chat'
             )
            
             yield "data: [DONE]\n\n"
        except Exception as outer_e:
             print(f"[Generator outer error] {outer_e}", flush=True)
             import traceback
             with open("traceback.log", "w", encoding="utf-8") as f:
                 f.write(traceback.format_exc())
             yield f"data: {json.dumps({'type': 'token', 'content': '系統錯誤'})}\n\n"

    # Create response with proper headers to prevent buffering
    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    
    # Critical headers to disable buffering in production (IIS, Nginx, Waitress)
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['X-Accel-Buffering'] = 'no'  # Nginx
    response.headers['Content-Encoding'] = 'none'  # Prevent compression
    response.headers['Connection'] = 'keep-alive'
    
    return response
