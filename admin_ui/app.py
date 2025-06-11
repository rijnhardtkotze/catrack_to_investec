#!/usr/bin/env python3
"""
Car Service Savings Management Admin UI
A Flask-based web application for managing the car service savings Lambda function.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, TextAreaField, SelectField
from wtforms.validators import DataRequired, NumberRange
import boto3
from botocore.exceptions import ClientError
import requests

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///admin.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('admin.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# AWS clients
try:
    lambda_client = boto3.client('lambda')
    cloudwatch_client = boto3.client('cloudwatch')
    logs_client = boto3.client('logs')
except Exception as e:
    logger.warning(f"Could not initialize AWS clients: {e}")
    lambda_client = cloudwatch_client = logs_client = None


# Database Models
class Configuration(db.Model):
    """Configuration settings for the Lambda function"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Configuration {self.name}>'


class TransactionLog(db.Model):
    """Log of all transactions and operations"""
    id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(50), nullable=False)  # 'transfer', 'calculation', 'error'
    status = db.Column(db.String(20), nullable=False)  # 'success', 'failed', 'pending'
    amount = db.Column(db.Float)
    distance = db.Column(db.Float)
    from_account = db.Column(db.String(100))
    to_account = db.Column(db.String(100))
    reference = db.Column(db.String(200))
    error_message = db.Column(db.Text)
    raw_data = db.Column(db.Text)  # JSON data from APIs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TransactionLog {self.transaction_type}:{self.status}>'


class ErrorLog(db.Model):
    """Detailed error logging"""
    id = db.Column(db.Integer, primary_key=True)
    error_type = db.Column(db.String(100), nullable=False)
    error_message = db.Column(db.Text, nullable=False)
    stack_trace = db.Column(db.Text)
    function_name = db.Column(db.String(100))
    lambda_request_id = db.Column(db.String(100))
    user_agent = db.Column(db.String(200))
    ip_address = db.Column(db.String(50))
    additional_data = db.Column(db.Text)  # JSON
    severity = db.Column(db.String(20), default='ERROR')
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ErrorLog {self.error_type}>'


# Forms
class ConfigurationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    value = TextAreaField('Value', validators=[DataRequired()])
    description = TextAreaField('Description')


class TransferTestForm(FlaskForm):
    registration = StringField('Vehicle Registration', validators=[DataRequired()])
    from_date = DateField('From Date', validators=[DataRequired()])
    to_date = DateField('To Date', validators=[DataRequired()])
    rate_per_km = FloatField('Rate per KM', validators=[DataRequired(), NumberRange(min=0)])


class ErrorResolutionForm(FlaskForm):
    resolution_notes = TextAreaField('Resolution Notes', validators=[DataRequired()])


# Routes
@app.route('/')
def dashboard():
    """Main dashboard with overview metrics"""
    try:
        # Get recent transactions
        recent_transactions = TransactionLog.query.order_by(TransactionLog.created_at.desc()).limit(10).all()
        
        # Get recent errors
        recent_errors = ErrorLog.query.filter_by(resolved=False).order_by(ErrorLog.created_at.desc()).limit(5).all()
        
        # Calculate statistics
        total_transactions = TransactionLog.query.count()
        total_errors = ErrorLog.query.count()
        unresolved_errors = ErrorLog.query.filter_by(resolved=False).count()
        
        # Get configuration count
        config_count = Configuration.query.count()
        
        # Calculate total savings this month
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_savings = db.session.query(db.func.sum(TransactionLog.amount)).filter(
            TransactionLog.created_at >= start_of_month,
            TransactionLog.transaction_type == 'transfer',
            TransactionLog.status == 'success'
        ).scalar() or 0
        
        return render_template('dashboard.html',
                             recent_transactions=recent_transactions,
                             recent_errors=recent_errors,
                             total_transactions=total_transactions,
                             total_errors=total_errors,
                             unresolved_errors=unresolved_errors,
                             config_count=config_count,
                             monthly_savings=monthly_savings)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash(f'Error loading dashboard: {e}', 'error')
        return render_template('dashboard.html', 
                             recent_transactions=[], 
                             recent_errors=[],
                             total_transactions=0,
                             total_errors=0,
                             unresolved_errors=0,
                             config_count=0,
                             monthly_savings=0)


@app.route('/config')
def config_list():
    """List all configuration settings"""
    configs = Configuration.query.order_by(Configuration.name).all()
    return render_template('config_list.html', configs=configs)


