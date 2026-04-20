"""
Amazon Affiliate Product Fetching Web App
Uses Amazon Product Advertising API 5.0 to fetch products based on keywords
"""

import os
import uuid
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Amazon PA API Configuration
ACCESS_KEY = os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
ASSOCIATE_TAG = os.getenv('ASSOCIATE_TAG')
HOST = 'webservices.amazon.in'  # Use 'webservices.amazon.com' for US, 'webservices.amazon.co.uk' for UK, etc.
REGION = 'us-east-1'  # AWS region for Amazon PA API
SERVICE = 'ProductAdvertisingAPI'

def generate_aws_signature(secret_key, date, region, service, payload):
    """
    Generate AWS Signature Version 4 for PA API 5.0
    """
    # Create signing key
    def sign(key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    k_secret = f'AWS4{secret_key}'.encode('utf-8')
    k_date = sign(k_secret, date)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, 'aws4_request')
    
    # Sign the payload
    signature = hmac.new(k_signing, payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def fetch_amazon_products(keyword, count=10):
    """
    Fetch products from Amazon Product Advertising API 5.0
    Returns list of products with title, price, image URL, and affiliate link
    """
    try:
        # Prepare the API endpoint
        endpoint = f'https://{HOST}/paapi5/searchitems'
        
        # Prepare the request body
        request_body = {
            'Keywords': keyword,
            'ItemCount': min(count, 10),  # Max 10 items per request
            'Resources': [
                'ItemInfo.Title',
                'Offers.Listings.Price',
                'Images.Primary.Medium',
                'DetailPageURL'
            ]
        }
        
        # Convert request body to JSON string
        payload = json.dumps(request_body)
        
        # Generate timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        date = timestamp[:8]
        
        # Create canonical request
        canonical_uri = '/paapi5/searchitems'
        canonical_querystring = ''
        canonical_headers = f'host:{HOST}\nx-amz-date:{timestamp}\n'
        signed_headers = 'host;x-amz-date'
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        canonical_request = f'POST\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
        
        # Create string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date}/{REGION}/{SERVICE}/aws4_request'
        string_to_sign = f'{algorithm}\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
        
        # Generate signature
        signature = generate_aws_signature(SECRET_KEY, date, REGION, SERVICE, string_to_sign)
        
        # Create authorization header
        authorization_header = f'{algorithm} Credential={ACCESS_KEY}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
        
        # Make the API request
        headers = {
            'Content-Type': 'application/json',
            'X-Amz-Date': timestamp,
            'Authorization': authorization_header
        }
        
        response = requests.post(endpoint, headers=headers, data=payload)
        
        # Check if request was successful
        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get('Errors', [{}])[0].get('Message', 'Unknown error')
            raise Exception(f'API Error: {error_msg}')
        
        data = response.json()
        
        # Parse the response
        products = []
        items = data.get('SearchResult', {}).get('Items', [])
        
        for item in items[:count]:
            # Extract product details
            title = item.get('ItemInfo', {}).get('Title', {}).get('DisplayValue', 'No title available')
            
            # Extract price
            price_info = item.get('Offers', {}).get('Listings', [{}])[0].get('Price', {})
            if price_info:
                amount = price_info.get('Amount', 0)
                currency = price_info.get('Currency', 'INR')
                price = f'{currency} {amount/100:.2f}' if amount else 'Price not available'
            else:
                price = 'Price not available'
            
            # Extract image URL
            image_url = item.get('Images', {}).get('Primary', {}).get('Medium', {}).get('URL', '')
            
            # Get detail page URL (affiliate link)
            affiliate_link = item.get('DetailPageURL', '')
            
            # Add tracking tag to affiliate link
            if affiliate_link and ASSOCIATE_TAG:
                parsed_url = urllib.parse.urlparse(affiliate_link)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                query_params['tag'] = [ASSOCIATE_TAG]
                new_query = urllib.parse.urlencode(query_params, doseq=True)
                affiliate_link = urllib.parse.urlunparse(parsed_url._replace(query=new_query))
            
            products.append({
                'title': title,
                'price': price,
                'image_url': image_url,
                'affiliate_link': affiliate_link
            })
        
        return products
    
    except requests.exceptions.RequestException as e:
        raise Exception(f'Network error: {str(e)}')
    except Exception as e:
        raise Exception(f'Failed to fetch products: {str(e)}')

@app.route('/')
def index():
    """
    Render the main page
    """
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """
    Handle product search request
    """
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        
        if not keyword:
            return jsonify({'error': 'Please enter a search keyword'}), 400
        
        # Fetch products from Amazon API
        products = fetch_amazon_products(keyword, count=8)
        
        if not products:
            return jsonify({'message': 'No products found for your search', 'products': []}), 200
        
        return jsonify({'products': products, 'count': len(products)}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
