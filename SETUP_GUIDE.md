# AWS Console Setup Guide - Method 1 (Complete)

Infrastructure setup via AWS Console with app deployment for EC2 and Lambda.

## Part 1: Infrastructure Setup (Already Completed ✓)

You have successfully created:
- VPC with public/private subnets
- RDS PostgreSQL database
- ElastiCache Redis cluster
- DynamoDB table
- S3 bucket
- SNS topic
- Security groups
- IAM roles

---

## Part 2: Initialize PostgreSQL Database

### Step 1: Launch Bastion Host (EC2 in Public Subnet)

1. Go to **EC2 Console** → **Instances** → **Launch Instances**
2. Configuration:
   - Name: `bastion-host`
   - AMI: Ubuntu 22.04 LTS
   - Instance type: `t2.micro`
   - Key pair: Select your key pair
   - Network: Select your VPC
   - Subnet: Select public subnet
   - Security group: Create new or select one allowing SSH (port 22)
   - Public IP: Enable
3. Launch instance

### Step 2: Connect to Bastion and Initialize Database

```bash
# SSH into bastion
ssh -i your-key.pem ubuntu@<bastion-public-ip>

# Install PostgreSQL client
sudo apt-get update
sudo apt-get install -y postgresql-client

# Get RDS endpoint from RDS Console
# Go to RDS → Databases → sample-app-db → Endpoint

# Connect to RDS
psql -h <RDS_ENDPOINT> -U postgres -d appdb

# Run schema
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    product VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# Exit
\q
```

---

## Part 3: Deploy Backend on EC2

### Step 1: Launch Backend EC2 (Private Subnet)

1. Go to **EC2 Console** → **Instances** → **Launch Instances**
2. Configuration:
   - Name: `backend-server`
   - AMI: Ubuntu 22.04 LTS
   - Instance type: `t2.micro`
   - Key pair: Select your key pair
   - Network: Select your VPC
   - Subnet: Select private subnet
   - Security group: Select backend security group (port 5000)
   - IAM instance profile: Select your EC2 role
3. Launch instance

### Step 2: Connect via Bastion and Deploy App

```bash
# From bastion, SSH to backend (using private IP)
ssh -i your-key.pem ubuntu@<backend-private-ip>

# Install dependencies
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip git postgresql-client

# Create app directory
mkdir -p /opt/sample-app
cd /opt/sample-app

# Clone repository
git clone <your-repo-url> .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install flask boto3 psycopg2-binary redis python-dotenv

# Create .env file
cat > .env <<EOF
AWS_REGION=us-east-1
DYNAMODB_TABLE=users_table
POSTGRES_HOST=<RDS_ENDPOINT>
POSTGRES_DB=appdb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<YOUR_DB_PASSWORD>
REDIS_HOST=<REDIS_ENDPOINT>
REDIS_PORT=6379
S3_BUCKET=<S3_BUCKET_NAME>
SNS_TOPIC_ARN=<SNS_TOPIC_ARN>
SES_FROM_EMAIL=<YOUR_EMAIL>
EOF

# Get values from AWS Console:
# - RDS Endpoint: RDS Console → Databases → sample-app-db
# - Redis Endpoint: ElastiCache Console → Clusters → sample-app-redis
# - S3 Bucket: S3 Console → Buckets
# - SNS Topic ARN: SNS Console → Topics

# Test app
cd backend
python3 app.py
```

### Step 3: Create Systemd Service (Optional - for auto-start)

```bash
# Create service file
sudo tee /etc/systemd/system/sample-app.service > /dev/null <<EOF
[Unit]
Description=Sample Application Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/sample-app
Environment="PATH=/opt/sample-app/venv/bin"
ExecStart=/opt/sample-app/venv/bin/python backend/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable sample-app
sudo systemctl start sample-app

# Check status
sudo systemctl status sample-app
```

### Step 4: Test Backend API

```bash
# From bastion
curl http://<backend-private-ip>:5000/health

# Create user
curl -X POST http://<backend-private-ip>:5000/users \
    -H "Content-Type: application/json" \
    -d '{"user_id":"user001","name":"John","email":"john@example.com"}'

# Get users
curl http://<backend-private-ip>:5000/users

# Create order
curl -X POST http://<backend-private-ip>:5000/orders \
    -H "Content-Type: application/json" \
    -d '{"user_id":"user001","product":"Laptop","amount":999.99}'

# Get orders
curl http://<backend-private-ip>:5000/orders
```

---

## Part 4: Deploy Frontend on EC2 (Private Subnet)

### Step 1: Launch Frontend EC2

1. Go to **EC2 Console** → **Instances** → **Launch Instances**
2. Configuration:
   - Name: `frontend-server`
   - AMI: Ubuntu 22.04 LTS
   - Instance type: `t2.micro`
   - Key pair: Select your key pair
   - Network: Select your VPC
   - Subnet: Select private subnet
   - Security group: Select frontend security group (port 80)
   - IAM instance profile: Select your EC2 role