@app.route('/config/new', methods=['GET', 'POST'])
def config_new():
    """Create new configuration setting"""
    form = ConfigurationForm()
    if form.validate_on_submit():
        try:
            config = Configuration(
                name=form.name.data,
                value=form.value.data,
                description=form.description.data
            )
            db.session.add(config)
            db.session.commit()
            logger.info(f"Created new configuration: {config.name}")
            flash(f'Configuration "{config.name}" created successfully!', 'success')
            return redirect(url_for('config_list'))
        except Exception as e:
            logger.error(f"Error creating configuration: {e}")
            flash(f'Error creating configuration: {e}', 'error')
    
    return render_template('config_form.html', form=form, title='New Configuration')


@app.route('/config/<int:config_id>/edit', methods=['GET', 'POST'])
def config_edit(config_id):
    """Edit existing configuration setting"""
    config = Configuration.query.get_or_404(config_id)
    form = ConfigurationForm(obj=config)
    
    if form.validate_on_submit():
        try:
            old_value = config.value
            config.name = form.name.data
            config.value = form.value.data
            config.description = form.description.data
            config.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Updated configuration {config.name}: {old_value} -> {config.value}")
            flash(f'Configuration "{config.name}" updated successfully!', 'success')
            return redirect(url_for('config_list'))
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            flash(f'Error updating configuration: {e}', 'error')
    
    return render_template('config_form.html', form=form, config=config, title='Edit Configuration')


@app.route('/config/<int:config_id>/delete', methods=['POST'])
def config_delete(config_id):
    """Delete configuration setting"""
    config = Configuration.query.get_or_404(config_id)
    try:
        name = config.name
        db.session.delete(config)
        db.session.commit()
        logger.info(f"Deleted configuration: {name}")
        flash(f'Configuration "{name}" deleted successfully!', 'success')
    except Exception as e:
        logger.error(f"Error deleting configuration: {e}")
        flash(f'Error deleting configuration: {e}', 'error')
    
    return redirect(url_for('config_list'))


