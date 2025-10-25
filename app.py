"""
PRODUCTION READY - Flask Application
Real-time data from live DB + SSO detailed endpoints
"""
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import pooling
import io
import os
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch

# ================================================================
# CONFIGURATION
# ================================================================

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Configuration
DB_CONFIG = {
    "host": os.getenv('DB_HOST', 'mysql'),
    "port": int(os.getenv('DB_PORT', 3306)),
    "database": os.getenv('DB_NAME', 'demo'),
    "user": os.getenv('DB_USER', 'dashboard_user'),
    "password": os.getenv('DB_PASSWORD', 'dashboard_pass'),
    "pool_name": "optimized_pool",
    "pool_size": int(os.getenv('DB_POOL_SIZE', 30)),
    "pool_reset_session": True,
    "autocommit": True,
    "connect_timeout": 10,
}

# ================================================================
# DATABASE CONNECTION POOL
# ================================================================

connection_pool = None

def init_db_pool():
    global connection_pool
    try:
        connection_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)
        logger.info("✅ Database pool initialized (PRODUCTION READY)")
        return True
    except Exception as e:
        logger.error(f"❌ Database pool error: {e}")
        return False

init_db_pool()

def get_db_connection():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return connection_pool.get_connection()
        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
    return None

def execute_query(query, params=None, fetch_one=False):
    """Execute query - REAL-TIME from live database"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True, buffered=True)
        cursor.execute(query, params or ())
        
        if fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        
        return result
    except Exception as e:
        logger.error(f"Query error: {e}\nQuery: {query}\nParams: {params}")
        return None if fetch_one else []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# ================================================================
# ROUTES
# ================================================================

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/health')
def health():
    try:
        result = execute_query("SELECT 1 as health", fetch_one=True)
        if result and result.get('health') == 1:
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now().isoformat()
            }), 200
        return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 503
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

# ================================================================
# LOGIN METRICS
# ================================================================

@app.route('/api/metrics/login')
def get_login_metrics():
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = """
            SELECT 
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as fail_count,
                COUNT(*) as total_count
            FROM idx2_audit_login
            WHERE tenant = %s 
              AND subtenant = %s
              AND timestamp >= %s
              AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
        """
        
        result = execute_query(query, (tenant_id, subtenant_id, start_date, end_date), fetch_one=True)
        
        if result:
            return jsonify({
                'success': int(result.get('success_count') or 0),
                'fail': int(result.get('fail_count') or 0),
                'total': int(result.get('total_count') or 0)
            })
        
        return jsonify({'success': 0, 'fail': 0, 'total': 0})
    
    except Exception as e:
        logger.error(f"Login metrics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics/login/users')
def get_login_users():
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status = request.args.get('status', 'SUCCESS')
        
        query = """
            SELECT 
                user,
                ip,
                timestamp,
                status
            FROM idx2_audit_login
            WHERE tenant = %s 
              AND subtenant = %s
              AND timestamp >= %s
              AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
              AND status = %s
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        
        result = execute_query(query, (tenant_id, subtenant_id, start_date, end_date, status))
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Login users error: {e}")
        return jsonify({'error': str(e)}), 500

# ================================================================
# PASSWORD RESET METRICS
# ================================================================

