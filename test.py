import jwt
import datetime

# Your secret key
secret = "shulelms"

# Create a payload with user ID and expiration (1 hour)
payload = {
    "user_id": 123,
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
}

# Generate the token using HS256 algorithm
token = jwt.encode(payload, secret, algorithm="HS256")

print(token)
