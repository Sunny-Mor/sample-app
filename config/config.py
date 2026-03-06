import os
import boto3
import psycopg2
import redis
from dotenv import load_dotenv

load_dotenv()

class Config:
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', 'users_table')
    S3_BUCKET = os.getenv('S3_BUCKET', 'app-files-bucket')
    SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')
    SES_FROM_EMAIL = os.getenv('SES_FROM_EMAIL')
    
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'appdb')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

def get_dynamodb():
    return boto3.resource('dynamodb', region_name=Config.AWS_REGION)

def get_s3():
    return boto3.client('s3', region_name=Config.AWS_REGION)

def get_sns():
    return boto3.client('sns', region_name=Config.AWS_REGION)

def get_ses():
    return boto3.client('ses', region_name=Config.AWS_REGION)

def get_postgres_conn():
    return psycopg2.connect(
        host=Config.POSTGRES_HOST,
        database=Config.POSTGRES_DB,
        user=Config.POSTGRES_USER,
        password=Config.POSTGRES_PASSWORD
    )

def get_redis():
    return redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)