@app.route('/api/metrics/password')
def get_password_metrics():
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = """
            SELECT 
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as fail_count
            FROM idx2_audit_fgtpwd
            WHERE tenant = %s 
              AND subtenant = %s
              AND timestamp >= %s
              AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
        """
        
        result = execute_query(query, (tenant_id, subtenant_id, start_date, end_date), fetch_one=True)
        
        if result:
            return jsonify({
                'success': int(result.get('success_count') or 0),
                'fail': int(result.get('fail_count') or 0)
            })
        
        return jsonify({'success': 0, 'fail': 0})
    
    except Exception as e:
        logger.error(f"Password metrics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics/password/users')
def get_password_users():
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status = request.args.get('status', 'SUCCESS')
        
        query = """
            SELECT 
                user,
                timestamp,
                status
            FROM idx2_audit_fgtpwd
            WHERE tenant = %s 
              AND subtenant = %s
              AND timestamp >= %s
              AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
              AND status = %s
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        
        result = execute_query(query, (tenant_id, subtenant_id, start_date, end_date, status))
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Password users error: {e}")
        return jsonify({'error': str(e)}), 500

# ================================================================
# SSO METRICS - WITH CLICKABLE BOXES
# ================================================================

@app.route('/api/metrics/sso')
def get_sso_metrics():
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = """
            SELECT 
                COUNT(DISTINCT user) as unique_users,
                COUNT(DISTINCT app) as unique_apps,
                COUNT(*) as total_sessions
            FROM idx2_audit_sso
            WHERE tenant = %s 
              AND subtenant = %s
              AND timestamp >= %s
              AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
        """
        
        result = execute_query(query, (tenant_id, subtenant_id, start_date, end_date), fetch_one=True)
        
        if result:
            return jsonify({
                'unique_users': int(result.get('unique_users') or 0),
                'unique_apps': int(result.get('unique_apps') or 0),
                'total_sessions': int(result.get('total_sessions') or 0)
            })
        
        return jsonify({'unique_users': 0, 'unique_apps': 0, 'total_sessions': 0})
    
    except Exception as e:
        logger.error(f"SSO metrics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics/sso/apps')
def get_sso_apps():
    """SSO app breakdown for bar chart"""
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = """
            SELECT 
                app,
                COUNT(*) as count
            FROM idx2_audit_sso
            WHERE tenant = %s 
              AND subtenant = %s
              AND timestamp >= %s
              AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
            GROUP BY app
            ORDER BY count DESC
            LIMIT 10
        """
        
        result = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"SSO apps error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics/sso/unique-users')
def get_sso_unique_users():
    """NEW: Get list of unique users only"""
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        logger.info(f"Fetching SSO unique users")
        
        query = """
            SELECT 
                user,
                COUNT(*) as total_sessions,
                COUNT(DISTINCT app) as apps_used,
                MAX(timestamp) as last_login
            FROM idx2_audit_sso
            WHERE tenant = %s 
              AND subtenant = %s
              AND timestamp >= %s
              AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
            GROUP BY user
            ORDER BY total_sessions DESC
            LIMIT 1000
        """
        
        result = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
        logger.info(f"Found {len(result)} unique users")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"SSO unique users error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics/sso/apps-list')
def get_sso_apps_list():
    """NEW: Get list of apps only"""
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        logger.info(f"Fetching SSO apps list")
        
        query = """
            SELECT 
                app,
                COUNT(*) as total_sessions,
                COUNT(DISTINCT user) as users_count,
                MAX(timestamp) as last_used
            FROM idx2_audit_sso
            WHERE tenant = %s 
              AND subtenant = %s
              AND timestamp >= %s
              AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
            GROUP BY app
            ORDER BY total_sessions DESC
            LIMIT 1000
        """
        
        result = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
        logger.info(f"Found {len(result)} apps")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"SSO apps list error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics/sso/sessions')
def get_sso_sessions():
    """NEW: Get all session details"""
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        logger.info(f"Fetching SSO sessions")
        
        query = """
            SELECT 
                user,
                app,
                ip,
                timestamp
            FROM idx2_audit_sso
            WHERE tenant = %s 
              AND subtenant = %s
              AND timestamp >= %s
              AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        
        result = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
        logger.info(f"Found {len(result)} sessions")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"SSO sessions error: {e}")
        return jsonify({'error': str(e)}), 500

# ================================================================
# ACCESS MAP
# ================================================================

@app.route('/api/metrics/access-map')
def get_access_map():
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = """
            SELECT 
                ip,
                COUNT(*) as access_count,
                COUNT(DISTINCT user) as unique_users,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_logins,
                MAX(timestamp) as last_access
            FROM idx2_audit_login
            WHERE tenant = %s 
              AND subtenant = %s
              AND timestamp >= %s
              AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
              AND ip IS NOT NULL
              AND ip != ''
            GROUP BY ip
            HAVING access_count > 0
            ORDER BY access_count DESC
            LIMIT 500
        """
        
        result = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
        
        map_data = []
        for row in result:
            map_data.append({
                'ip': row['ip'],
                'count': row['access_count'],
                'users': row['unique_users'],
                'successful': row['successful_logins'],
                'last_access': str(row['last_access'])
            })
        
        return jsonify(map_data)
    
    except Exception as e:
        logger.error(f"Access map error: {e}")
        return jsonify({'error': str(e)}), 500

# ================================================================
# PDF GENERATION
# ================================================================

