"""
designdb 시맨틱 검색 API.

- GET  /api/designdb/status                 : 인덱스 유무/건수/카테고리
- POST /api/designdb/search                 : 제품 설명(쿼리)로 검색
    body: {query, category?, top_n?}
    resp: {success, results:[{id,category,category_name,post_id,title,field,date,snippet,char_len,score}]}
"""
from flask import jsonify, request

from . import designdb_bp
from ..services import designdb_search
from ..utils.logger import get_logger

logger = get_logger("mirofish.api.designdb")


@designdb_bp.route("/status", methods=["GET"])
def status():
    try:
        return jsonify({"success": True, **designdb_search.status()})
    except Exception as e:
        logger.error(f"[designdb] status 실패: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@designdb_bp.route("/article/<int:aid>", methods=["GET"])
def article(aid):
    try:
        return jsonify({"success": True, "article": designdb_search.get_article(aid)})
    except (IndexError, ValueError):
        return jsonify({"success": False, "error": "기사를 찾을 수 없습니다"}), 404
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        logger.error(f"[designdb] article 실패: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@designdb_bp.route("/search", methods=["POST"])
def search():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    category = data.get("category") or None   # ""/None → 전체
    page = int(data.get("page") or 1)
    page_size = int(data.get("page_size") or 20)
    if not query:
        return jsonify({"success": False, "error": "query 가 필요합니다"}), 400
    try:
        res = designdb_search.search(query, category=category, page=page, page_size=page_size)
        return jsonify({"success": True, **res})
    except RuntimeError as e:
        # 인덱스 없음 등
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        logger.error(f"[designdb] search 실패: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
