import json
import sys
from flask import Flask, request, jsonify
from datetime import datetime
sys.path.append('..')
from config.config import *

app = Flask(__name__)

dynamodb = get_dynamodb()
s3 = get_s3()
sns = get_sns()
ses = get_ses()
cache = get_redis()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/users', methods=['GET'])
def get_users():
    cache_key = 'users_list'
    cached = cache.get(cache_key)
    if cached:
        return jsonify({'source': 'cache', 'data': json.loads(cached)})
    
    table = dynamodb.Table(Config.DYNAMODB_TABLE)
    response = table.scan()
    users = response.get('Items', [])
    
    cache.setex(cache_key, 300, json.dumps(users))
    return jsonify({'source': 'dynamodb', 'data': users})

@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    user_id = data.get('user_id')
    
    table = dynamodb.Table(Config.DYNAMODB_TABLE)
    table.put_item(Item={
        'user_id': user_id,
        'name': data.get('name'),
        'email': data.get('email'),
        'created_at': datetime.utcnow().isoformat()
    })
    
    cache.delete('users_list')
    
    sns.publish(
        TopicArn=Config.SNS_TOPIC_ARN,
        Message=json.dumps({'action': 'user_created', 'user_id': user_id}),
        Subject='New User Created'
    )
    
    return jsonify({'message': 'User created', 'user_id': user_id}), 201

@app.route('/orders', methods=['GET'])
def get_orders():
    cache_key = 'orders_list'
    cached = cache.get(cache_key)
    if cached:
        return jsonify({'source': 'cache', 'data': json.loads(cached)})
    
    conn = get_postgres_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, product, amount, created_at FROM orders')
    rows = cur.fetchall()
    orders = [{'id': r[0], 'user_id': r[1], 'product': r[2], 'amount': r[3], 'created_at': str(r[4])} for r in rows]
    cur.close()
    conn.close()
    
    cache.setex(cache_key, 300, json.dumps(orders))
    return jsonify({'source': 'postgres', 'data': orders})

@app.route('/orders', methods=['POST'])
def create_order():
    data = request.json
    
    conn = get_postgres_conn()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO orders (user_id, product, amount) VALUES (%s, %s, %s) RETURNING id',
        (data.get('user_id'), data.get('product'), data.get('amount'))
    )
    order_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    cache.delete('orders_list')
    
    return jsonify({'message': 'Order created', 'order_id': order_id}), 201

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    filename = file.filename
    
    s3.upload_fileobj(file, Config.S3_BUCKET, filename)
    
    return jsonify({'message': 'File uploaded', 'filename': filename, 'bucket': Config.S3_BUCKET})

@app.route('/send-email', methods=['POST'])
def send_email():
    data = request.json
    
    ses.send_email(
        Source=Config.SES_FROM_EMAIL,
        Destination={'ToAddresses': [data.get('to')]},
        Message={
            'Subject': {'Data': data.get('subject')},
            'Body': {'Text': {'Data': data.get('body')}}
        }
    )
    
    return jsonify({'message': 'Email sent'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