@app.route('/api/generate-pdf/<report_type>')
def generate_pdf(report_type):
    try:
        tenant_id = request.args.get('tenant_id', 22, type=int)
        subtenant_id = request.args.get('subtenant_id', 13, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status = request.args.get('status', '')
        
        logger.info(f"PDF request: type={report_type}, status={status}")
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#FF8C42'),
            spaceAfter=30,
            alignment=1
        )
        
        title = f"{report_type.upper().replace('-', ' ')} Report"
        if status:
            title += f" - {status} Only"
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        meta_data = [
            ['Report Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Date Range:', f"{start_date} to {end_date}"],
            ['Tenant ID:', str(tenant_id)],
            ['Subtenant ID:', str(subtenant_id)]
        ]
        
        if status:
            meta_data.append(['Filter:', f"Status = {status}"])
        
        meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(meta_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Fetch data based on report type
        if report_type == 'login':
            if status:
                query = """
                    SELECT user, ip, timestamp, status
                    FROM idx2_audit_login
                    WHERE tenant = %s AND subtenant = %s
                    AND timestamp >= %s AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
                    AND status = %s
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """
                data = execute_query(query, (tenant_id, subtenant_id, start_date, end_date, status))
            else:
                query = """
                    SELECT user, ip, timestamp, status
                    FROM idx2_audit_login
                    WHERE tenant = %s AND subtenant = %s
                    AND timestamp >= %s AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """
                data = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
            
            table_data = [['User', 'IP', 'Timestamp', 'Status']]
            for row in data:
                table_data.append([
                    str(row.get('user', 'N/A'))[:40],
                    str(row.get('ip', 'N/A')),
                    str(row.get('timestamp', ''))[:19],
                    str(row.get('status', ''))
                ])
        
        elif report_type == 'password':
            if status:
                query = """
                    SELECT user, timestamp, status
                    FROM idx2_audit_fgtpwd
                    WHERE tenant = %s AND subtenant = %s
                    AND timestamp >= %s AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
                    AND status = %s
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """
                data = execute_query(query, (tenant_id, subtenant_id, start_date, end_date, status))
            else:
                query = """
                    SELECT user, timestamp, status
                    FROM idx2_audit_fgtpwd
                    WHERE tenant = %s AND subtenant = %s
                    AND timestamp >= %s AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """
                data = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
            
            table_data = [['User', 'Timestamp', 'Status']]
            for row in data:
                table_data.append([
                    str(row.get('user', 'N/A'))[:40],
                    str(row.get('timestamp', ''))[:19],
                    str(row.get('status', ''))
                ])
        
        elif report_type == 'sso-unique-users':
            query = """
                SELECT user, COUNT(*) as sessions, COUNT(DISTINCT app) as apps, MAX(timestamp) as last_login
                FROM idx2_audit_sso
                WHERE tenant = %s AND subtenant = %s
                AND timestamp >= %s AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
                GROUP BY user
                ORDER BY sessions DESC
                LIMIT 1000
            """
            data = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
            
            table_data = [['User', 'Total Sessions', 'Apps Used', 'Last Login']]
            for row in data:
                table_data.append([
                    str(row.get('user', 'N/A'))[:40],
                    str(row.get('sessions', 0)),
                    str(row.get('apps', 0)),
                    str(row.get('last_login', ''))[:19]
                ])
        
        elif report_type == 'sso-apps-list':
            query = """
                SELECT app, COUNT(*) as sessions, COUNT(DISTINCT user) as users, MAX(timestamp) as last_used
                FROM idx2_audit_sso
                WHERE tenant = %s AND subtenant = %s
                AND timestamp >= %s AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
                GROUP BY app
                ORDER BY sessions DESC
                LIMIT 1000
            """
            data = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
            
            table_data = [['Application', 'Total Sessions', 'Users', 'Last Used']]
            for row in data:
                table_data.append([
                    str(row.get('app', 'N/A'))[:40],
                    str(row.get('sessions', 0)),
                    str(row.get('users', 0)),
                    str(row.get('last_used', ''))[:19]
                ])
        
        elif report_type == 'sso-sessions':
            query = """
                SELECT user, app, ip, timestamp
                FROM idx2_audit_sso
                WHERE tenant = %s AND subtenant = %s
                AND timestamp >= %s AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
                ORDER BY timestamp DESC
                LIMIT 1000
            """
            data = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
            
            table_data = [['User', 'Application', 'IP', 'Timestamp']]
            for row in data:
                table_data.append([
                    str(row.get('user', 'N/A'))[:30],
                    str(row.get('app', 'N/A'))[:25],
                    str(row.get('ip', 'N/A')),
                    str(row.get('timestamp', ''))[:19]
                ])
        
        elif report_type == 'access-map':
            query = """
                SELECT ip, COUNT(*) as count, COUNT(DISTINCT user) as users, 
                       SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END) as successful
                FROM idx2_audit_login
                WHERE tenant = %s AND subtenant = %s
                AND timestamp >= %s AND timestamp < DATE_ADD(%s, INTERVAL 1 DAY)
                AND ip IS NOT NULL
                GROUP BY ip
                ORDER BY count DESC
                LIMIT 1000
            """
            data = execute_query(query, (tenant_id, subtenant_id, start_date, end_date))
            
            table_data = [['IP Address', 'Total Access', 'Unique Users', 'Successful']]
            for row in data:
                table_data.append([
                    str(row.get('ip', 'N/A')),
                    str(row.get('count', 0)),
                    str(row.get('users', 0)),
                    str(row.get('successful', 0))
                ])
        
        if len(table_data) > 1:
            col_widths = [1.8*inch] * len(table_data[0])
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF8C42')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
            
            elements.append(Spacer(1, 0.3*inch))
            summary_text = f"<b>Total Records:</b> {len(table_data) - 1}"
            elements.append(Paragraph(summary_text, styles['Normal']))
        else:
            elements.append(Paragraph("No data available.", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        
        logger.info(f"PDF generated: {len(table_data)-1} rows")
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{report_type}_report_{start_date}_to_{end_date}.pdf'
        )
    
    except Exception as e:
        logger.error(f"PDF generation error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# ================================================================
# ERROR HANDLERS
# ================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# ================================================================
# STARTUP
# ================================================================

if __name__ == '__main__':
    logger.info("🚀 Starting PRODUCTION READY Dashboard")
    logger.info("📊 Real-time data from live database")
    logger.info("♻️ Auto-refresh every 30 seconds")
    app.run(
        debug=os.getenv('FLASK_ENV') == 'development',
        host='0.0.0.0',
        port=5000
    )