@app.route('/transactions')
def transaction_list():
    """List all transactions with filtering"""
    page = request.args.get('page', 1, type=int)
    transaction_type = request.args.get('type', '')
    status = request.args.get('status', '')
    
    query = TransactionLog.query
    
    if transaction_type:
        query = query.filter(TransactionLog.transaction_type == transaction_type)
    if status:
        query = query.filter(TransactionLog.status == status)
    
    transactions = query.order_by(TransactionLog.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('transaction_list.html', transactions=transactions, 
                         current_type=transaction_type, current_status=status)


@app.route('/transactions/<int:transaction_id>')
def transaction_detail(transaction_id):
    """View detailed transaction information"""
    transaction = TransactionLog.query.get_or_404(transaction_id)
    return render_template('transaction_detail.html', transaction=transaction)


@app.route('/errors')
def error_list():
    """List all errors with filtering"""
    page = request.args.get('page', 1, type=int)
    resolved = request.args.get('resolved', '')
    severity = request.args.get('severity', '')
    
    query = ErrorLog.query
    
    if resolved:
        query = query.filter(ErrorLog.resolved == (resolved == 'true'))
    if severity:
        query = query.filter(ErrorLog.severity == severity)
    
    errors = query.order_by(ErrorLog.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('error_list.html', errors=errors, 
                         current_resolved=resolved, current_severity=severity)


@app.route('/errors/<int:error_id>')
def error_detail(error_id):
    """View detailed error information"""
    error = ErrorLog.query.get_or_404(error_id)
    return render_template('error_detail.html', error=error)


@app.route('/errors/<int:error_id>/resolve', methods=['POST'])
def error_resolve(error_id):
    """Mark error as resolved"""
    error = ErrorLog.query.get_or_404(error_id)
    form = ErrorResolutionForm()
    
    if form.validate_on_submit():
        try:
            error.resolved = True
            if form.resolution_notes.data:
                additional_data = json.loads(error.additional_data or '{}')
                additional_data['resolution_notes'] = form.resolution_notes.data
                additional_data['resolved_at'] = datetime.utcnow().isoformat()
                error.additional_data = json.dumps(additional_data)
            
            db.session.commit()
            logger.info(f"Resolved error {error_id}: {error.error_type}")
            flash('Error marked as resolved!', 'success')
        except Exception as e:
            logger.error(f"Error resolving error log: {e}")
            flash(f'Error resolving error: {e}', 'error')
    
    return redirect(url_for('error_detail', error_id=error_id))


@app.route('/test')
def test_page():
    """Test page for manual operations"""
    form = TransferTestForm()
    return render_template('test_page.html', form=form)


@app.route('/test/calculate', methods=['POST'])
def test_calculate():
    """Test distance calculation"""
    form = TransferTestForm()
    if form.validate_on_submit():
        try:
            # Get configuration
            username = get_config_value('cartrack_username')
            password = get_config_value('cartrack_password')
            
            if not username or not password:
                flash('CarTrack credentials not configured!', 'error')
                return redirect(url_for('test_page'))
            
            # Simulate CarTrack API call
            response_data = {
                'registration': form.registration.data,
                'from_date': form.from_date.data.isoformat(),
                'to_date': form.to_date.data.isoformat(),
                'distance': 150.5,  # Simulated distance
                'amount': 150.5 * form.rate_per_km.data
            }
            
            # Log the test calculation
            log_entry = TransactionLog(
                transaction_type='calculation',
                status='success',
                amount=response_data['amount'],
                distance=response_data['distance'],
                reference=f"Test calculation for {form.registration.data}",
                raw_data=json.dumps(response_data)
            )
            db.session.add(log_entry)
            db.session.commit()
            
            flash(f'Test calculation completed! Distance: {response_data["distance"]}km, Amount: R{response_data["amount"]:.2f}', 'success')
            
        except Exception as e:
            logger.error(f"Test calculation error: {e}")
            flash(f'Test calculation failed: {e}', 'error')
    
    return redirect(url_for('test_page'))


@app.route('/api/lambda/logs')
def lambda_logs():
    """Get recent Lambda function logs"""
    try:
        if not logs_client:
            return jsonify({'error': 'AWS logs client not available'}), 503
        
        # Get log group name from config or use default
        log_group = get_config_value('lambda_log_group', '/aws/lambda/cartrack_to_investec')
        
        response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        logs = []
        for stream in response['logStreams']:
            events = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream['logStreamName'],
                limit=10
            )
            
            for event in events['events']:
                logs.append({
                    'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                    'message': event['message']
                })
        
        return jsonify(logs[:20])  # Return latest 20 log entries
        
    except Exception as e:
        logger.error(f"Error fetching Lambda logs: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/lambda/invoke', methods=['POST'])
def lambda_invoke():
    """Manually invoke the Lambda function"""
    try:
        if not lambda_client:
            return jsonify({'error': 'AWS Lambda client not available'}), 503
        
        function_name = get_config_value('lambda_function_name', 'cartrack_to_investec')
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse'
        )
        
        result = {
            'status_code': response['StatusCode'],
            'payload': response['Payload'].read().decode('utf-8'),
            'execution_time': response.get('ExecutedVersion', 'N/A')
        }
        
        # Log the manual invocation
        log_entry = TransactionLog(
            transaction_type='manual_invoke',
            status='success' if response['StatusCode'] == 200 else 'failed',
            reference='Manual Lambda invocation from admin UI',
            raw_data=json.dumps(result)
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error invoking Lambda: {e}")
        return jsonify({'error': str(e)}), 500


# Helper functions
def get_config_value(name, default=None):
    """Get configuration value from database"""
    config = Configuration.query.filter_by(name=name).first()
    return config.value if config else default


def log_error(error_type, error_message, **kwargs):
    """Log error to database"""
    try:
        error_log = ErrorLog(
            error_type=error_type,
            error_message=str(error_message),
            stack_trace=kwargs.get('stack_trace'),
            function_name=kwargs.get('function_name'),
            lambda_request_id=kwargs.get('lambda_request_id'),
            user_agent=kwargs.get('user_agent'),
            ip_address=kwargs.get('ip_address'),
            additional_data=json.dumps(kwargs.get('additional_data', {})),
            severity=kwargs.get('severity', 'ERROR')
        )
        db.session.add(error_log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log error to database: {e}")


# Initialize database
@app.before_first_request
def create_tables():
    """Create database tables if they don't exist"""
    db.create_all()
    
    # Create default configurations if they don't exist
    default_configs = [
        ('lambda_function_name', 'cartrack_to_investec', 'Name of the Lambda function'),
        ('lambda_log_group', '/aws/lambda/cartrack_to_investec', 'CloudWatch log group name'),
        ('cartrack_username', '', 'CarTrack API username'),
        ('cartrack_password', '', 'CarTrack API password'),
        ('investec_client_id', '', 'Investec API client ID'),
        ('investec_secret_key', '', 'Investec API secret key'),
        ('investec_api_key', '', 'Investec API key'),
        ('investec_from_account_id', '', 'Source account ID for transfers'),
        ('investec_to_account_id', '', 'Destination account ID for transfers'),
        ('rate_per_km', '0.25', 'Rate per kilometer for savings calculation'),
        ('default_registration', 'DV77FCGP', 'Default vehicle registration'),
    ]
    
    for name, value, description in default_configs:
        if not Configuration.query.filter_by(name=name).first():
            config = Configuration(name=name, value=value, description=description)
            db.session.add(config)
    
    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"Error creating default configurations: {e}")
        db.session.rollback()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)