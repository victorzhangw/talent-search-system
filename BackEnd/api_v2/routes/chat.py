from flask import Blueprint, request, Response, jsonify, stream_with_context, current_app
import json
import threading
import os
from sqlalchemy.exc import OperationalError
from ..services.rag_engine import RAGService
from ..services.session_store import SqlSessionStore
from ..database.connection import get_db_session
from ..database.models import ChatSession
from ..database import db_session

bp = Blueprint('chat', __name__, url_prefix='/chat')

rag_service = None

def background_generate_title(session_id, user_query, candidate_names):
    try:
        global rag_service
        if not rag_service: 
            return
            
        # 1. Ask LLM for title
        c_names = ', '.join(candidate_names) if candidate_names else '無'
        
        # Load prompt from external file
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts', 'conversation_title_prompt.txt')
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_tpl = f.read()
            prompt = prompt_tpl.format(c_names=c_names, user_query=user_query)
        except Exception as pe:
            print(f"[Background Title] Prompt load error: {pe}")
            # Fallback simple prompt
            prompt = f"分析候選人 {c_names} 的對話，摘要為 19 字以內的標題。提問：{user_query}"
        
        messages = [{"role": "user", "content": prompt}]
        response = rag_service.client.chat.completions.create(
            model=rag_service.model_name,
            messages=messages,
            max_tokens=30,
            temperature=0.3
        )
        title = response.choices[0].message.content.strip().strip('"\'')
        if len(title) > 20:
            title = title[:20]
            
        # 1.5 Record Token Usage
        total_tokens = getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0
        p_tokens = getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') else 0
        c_tokens = getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') else 0
        try:
            from ..services.session_store import SqlSessionStore
            store = SqlSessionStore()
            store.add_message(
                session_id, 'system', f'[System] 產生標題: {title}', 
                token_usage=total_tokens, prompt_tokens=p_tokens, completion_tokens=c_tokens, 
                model_name=rag_service.model_name
            )
        except Exception as te:
            print(f"[Background Title] Token logging error: {te}")
            
        # 2. Update DB
        db = get_db_session()
        try:
            session_obj = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if session_obj:
                meta = dict(session_obj.metadata_ or {})
                meta['title'] = title
                
                # Update candidates info if not present
                if 'candidates' not in meta and candidate_names:
                    meta['candidates'] = [{"name": n} for n in candidate_names]
                    
                session_obj.metadata_ = meta
                db.commit()
                print(f"[Background Title] Updated session {session_id} title to: {title}")
        except Exception as e:
            db.rollback()
            print(f"[Background Title] DB error: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"[Background Title] Error: {e}")

@bp.before_request
def init_service():
    global rag_service
    if rag_service is None:
        rag_service = RAGService()

@bp.route('/history', methods=['GET', 'OPTIONS'])
def get_user_history():
    if request.method == 'OPTIONS':
        return '', 200
        
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id parameter is required'}), 400
        
    session_store = SqlSessionStore()
    sessions = session_store.get_user_sessions(user_id=user_id, days=30)
    
    # Format and group by Today vs Past 30 Days (using UTC+8 and last_active_at)
    from datetime import datetime, timedelta
    
    today_sessions = []
    past_sessions = []
    
    # Taiwan Time UTC+8
    now_utc8 = (datetime.utcnow() + timedelta(hours=8)).date()
    
    for s in sessions:
        active_time = s.last_active_at if s.last_active_at else s.started_at
        s_date_utc8 = (active_time + timedelta(hours=8)).date() if active_time else None

        
        # Build candidate info summary if possible
        # metadata_ might have it, or we can just return what we have
        title = "新對話"
        if s.metadata_ and isinstance(s.metadata_, dict):
            # Try to get explicitly saved title
            saved_title = s.metadata_.get('title')
            if saved_title:
                title = saved_title
            else:
                # Try to get candidate names or something to act as title
                cands = s.metadata_.get('candidates', [])
                if cands:
                    title = ", ".join([c.get('name', 'Unknown') for c in cands]) + " 分析"
                
        # If no explicit metadata candidates, maybe fallback or the frontend handles it
        # Actually in Traitty, session has metadata_? Let's check when we create session.
        # Currently we don't save candidates to session metadata. Let's return basic info for now.
        
        session_data = {
            'session_id': s.session_id,
            'started_at': s.started_at.isoformat() if hasattr(s.started_at, 'isoformat') else s.started_at,
            'last_active_at': s.last_active_at.isoformat() if hasattr(s.last_active_at, 'isoformat') else s.last_active_at,
            'status': s.status,
            'title': title
        }
        
        if s_date_utc8 == now_utc8:
            today_sessions.append(session_data)
        else:
            past_sessions.append(session_data)
            
    return jsonify({
        'today': today_sessions,
        'past_30_days': past_sessions
    })

@bp.route('/<session_id>', methods=['GET', 'OPTIONS'])
def get_session_details(session_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    session_store = SqlSessionStore()
    session = session_store.get_session(session_id)
    if not session:
        return jsonify({'error': 'Not found'}), 404
        
    messages = session_store.get_messages(session_id)
    
    # 過濾掉 system role（如背景任務產生的系統訊息），並將 assistant → ai 以符合前端渲染規則
    ROLE_MAP = {'assistant': 'ai', 'user': 'user'}
    visible_messages = [m for m in messages if m.role in ('user', 'assistant')]
    
    return jsonify({
        'session_id': session.session_id,
        'status': session.status,
        'metadata': session.metadata_,
        'messages': [{
            'id': m.id,
            'role': ROLE_MAP.get(m.role, m.role),
            'content': m.content,
            'rating': getattr(m, 'rating', 0),
            'created_at': m.created_at.isoformat() if m.created_at else None
        } for m in visible_messages]
    })

@bp.route('/message/<int:message_id>/rating', methods=['PUT', 'OPTIONS'])
def update_message_rating(message_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.get_json()
    if not data or 'rating' not in data:
        return jsonify({'error': 'rating is required'}), 400
        
    rating = int(data['rating'])
    
    session_store = SqlSessionStore()
    success = session_store.update_message_rating(message_id, rating)
    
    if success:
        return jsonify({'status': 'success', 'message_id': message_id, 'rating': rating})
    else:
        return jsonify({'error': 'Message not found or update failed'}), 404

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
    
    mode = data.get('mode', 'explanation') # Default to explanation if not provided
    
    print(f"[Chat] Received trait_reports for {len(trait_reports)} candidates", flush=True)
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400

    print(f">>> [DEBUG] Candidate IDs: {candidate_ids}", flush=True)
    print(f">>> [DEBUG] Session ID: {session_id}, User ID: {user_id}, Mode: {mode}", flush=True)
    
    def generate():
        print(">>> [DEBUG] Generator started", flush=True)
        try:
            # Initialize Session Store
            session_store = SqlSessionStore()
            print(">>> [DEBUG] Session store initialized", flush=True)
        
            # Ensure session exists (Upsert logic or Check?)
            needs_title_generation = False
            try:
                # Check if exists
                existing_session = session_store.get_session(session_id)
                if not existing_session:
                    # Create with user_id
                    print(f"[Chat] Creating new session {session_id} with user_id: '{user_id}'", flush=True)
                    session_store.create_session(session_id=session_id, user_id=user_id)
                    needs_title_generation = True
                else:
                    # Check if we need to update user_id
                    current_db_user_id = existing_session.user_id
                    print(f"[Chat] Found existing session {session_id}. DB user_id: '{current_db_user_id}'. Request user_id: '{user_id}'", flush=True)
                     
                    # 檢查現有 Session 是否缺少 title
                    meta = existing_session.metadata_ or {}
                    if not meta.get('title'):
                        print(f"[Chat] Existing session {session_id} is missing a title. Will generate one.", flush=True)
                        needs_title_generation = True
                        
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

            # Fire Background Task for Title Generation
            if needs_title_generation:
                candidate_names = [c.get('name') for c in candidates_info if 'name' in c]
                threading.Thread(
                    target=background_generate_title, 
                    args=(session_id, query, candidate_names),
                    daemon=True
                ).start()

            # Log User Message
            session_store.add_message(session_id, 'user', query)

            try:
                response_stream, use_case_id = rag_service.generate_response(
                    query, candidate_ids, session_id, 
                    candidates_info=candidates_info,
                    trait_reports=trait_reports,
                    mode=mode
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
            has_llm_error = False
            
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
                            if "⚠️ 系統提示：AI 服務暫時無法連線" in content or "由於 LLM 連線失敗" in content:
                                has_llm_error = True
                            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            except Exception as e:
                print(f"[Streaming Error] {e}", flush=True)  # ADDED FLUSH
                import traceback
                traceback.print_exc()
                err_msg = "\n\n(連線中斷: 請稍後再試)"
                has_llm_error = True
                yield f"data: {json.dumps({'type': 'token', 'content': err_msg})}\n\n"
            
            # Log Assistant Message & Usage
            prompt_tokens = 0
            completion_tokens = 0
            if total_usage:
                prompt_tokens = getattr(total_usage, 'prompt_tokens', 0)
                completion_tokens = getattr(total_usage, 'completion_tokens', 0)
            
            # Store total and split token usage
            msg_id = session_store.add_message(
                session_id, 
                'assistant', 
                full_assistant_content, 
                token_usage=(prompt_tokens + completion_tokens),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model_name=rag_service.model_name
            )
            
            if msg_id:
                yield f"data: {json.dumps({'type': 'message_id', 'id': msg_id})}\n\n"
            
            # --- 扣除額度並即時同步回傳給前端 ---
            if not has_llm_error:
                # 若完全沒有攜帶特質報告（沒有選擇任一具備報告的人或未帶入），則不扣除額度
                if not trait_reports:
                    print(f"[Daily Settlement] Skipped quota deduction because no valid trait_reports were provided in the payload.", flush=True)
                else:
                    try:
                        from ..utils.traitty_api import fetch_init_data, find_active_plan, submit_daily_settlement
                        if user_id and user_id != 'anonymous':
                            # 1. 取得最新方案清單
                            init_data = fetch_init_data(user_id)
                            usable_plans = init_data.get('usable_plans', [])
                            plan_id = find_active_plan(usable_plans)
                            
                            if plan_id:
                                # 2. 發送 Daily Settlement 扣款請求
                                print(f"[Daily Settlement] Deducting quota for plan: {plan_id}, user: {user_id}, msg: {msg_id}", flush=True)
                                submit_daily_settlement(user_id, plan_id, session_id, message_id=str(msg_id))
                                
                                # 3. 扣款成功後，重新查詢最新 quota_summary 推給前端
                                post_settle_data = fetch_init_data(user_id)
                                new_quota = post_settle_data.get('quota_summary')
                                
                                if new_quota:
                                    yield f"data: {json.dumps({'type': 'quota', 'quota_summary': new_quota})}\n\n"
                                    print("[Daily Settlement] Successfully refreshed quota and synced to frontend", flush=True)
                            else:
                                print(f"[Daily Settlement] No valid usable plan found for user {user_id}", flush=True)
                    except Exception as quota_e:
                        print(f"[Daily Settlement Error] Failed to deduct quota or sync: {quota_e}", flush=True)
            else:
                print(f"[Daily Settlement] Skipped quota deduction due to LLM error flag for session: {session_id}", flush=True)

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