3. Launch instance

### Step 2: Deploy Frontend

```bash
# From bastion, SSH to frontend
ssh -i your-key.pem ubuntu@<frontend-private-ip>

# Install nginx
sudo apt-get update
sudo apt-get install -y nginx

# Create app directory
mkdir -p /opt/sample-app/frontend
cd /opt/sample-app

# Clone repository
git clone <your-repo-url> .

# Configure nginx
sudo tee /etc/nginx/sites-available/default > /dev/null <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    root /opt/sample-app/frontend;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /api/ {
        proxy_pass http://<BACKEND_PRIVATE_IP>:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Replace BACKEND_PRIVATE_IP with actual backend private IP
sudo sed -i 's/<BACKEND_PRIVATE_IP>/<actual-backend-ip>/g' /etc/nginx/sites-available/default

# Enable and start nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# Check status
sudo systemctl status nginx
```

### Step 3: Create NLB (Network Load Balancer)

1. Go to **EC2 Console** → **Load Balancers** → **Create Load Balancer**
2. Select **Network Load Balancer**
3. Configuration:
   - Name: `sample-app-nlb`
   - Scheme: Internet-facing
   - IP address type: IPv4
   - VPC: Select your VPC
   - Subnets: Select both public subnets
4. Click **Next**
5. Security groups: Select NLB security group (port 80)
6. Click **Next**
7. Configure routing:
   - Target type: Instances
   - Protocol: TCP
   - Port: 80
   - Name: `frontend-targets`
8. Click **Next**
9. Register targets:
   - Select frontend EC2 instance
   - Port: 80
   - Click **Add to registered**
10. Click **Create**

### Step 4: Test Frontend via NLB

```bash
# Get NLB DNS name from Load Balancers console
# Access in browser: http://<NLB-DNS-NAME>

# Or via curl
curl http://<NLB-DNS-NAME>/
```

---

## Part 5: Deploy Lambda Functions

### Step 1: Create Lambda Execution Role

1. Go to **IAM Console** → **Roles** → **Create Role**
2. Trusted entity: **AWS Service** → **Lambda**
3. Attach policies:
   - `AWSLambdaBasicExecutionRole`
   - `AWSLambdaVPCAccessExecutionRole`
   - `AmazonDynamoDBFullAccess`
   - `AmazonS3FullAccess`
   - `AmazonSNSFullAccess`
   - `AmazonSESFullAccess`
4. Role name: `lambda-execution-role`
5. Create role

### Step 2: Create API Lambda Function

1. Go to **Lambda Console** → **Functions** → **Create Function**
2. Configuration:
   - Name: `app-api-handler`
   - Runtime: Python 3.11
   - Execution role: Select `lambda-execution-role`
3. Click **Create Function**
4. In function code editor, paste:

```python
import json
import boto3
import psycopg2
import redis
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_REGION'])
s3 = boto3.client('s3', region_name=os.environ['AWS_REGION'])
sns = boto3.client('sns', region_name=os.environ['AWS_REGION'])
ses = boto3.client('ses', region_name=os.environ['AWS_REGION'])

def lambda_handler(event, context):
    path = event.get('path', '')
    method = event.get('httpMethod', '')
    
    try:
        if path == '/users' and method == 'GET':
            return get_users()
        elif path == '/users' and method == 'POST':
            return create_user(json.loads(event.get('body', '{}')))
        elif path == '/orders' and method == 'GET':
            return get_orders()
        elif path == '/orders' and method == 'POST':
            return create_order(json.loads(event.get('body', '{}')))
        elif path == '/health':
            return {'statusCode': 200, 'body': json.dumps({'status': 'healthy'})}
        else:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Not found'})}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def get_users():
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    response = table.scan()
    return {'statusCode': 200, 'body': json.dumps(response.get('Items', []))}

def create_user(data):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    table.put_item(Item={
        'user_id': data.get('user_id'),
        'name': data.get('name'),
        'email': data.get('email'),
        'created_at': datetime.utcnow().isoformat()
    })
    
    sns.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Message=json.dumps({'action': 'user_created', 'user_id': data.get('user_id')}),
        Subject='New User Created'
    )
    
    return {'statusCode': 201, 'body': json.dumps({'message': 'User created'})}

def get_orders():
    conn = psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, product, amount, created_at FROM orders')
    rows = cur.fetchall()
    orders = [{'id': r[0], 'user_id': r[1], 'product': r[2], 'amount': float(r[3]), 'created_at': str(r[4])} for r in rows]
    cur.close()
    conn.close()
    return {'statusCode': 200, 'body': json.dumps(orders)}

def create_order(data):
    conn = psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO orders (user_id, product, amount) VALUES (%s, %s, %s) RETURNING id',
        (data.get('user_id'), data.get('product'), data.get('amount'))
    )
    order_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {'statusCode': 201, 'body': json.dumps({'message': 'Order created', 'order_id': order_id})}
```

