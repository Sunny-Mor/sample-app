import json
import boto3
import psycopg2
import redis
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_REGION'])
s3 = boto3.client('s3', region_name=os.environ['AWS_REGION'])
ses = boto3.client('ses', region_name=os.environ['AWS_REGION'])

cache = redis.Redis(host=os.environ['REDIS_HOST'], port=int(os.environ['REDIS_PORT']), decode_responses=True)

def get_postgres_conn():
    return psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )

def lambda_handler(event, context):
    http_method = event.get('httpMethod')
    path = event.get('path')
    
    if path == '/users' and http_method == 'GET':
        return get_users()
    elif path == '/users' and http_method == 'POST':
        return create_user(json.loads(event.get('body', '{}')))
    elif path == '/orders' and http_method == 'GET':
        return get_orders()
    elif path == '/orders' and http_method == 'POST':
        return create_order(json.loads(event.get('body', '{}')))
    
    return {'statusCode': 404, 'body': json.dumps({'error': 'Not found'})}

def get_users():
    cache_key = 'users_list'
    cached = cache.get(cache_key)
    if cached:
        return {'statusCode': 200, 'body': json.dumps({'source': 'cache', 'data': json.loads(cached)})}
    
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    response = table.scan()
    users = response.get('Items', [])
    
    cache.setex(cache_key, 300, json.dumps(users))
    return {'statusCode': 200, 'body': json.dumps({'source': 'dynamodb', 'data': users})}

def create_user(data):
    user_id = data.get('user_id')
    
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    table.put_item(Item={
        'user_id': user_id,
        'name': data.get('name'),
        'email': data.get('email'),
        'created_at': datetime.utcnow().isoformat()
    })
    
    cache.delete('users_list')
    
    return {'statusCode': 201, 'body': json.dumps({'message': 'User created', 'user_id': user_id})}

def get_orders():
    cache_key = 'orders_list'
    cached = cache.get(cache_key)
    if cached:
        return {'statusCode': 200, 'body': json.dumps({'source': 'cache', 'data': json.loads(cached)})}
    
    conn = get_postgres_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, product, amount, created_at FROM orders')
    rows = cur.fetchall()
    orders = [{'id': r[0], 'user_id': r[1], 'product': r[2], 'amount': r[3], 'created_at': str(r[4])} for r in rows]
    cur.close()
    conn.close()
    
    cache.setex(cache_key, 300, json.dumps(orders))
    return {'statusCode': 200, 'body': json.dumps({'source': 'postgres', 'data': orders})}

def create_order(data):
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
    
    return {'statusCode': 201, 'body': json.dumps({'message': 'Order created', 'order_id': order_id})}
