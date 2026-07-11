"""
MiroFish Backend - Flask应用工厂
"""

import os
import warnings

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
# 需要在所有其他导入之前设置
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 设置JSON编码：确保中文直接显示（而不是 \uXXXX 格式）
    # Flask >= 2.3 使用 app.json.ensure_ascii，旧版本使用 JSON_AS_ASCII 配置
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # 设置日志
    logger = setup_logger('mirofish')
    
    # 只在 reloader 子进程中打印启动信息（避免 debug 模式下打印两次）
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish Backend 启动中...")
        logger.info("=" * 50)
    
    # OpenAI TPM 스로틀: 메인 프로세스의 모든 OpenAI 호출(온톨로지·설정/프로필 생성 등)을
    # 시뮬레이션 서브프로세스와 '합산' 예산(크로스-프로세스 파일락)으로 묶어 429를 사전 회피.
    # Completions.create 를 클래스 레벨에서 몽키패치하므로, 각 서비스가 자체 OpenAI() 클라이언트를
    # 만들어도 전부 걸린다(llm_client의 raw-response 경로는 자체 reserve로 별도 처리).
    if "openai.com" in (Config.LLM_BASE_URL or ""):
        try:
            from .utils.openai_throttle import install as _install_tpm
            if _install_tpm():
                logger.info("[throttle] OpenAI TPM 스로틀 활성화(메인 프로세스)")
        except Exception as _e:
            logger.warning(f"[throttle] 설치 실패(무시): {_e}")

    # 启用CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # 注册模拟进程清理函数（确保服务器关闭时终止所有模拟进程）
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("已注册模拟进程清理函数")
    
    # 请求日志中间件
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"请求: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"请求体: {request.get_json(silent=True)}")
    
    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"响应: {response.status_code}")
        return response
    
    # 注册蓝图
    from .api import graph_bp, simulation_bp, report_bp, designdb_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(designdb_bp, url_prefix='/api/designdb')
    
    # 健康检查
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'MiroFish Backend'}

    # LLM(로컬 Qwen 서버) 준비상태 — 모델 로딩 전 제출 버튼 비활성화용
    @app.route('/api/llm/status')
    def llm_status():
        import urllib.request
        from .config import Config
        ready = False
        try:
            url = (Config.LLM_BASE_URL or '').rstrip('/') + '/models'
            req = urllib.request.Request(
                url, headers={'Authorization': f'Bearer {Config.LLM_API_KEY or "x"}'}
            )
            with urllib.request.urlopen(req, timeout=3) as r:
                ready = (getattr(r, 'status', 200) == 200)
        except Exception:
            ready = False
        return {'llm_ready': ready}
    
    # Nemotron 퍼소나 사용 시, 전체 풀(100만·~24s 로드)을 백그라운드로 미리 데워둔다.
    # → 사용자가 Step2 필터 UI에 도달할 즈음엔 이미 로드 완료(첫 호출 멈춤 방지).
    if os.environ.get("USE_NEMOTRON_PERSONAS", "").strip().lower() in ("1", "true", "yes", "on"):
        try:
            from .services.nemotron_loader import warm_pool_async
            warm_pool_async()
        except Exception as e:
            logger.warning(f"Nemotron 풀 워밍 실패(무시): {e}")

    if should_log_startup:
        logger.info("MiroFish Backend 启动完成")

    return app