5. Click **Deploy**

### Step 3: Add Environment Variables to Lambda

1. In Lambda function → **Configuration** → **Environment variables**
2. Add:
   - `AWS_REGION`: `us-east-1`
   - `DYNAMODB_TABLE`: `users_table`
   - `POSTGRES_HOST`: `<RDS_ENDPOINT>`
   - `POSTGRES_DB`: `appdb`
   - `POSTGRES_USER`: `postgres`
   - `POSTGRES_PASSWORD`: `<YOUR_DB_PASSWORD>`
   - `REDIS_HOST`: `<REDIS_ENDPOINT>`
   - `REDIS_PORT`: `6379`
   - `S3_BUCKET`: `<S3_BUCKET_NAME>`
   - `SNS_TOPIC_ARN`: `<SNS_TOPIC_ARN>`
   - `SES_FROM_EMAIL`: `<YOUR_EMAIL>`

### Step 4: Configure VPC for Lambda

1. In Lambda function → **Configuration** → **VPC**
2. Select your VPC
3. Select private subnets
4. Select backend security group
5. Click **Save**

### Step 5: Create API Gateway

1. Go to **API Gateway Console** → **Create API**
2. Select **REST API** → **Build**
3. Configuration:
   - API name: `sample-app-api`
   - Endpoint type: Regional
4. Click **Create API**
5. Create resources:
   - Right-click **/** → **Create Resource**
   - Resource name: `users`
   - Create resource
   - Repeat for `orders`, `upload`, `send-email`

6. Create methods:
   - Select `/users` → **Create Method** → **GET**
   - Integration type: Lambda Function
   - Lambda Function: `app-api-handler`
   - Click **Save**
   - Repeat for POST, and other resources

7. Deploy API:
   - Click **Deploy API**
   - Stage: `prod`
   - Click **Deploy**

### Step 6: Test Lambda via API Gateway

```bash
# Get API endpoint from API Gateway console
API_URL="https://<api-id>.execute-api.us-east-1.amazonaws.com/prod"

# Test health
curl $API_URL/health

# Create user
curl -X POST $API_URL/users \
    -H "Content-Type: application/json" \
    -d '{"user_id":"user001","name":"John","email":"john@example.com"}'

# Get users
curl $API_URL/users
```

### Step 7: Create SNS Lambda Handler

1. Go to **Lambda Console** → **Create Function**
2. Configuration:
   - Name: `app-sns-handler`
   - Runtime: Python 3.11
   - Execution role: Select `lambda-execution-role`
3. Code:

```python
import json
import boto3
import os

ses = boto3.client('ses', region_name=os.environ['AWS_REGION'])

def lambda_handler(event, context):
    for record in event['Records']:
        sns_message = json.loads(record['Sns']['Message'])
        
        if sns_message.get('action') == 'user_created':
            send_welcome_email(sns_message.get('user_id'))
        
    return {'statusCode': 200, 'body': json.dumps('Notification processed')}

def send_welcome_email(user_id):
    ses.send_email(
        Source=os.environ['SES_FROM_EMAIL'],
        Destination={'ToAddresses': ['admin@example.com']},
        Message={
            'Subject': {'Data': 'New User Registration'},
            'Body': {'Text': {'Data': f'New user registered with ID: {user_id}'}}
        }
    )
```

4. Add environment variables:
   - `AWS_REGION`: `us-east-1`
   - `SES_FROM_EMAIL`: `<YOUR_EMAIL>`

5. Click **Deploy**

### Step 8: Subscribe SNS to Lambda

1. Go to **SNS Console** → **Topics** → `app-notifications`
2. Click **Create subscription**
3. Configuration:
   - Protocol: Lambda
   - Endpoint: `app-sns-handler`
4. Click **Create subscription**

---

## Testing

### Test EC2 Backend
```bash
curl http://<backend-private-ip>:5000/health
```

### Test Frontend via NLB
```bash
curl http://<NLB-DNS-NAME>/
```

### Test Lambda API
```bash
curl https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/health
```

---

## Summary

✓ Infrastructure created (VPC, RDS, Redis, DynamoDB, S3, SNS)
✓ PostgreSQL database initialized
✓ Backend EC2 deployed with Flask app
✓ Frontend EC2 deployed with nginx
✓ NLB routing traffic to frontend
✓ Lambda functions deployed with API Gateway
✓ SNS notifications configured

**Access Points:**
- Frontend: `http://<NLB-DNS-NAME>`
- Backend API (EC2): `http://<backend-private-ip>:5000`
- Lambda API: `https://<api-id>.execute-api.us-east-1.amazonaws.com/prod`
