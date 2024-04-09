import bcrypt

def hash_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# Example usage
hashed_password_1 = hash_password('Livante141')
hashed_password_2 = hash_password('Livante141')

# Replace the placeholders in the credentials.yaml file with the hashed passwords
print(f"hashed_password_1: {hashed_password_1}")
print(f"hashed_password_2: {hashed_password_2}")